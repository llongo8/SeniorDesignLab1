#!/usr/bin/env python3
"""A software stand-in for the third box.

We have one set of hardware and three people. This serves the exact same JSON
API as the ESP32 so that the PC application, the chart and the alerting can all
be built and tested by anyone, at any time, with nothing plugged in.

    python tools/fake_box.py            # listens on http://127.0.0.1:8080

Point the PC app at it by setting these in pc-app/.env:

    BOX_HOST=127.0.0.1
    BOX_PORT=8080

Standard library only, on purpose -- no install step, no virtualenv needed.

Fault injection, for exercising the error paths the requirements demand:

    curl "http://127.0.0.1:8080/sim/unplug?sensor=1&value=true"   # Req 5a.i
    curl "http://127.0.0.1:8080/sim/power?on=false"               # Req 5a.ii / 6
    curl "http://127.0.0.1:8080/sim/temp?sensor=2&value=45"       # Req 7
    curl "http://127.0.0.1:8080/sim/temp?sensor=2&value=auto"     # back to normal
"""

from __future__ import annotations

import json
import math
import random
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HISTORY_LEN = 300
SAMPLE_PERIOD_S = 1.0
SENSOR_IDS = (1, 2)

_lock = threading.Lock()

state = {
    "powered": True,
    "sensors": {
        sid: {
            "plugged": True,
            "display_on": sid == 1,
            "temp_c": 22.0,
            "forced": None,  # set by /sim/temp to pin a value
        }
        for sid in SENSOR_IDS
    },
    # Oldest-first ring buffers, centi-degrees, None for a missing sample.
    "history": {sid: [] for sid in SENSOR_IDS},
    "boot_ts": time.time(),
}


def _simulate(sid: int, t: float) -> float:
    """A plausible room temperature: a slow drift plus a little noise, with the
    two probes offset from each other so they are easy to tell apart."""
    base = 22.0 + (0.8 if sid == 2 else 0.0)
    drift = 1.5 * math.sin(t / 45.0 + sid)
    return base + drift + random.uniform(-0.06, 0.06)


def _sampler() -> None:
    while True:
        now = time.time()
        with _lock:
            for sid in SENSOR_IDS:
                s = state["sensors"][sid]
                if state["powered"] and s["plugged"]:
                    s["temp_c"] = s["forced"] if s["forced"] is not None else _simulate(sid, now)
                    sample = int(round(s["temp_c"] * 100))
                else:
                    s["temp_c"] = None
                    sample = None
                buf = state["history"][sid]
                buf.append(sample)
                del buf[:-HISTORY_LEN]
        time.sleep(SAMPLE_PERIOD_S)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:  # quieter console
        if "/sim/" in self.path:
            sys.stderr.write("sim: %s\n" % (fmt % args))

    # -- helpers ------------------------------------------------------------
    def _send(self, code: int, payload: dict | str) -> None:
        body = (payload if isinstance(payload, str) else json.dumps(payload)).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _query(self) -> dict:
        return {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}

    # -- routing ------------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        self._route()

    def do_POST(self) -> None:  # noqa: N802
        self._route()

    def _route(self) -> None:
        path = urlparse(self.path).path
        query = self._query()

        if path.startswith("/sim/"):
            self._handle_sim(path, query)
            return

        # A box with its power switch off is simply not there.
        with _lock:
            powered = state["powered"]
        if not powered:
            self._send(503, {"error": "box is powered off"})
            return

        if path == "/api/state":
            self._handle_state()
        elif path == "/api/history":
            self._handle_history()
        elif path == "/api/info":
            self._handle_info()
        elif path == "/api/button":
            self._handle_button(query)
        else:
            self._send(404, {"error": "not found"})

    def _handle_state(self) -> None:
        with _lock:
            sensors = [
                {
                    "id": sid,
                    "present": state["sensors"][sid]["plugged"],
                    "display_on": state["sensors"][sid]["display_on"],
                    "temp_c": (
                        round(state["sensors"][sid]["temp_c"], 2)
                        if state["sensors"][sid]["plugged"]
                        and state["sensors"][sid]["temp_c"] is not None
                        else None
                    ),
                }
                for sid in SENSOR_IDS
            ]
            uptime = int((time.time() - state["boot_ts"]) * 1000)
        self._send(200, {"fw": "fake-0.1.0", "uptime_ms": uptime, "sensors": sensors})

    def _handle_history(self) -> None:
        with _lock:
            length = max(len(state["history"][sid]) for sid in SENSOR_IDS)
            sensors = [
                {"id": sid, "samples_c100": list(state["history"][sid])} for sid in SENSOR_IDS
            ]
        self._send(200, {"period_ms": 1000, "len": length, "sensors": sensors})

    def _handle_info(self) -> None:
        with _lock:
            uptime = int((time.time() - state["boot_ts"]) * 1000)
            length = len(state["history"][1])
        self._send(
            200,
            {
                "fw": "fake-0.1.0",
                "ip": "127.0.0.1",
                "mac": "00:00:00:00:00:00",
                "rssi_dbm": -42,
                "uptime_ms": uptime,
                "free_heap": 250000,
                "history_len": length,
                "i2c_hz": 800000,
                "max_render_us": 11800,
                "max_button_latency_us": 12100,
            },
        )

    def _handle_button(self, query: dict) -> None:
        try:
            sid = int(query.get("sensor", ""))
        except ValueError:
            sid = 0
        want = query.get("state", "toggle")
        if sid not in SENSOR_IDS:
            self._send(400, {"error": "sensor must be 1 or 2"})
            return
        with _lock:
            s = state["sensors"][sid]
            if want == "on":
                s["display_on"] = True
            elif want == "off":
                s["display_on"] = False
            elif want == "toggle":
                s["display_on"] = not s["display_on"]
            else:
                self._send(400, {"error": "state must be on, off or toggle"})
                return
            now_on = s["display_on"]
        self._send(200, {"id": sid, "display_on": now_on})

    def _handle_sim(self, path: str, query: dict) -> None:
        with _lock:
            if path == "/sim/power":
                state["powered"] = query.get("on", "true").lower() != "false"
                self._send(200, {"powered": state["powered"]})
                return

            sid = int(query.get("sensor", 1))
            if sid not in SENSOR_IDS:
                self._send(400, {"error": "sensor must be 1 or 2"})
                return

            if path == "/sim/unplug":
                unplugged = query.get("value", "true").lower() != "false"
                state["sensors"][sid]["plugged"] = not unplugged
                self._send(200, {"id": sid, "plugged": not unplugged})
                return

            if path == "/sim/temp":
                raw = query.get("value", "auto")
                state["sensors"][sid]["forced"] = None if raw == "auto" else float(raw)
                self._send(200, {"id": sid, "forced": state["sensors"][sid]["forced"]})
                return

        self._send(404, {"error": "unknown sim endpoint"})


class Server(ThreadingHTTPServer):
    """Threading server that stays quiet when a client hangs up on it.

    We speak HTTP/1.1, so clients keep connections open between requests. When
    one goes away -- the browser navigates off the page, the PC app restarts,
    someone closes a tab -- the socket is reset mid-read and the default
    handler dumps a full traceback to the console. It is harmless; the server
    keeps running. But it looks exactly like a crash, and a debugging tool that
    cries wolf is worse than no tool at all.

    Genuine bugs still print normally.
    """

    def handle_error(self, request, client_address) -> None:
        exc = sys.exc_info()[1]
        if isinstance(exc, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    threading.Thread(target=_sampler, daemon=True).start()

    # Give the ring buffer some content so the graph has history immediately,
    # exactly as a real box that has been running would.
    with _lock:
        now = time.time()
        for sid in SENSOR_IDS:
            state["history"][sid] = [
                int(round(_simulate(sid, now - (HISTORY_LEN - k)) * 100))
                for k in range(HISTORY_LEN)
            ]

    server = Server(("127.0.0.1", port), Handler)
    print(f"fake third box listening on http://127.0.0.1:{port}")
    print("set BOX_HOST=127.0.0.1 and BOX_PORT=%d in pc-app/.env" % port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping")


if __name__ == "__main__":
    main()
