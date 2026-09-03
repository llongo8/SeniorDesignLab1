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


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(poller.run(), name="box-poller")
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        await poller.aclose()


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


@app.get("/api/carriers")
async def carriers() -> list[dict]:
    """The carrier dropdown. Served from the server so the gateway table has one
    home -- a phone number alone cannot identify a carrier, so the user picks."""
    return settings_store.carrier_choices()


@app.post("/api/settings/preview-sms")
async def preview_sms(body: dict) -> dict:
    """Resolve a number and carrier to a gateway address without saving.

    The UI could build this string itself, but then the normalisation rules --
    stripping punctuation, tolerating a leading country code, the gateway table
    -- would exist in two places and drift apart.
    """
    probe = settings_store.AlertSettings(
        sms_number=str(body.get("sms_number", "")),
        sms_carrier=str(body.get("sms_carrier", "")),
    )
    return {"sms_address": probe.sms_address}


@app.post("/api/alerts/test")
async def test_alert() -> dict:
    """Send to every configured destination, so the team can prove delivery
    works before the demo rather than during it."""
    cfg = settings_store.load()
    destinations = cfg.destinations()
    if not destinations:
        raise HTTPException(
            status_code=400,
            detail="No destination set. Add an email address, or a phone number and its carrier.",
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
