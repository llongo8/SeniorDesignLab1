"""Polls the third box once a second and keeps the PC-side picture of the world.

Why polling rather than a websocket: every timing requirement in the handout is
generous (1 s updates, sub-1 s button response, 10 s to first graph), and a
plain request/response loop is dramatically easier to reason about, to test
against the simulator, and to debug with a browser when something misbehaves on
demo day. A websocket would buy latency we are not asked for and cost us a
reconnection state machine we would have to get right.
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

import httpx

from .alerts import AlertEngine
from .config import settings
from .history import HistoryStore
from . import settings_store

log = logging.getLogger(__name__)

SENSOR_IDS = (1, 2)

# Requirement 5a.ii: if the box switch is off the UI must say "no data
# available". We allow a couple of missed polls before declaring it off, so a
# single dropped WiFi packet does not flicker the whole display.
OFFLINE_AFTER_S = 3.0

# Where inside each wall-clock second we take our sample.
#
# The history is keyed by whole seconds, so the poll loop has to stay locked to
# the second boundary. Sleeping for "one second minus however long the work
# took" is not enough: scheduling jitter makes the sample time wander, and the
# moment two consecutive samples land in the same integer second, the next
# second gets no sample at all and the graph grows a gap that never happened.
# Aiming at x.10 instead absorbs +/-100 ms of jitter without ever changing which
# second a sample belongs to.
TICK_PHASE_S = 0.10


@dataclass
class SensorSnapshot:
    present: bool = False
    display_on: bool = False
    temp_c: Optional[float] = None


@dataclass
class BoxSnapshot:
    online: bool = False
    last_error: Optional[str] = None
    last_success_ts: float = 0.0
    firmware: Optional[str] = None
    sensors: Dict[int, SensorSnapshot] = field(
        default_factory=lambda: {sid: SensorSnapshot() for sid in SENSOR_IDS}
    )


class BoxPoller:
    def __init__(self, history: HistoryStore, alerts: AlertEngine) -> None:
        self.history = history
        self.alerts = alerts
        self.snapshot = BoxSnapshot()
        self._client = httpx.AsyncClient(
            base_url=settings.box_base_url,
            timeout=settings.box_timeout_s,
        )
        # Set whenever we (re)establish contact, so we pull the box ring buffer
        # and can draw 300 s of history immediately. Req 5c and Req 6.
        self._need_backfill = True

    async def aclose(self) -> None:
        await self._client.aclose()

    async def run(self) -> None:
        log.info("polling third box at %s", settings.box_base_url)
        while True:
            try:
                await self.tick(time.time())
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 -- the poll loop must never die
                log.exception("unhandled error in poll loop")

            # Sleep to the next second boundary, not for a fixed duration.
            # A tick that overran simply lands on the following boundary.
            now = time.time()
            await asyncio.sleep(max(0.0, math.floor(now) + 1 + TICK_PHASE_S - now))

    async def tick(self, tick_ts: float) -> None:
        """Run one poll. `tick_ts` is the instant the tick fired, and is the
        timestamp every reading from it is filed under -- so the second a sample
        belongs to never depends on how long the HTTP request happened to take."""
        try:
            response = await self._client.get("/api/state")
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # noqa: BLE001
            self._mark_unreachable(exc)
            return

        was_offline = not self.snapshot.online
        self.snapshot.online = True
        self.snapshot.last_error = None
        self.snapshot.last_success_ts = time.time()
        self.snapshot.firmware = payload.get("fw")

        if was_offline:
            log.info("third box is online")
            self._need_backfill = True

        if self._need_backfill:
            await self._backfill(tick_ts)

        cfg = settings_store.load()
        for entry in payload.get("sensors", []):
            sid = int(entry["id"])
            if sid not in self.snapshot.sensors:
                continue
            temp_c = entry.get("temp_c") if entry.get("present") else None
            self.snapshot.sensors[sid] = SensorSnapshot(
                present=bool(entry.get("present")),
                display_on=bool(entry.get("display_on")),
                temp_c=temp_c,
            )
            self.history.record(sid, temp_c, ts=tick_ts)
            await self.alerts.evaluate(sid, temp_c, cfg)

    @staticmethod
    def _describe(exc: BaseException) -> str:
        """Turn an httpx exception into something worth putting on screen.

        The default rendering was `f"{type(exc).__name__}: {exc}"`, which for a
        connect timeout produces "ConnectTimeout:" -- a bare class name and a
        colon with nothing after it, because those exceptions carry no message.
        On the demo screen that reads as a broken string rather than a
        diagnosis, and it does not tell anyone what to go and check.
        """
        if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout)):
            return f"cannot reach the box at {settings.box_host} — check it is powered and on this network"
        if isinstance(exc, httpx.TimeoutException):
            return f"the box at {settings.box_host} accepted the connection but did not reply in time"
        detail = str(exc).strip()
        return f"{type(exc).__name__}: {detail}" if detail else type(exc).__name__

    def _mark_unreachable(self, exc: BaseException) -> None:
        self.snapshot.last_error = self._describe(exc)
        if time.time() - self.snapshot.last_success_ts > OFFLINE_AFTER_S:
            if self.snapshot.online:
                log.warning("third box unreachable: %s", self.snapshot.last_error)
            self.snapshot.online = False
            self._need_backfill = True
            for snap in self.snapshot.sensors.values():
                snap.present = False
                snap.temp_c = None

    async def _backfill(self, end_ts: float) -> None:
        """Pull the box 300-sample ring buffer into our history store."""
        try:
            response = await self._client.get("/api/history", timeout=5.0)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # noqa: BLE001
            log.warning("history backfill failed, will retry: %s", exc)
            return

        end = end_ts
        for entry in payload.get("sensors", []):
            sid = int(entry["id"])
            if sid not in self.snapshot.sensors:
                continue
            raw = entry.get("samples_c100", [])
            samples = [None if v is None else v / 100.0 for v in raw]
            self.history.backfill(sid, samples, end_ts=end)

        self._need_backfill = False
        log.info("backfilled %d samples of history from the box", payload.get("len", 0))

    async def press_button(self, sensor_id: int, state: str) -> dict:
        """Requirement 5b: the computer virtually presses a button on the box."""
        response = await self._client.post(
            "/api/button",
            params={"sensor": sensor_id, "state": state},
            timeout=2.0,
        )
        response.raise_for_status()
        result = response.json()
        # Reflect the new state immediately rather than waiting up to a second
        # for the next poll -- Req 5b allows under one second end to end.
        if sensor_id in self.snapshot.sensors:
            self.snapshot.sensors[sensor_id].display_on = bool(result.get("display_on"))
        return result
