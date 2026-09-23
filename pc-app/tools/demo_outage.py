#!/usr/bin/env python3
"""Run the UI against the simulator with outages on a loop, for screenshots.

Starts everything needed and drives the simulator so the graph always shows
data, then a cut-out, then a recovery:

    python tools/demo_outage.py      # then open http://127.0.0.1:8000

Two different outages alternate, because they are two different requirements
and they draw differently:

* one probe unplugged  -> that trace breaks, hatched no-data band  (5a.i, 5c.iv)
* the whole box off    -> both traces stop, "no data available"    (5a.ii, 6)

The cycle is shorter than the 300 s window, so several outages are on screen at
once and nothing scrolls away before you can capture it. Ctrl+C stops
everything it started.

The readings are simulated and the page says so, in amber, at the top. Leave
that badge in any screenshot. For requirement evidence use a capture from the
real hardware instead -- T-5c.iv already has one from the ice bath.

Nothing here touches the real box or the history saved for it: the app is
pointed at the simulator and writes to its own history file, and mail is
switched off so a simulated reading cannot raise a real alert.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
PY = sys.executable
APP_URL = "http://127.0.0.1:8000"
SIM_URL = "http://127.0.0.1:8080"

DEMO_HISTORY = Path(tempfile.gettempdir()) / "thermobox-demo-history.json"
LOG_DIR = Path(tempfile.gettempdir())

# seconds: (label, how long)
CYCLE = [
    ("normal", 40),
    ("probe 1 unplugged", 12),
    ("normal", 25),
    ("box switched off", 12),
]


def sim(path: str) -> None:
    try:
        urllib.request.urlopen(SIM_URL + path, timeout=4).read()
    except Exception as exc:  # noqa: BLE001 -- the demo is not worth crashing for
        print("   (simulator call failed: %s)" % exc, flush=True)


def wait_for_app(limit: float = 30.0) -> bool:
    deadline = time.time() + limit
    while time.time() < deadline:
        try:
            urllib.request.urlopen(APP_URL + "/api/live", timeout=2).read()
            return True
        except Exception:
            time.sleep(0.5)
    return False


def main() -> int:
    if DEMO_HISTORY.exists():
        DEMO_HISTORY.unlink()

    env = dict(os.environ)
    env.update(
        BOX_HOST="127.0.0.1",
        BOX_PORT="8080",
        HISTORY_FILE=str(DEMO_HISTORY),
        # No mail: a simulated 40 C must not send a real alert.
        SMTP_HOST="",
        SMTP_USER="",
        SMTP_PASSWORD="",
    )

    sim_log = open(LOG_DIR / "thermobox-demo-sim.log", "wb")
    app_log = open(LOG_DIR / "thermobox-demo-app.log", "wb")

    print("starting the simulator and the web app...", flush=True)
    children = [
        subprocess.Popen([PY, "tools/fake_box.py"], cwd=APP_DIR,
                         stdout=sim_log, stderr=subprocess.STDOUT),
        subprocess.Popen([PY, "-m", "uvicorn", "app.main:app",
                          "--port", "8000", "--host", "127.0.0.1"],
                         cwd=APP_DIR, env=env, stdout=app_log, stderr=subprocess.STDOUT),
    ]

    try:
        if not wait_for_app():
            print("the app did not start; see %s" % (LOG_DIR / "thermobox-demo-app.log"))
            return 1

        # A step on sensor 2 so the two traces are easy to tell apart.
        sim("/sim/temp?sensor=2&value=40")

        print("", flush=True)
        print("  OPEN  %s" % APP_URL, flush=True)
        print("", flush=True)
        print("  Outages repeat, so there is always one on the graph.", flush=True)
        print("  Screenshot whenever you like. Ctrl+C stops everything.", flush=True)
        print("", flush=True)

        while True:
            for label, seconds in CYCLE:
                if label == "probe 1 unplugged":
                    sim("/sim/unplug?sensor=1&value=true")
                elif label == "box switched off":
                    sim("/sim/power?on=false")
                else:
                    sim("/sim/unplug?sensor=1&value=false")
                    sim("/sim/power?on=true")

                print("  %s  %-20s (%d s)"
                      % (time.strftime("%H:%M:%S"), label, seconds), flush=True)
                time.sleep(seconds)

    except KeyboardInterrupt:
        print("\nstopping...", flush=True)
    finally:
        # Put the simulator back before shutting down, so a later run of the
        # smoke test does not start against a box that is switched off.
        sim("/sim/unplug?sensor=1&value=false")
        sim("/sim/power?on=true")
        for child in children:
            child.terminate()
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
        sim_log.close()
        app_log.close()
        print("stopped. the real box and its saved history were never touched.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
