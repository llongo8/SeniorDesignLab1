"""FastAPI application for the PC side of the thermometer (Requirements 5-7).

Run it with:

    uvicorn app.main:app --reload --port 8000

then open http://localhost:8000.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import settings_store
from .alerts import AlertEngine
from .config import STATIC_DIR, settings
from .history import WINDOW_S, HistoryStore
from .poller import SENSOR_IDS, BoxPoller

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
log = logging.getLogger("app")

history = HistoryStore(SENSOR_IDS)
alerts = AlertEngine()
poller = BoxPoller(history, alerts)

# How often the graph history is written to disk. A kill loses at most this
# much, and usually nothing: if the box stayed up, its ring buffer fills the
# missing seconds back in on the next start.
HISTORY_SAVE_PERIOD_S = 5.0


def _box_id() -> str:
    return f"{settings.box_host}:{settings.box_port}"


def _save_history() -> None:
    try:
        history.save(settings.history_file, _box_id())
    except OSError as exc:
        log.warning("could not save history to %s: %s", settings.history_file, exc)


async def _save_history_periodically() -> None:
    while True:
        await asyncio.sleep(HISTORY_SAVE_PERIOD_S)
        _save_history()


def _quiet_connection_reset(loop: asyncio.AbstractEventLoop, context: dict) -> None:
    """Swallow the traceback Windows prints when a browser tab goes away.

    The proactor event loop reports ConnectionResetError from a half-closed
    socket through the loop exception handler, which prints a full traceback for
    something entirely normal: a client closed the page mid-response. Nothing is
    broken and the server carries on, but the log then looks like a crash, and a
    log that cries wolf is one nobody reads. Real errors still print.
    """
    if isinstance(context.get("exception"), ConnectionResetError):
        return
    loop.default_exception_handler(context)


@asynccontextmanager
async def lifespan(_: FastAPI):
    asyncio.get_running_loop().set_exception_handler(_quiet_connection_reset)
    restored = history.load(settings.history_file, _box_id())
    if restored:
        log.info("restored %d readings from %s", restored, settings.history_file)
    tasks = [
        asyncio.create_task(poller.run(), name="box-poller"),
        asyncio.create_task(_save_history_periodically(), name="history-saver"),
    ]
    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        await poller.aclose()
        # A clean stop (Ctrl+C) saves right up to the last second. A kill never
        # reaches this line, which is why the periodic save exists at all.
        _save_history()


app = FastAPI(title="ECE:4880 Lab 1 Thermometer", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/live")
async def live() -> dict:
    """Everything the big readout needs, once a second."""
    snap = poller.snapshot
    # `box` and `simulated` are reported so the page can never leave you
    # guessing whether a reading came from a probe or from tools/fake_box.py.
    # Mistaking simulated data for real data is the most expensive confusion
    # available in this project.
    return {
        "box_online": snap.online,
        "box_error": snap.last_error,
        "firmware": snap.firmware,
        "box": f"{settings.box_host}:{settings.box_port}",
        "simulated": (snap.firmware or "").startswith("fake"),
        "sensors": [
            {
                "id": sid,
                "present": s.present,
                "display_on": s.display_on,
                "temp_c": s.temp_c,
            }
            for sid, s in sorted(snap.sensors.items())
        ],
        "alerts": {
            "smtp_configured": settings.smtp_configured,
            "sent_count": alerts.sent_count,
            "last_error": alerts.last_error,
        },
    }


@app.get("/api/series")
async def series() -> dict:
    """The 300-second window for the chart recorder.

    Values are Celsius; `null` is a second with no data. The browser converts to
    Fahrenheit when asked, so the server only ever deals in one unit.
    """
    return {
        "window_s": WINDOW_S,
        "sensors": [
            {"id": sid, "values_c": history.series(sid)} for sid in sorted(SENSOR_IDS)
        ],
    }


@app.post("/api/button/{sensor_id}")
async def button(sensor_id: int, state: str = "toggle") -> dict:
    """Requirement 5b: virtually press a button on the third box."""
    if sensor_id not in SENSOR_IDS:
        raise HTTPException(status_code=404, detail="unknown sensor")
    if state not in ("on", "off", "toggle"):
        raise HTTPException(status_code=400, detail="state must be on, off or toggle")
    try:
        return await poller.press_button(sensor_id, state)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"third box unreachable: {exc}") from exc


@app.get("/api/settings")
async def get_settings() -> settings_store.AlertSettings:
    return settings_store.load()


@app.put("/api/settings")
async def put_settings(value: settings_store.AlertSettings) -> settings_store.AlertSettings:
    if value.min_c >= value.max_c:
        raise HTTPException(status_code=400, detail="minimum must be below maximum")
    settings_store.save(value)
    log.info("alert settings updated: %s", value.model_dump())
    return value


@app.post("/api/alerts/test")
async def test_alert() -> dict:
    """Send to every configured destination, so the team can prove delivery
    works before the demo rather than during it."""
    cfg = settings_store.load()
    destinations = cfg.destinations()
    if not destinations:
        raise HTTPException(
            status_code=400,
            detail="No destination set. Add an email address in the Alerts panel.",
        )

    failures = await alerts.send(
        destinations,
        "Thermometer test",
        "Test message from the ECE:4880 Lab 1 thermometer. If you can read this, alerting works.",
    )
    delivered = [d for d in destinations if d not in failures]

    if failures and not delivered:
        raise HTTPException(status_code=502, detail=alerts.last_error or "all destinations failed")
    return {"delivered": delivered, "failed": failures, "error": alerts.last_error}
