"""User-editable alert settings (Requirement 7).

Requirement 7 says the two messages, the max temperature, the min temperature
and the destination address "can all be altered with the computer user
interface" -- so these cannot live in .env. They are edited through the web UI
and persisted to data/alert-settings.json so they survive a restart.

Thresholds are stored in degrees Celsius always. The UI converts for display
when the user has selected Fahrenheit; keeping one canonical unit on the server
avoids a whole class of unit-mixing bugs.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from .config import DATA_DIR

SETTINGS_PATH: Path = DATA_DIR / "alert-settings.json"


class AlertSettings(BaseModel):
    enabled: bool = True

    # Canonical units: degrees Celsius.
    min_c: float = Field(default=15.0, description="Alert when temperature falls below this")
    max_c: float = Field(default=30.0, description="Alert when temperature rises above this")

    # Email address, or a carrier SMS gateway address to reach a phone.
    recipient: str = ""

    message_low: str = "ALERT: {sensor} has dropped to {temp} (limit {limit})."
    message_high: str = "ALERT: {sensor} has risen to {temp} (limit {limit})."

    # Do not re-send the same alert more often than this.
    cooldown_s: int = 300
    # A reading must move this far back inside the limits before the sensor is
    # considered normal again. Stops a value sitting exactly on the threshold
    # from firing an alert every second.
    hysteresis_c: float = 0.5


def load() -> AlertSettings:
    if SETTINGS_PATH.exists():
        try:
            return AlertSettings.model_validate_json(SETTINGS_PATH.read_text("utf-8"))
        except (ValueError, OSError):
            # A corrupt settings file should not stop the app from starting;
            # fall back to defaults and let the user re-enter them.
            pass
    return AlertSettings()


def save(value: AlertSettings) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(value.model_dump(), indent=2), encoding="utf-8")
