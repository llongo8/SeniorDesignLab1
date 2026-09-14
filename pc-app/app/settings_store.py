"""User-editable alert settings (Requirement 7).

Requirement 7 says the two messages, the max temperature, the min temperature
and the destination address "can all be altered with the computer user
interface" -- so these cannot live in .env. They are edited through the web UI
and persisted to data/alert-settings.json so they survive a restart.

Thresholds are stored in degrees Celsius always. The UI converts for display
when the user has selected Fahrenheit; keeping one canonical unit on the server
avoids a whole class of unit-mixing bugs.

Alerts go by email only. An SMS path through carrier email-to-SMS gateways was
built and worked, then the gateway began silently dropping messages while email
stayed reliable -- see docs/00-requirements-traceability.md. Requirement 1d asks
for a phone receiving "text messages **or** emails" and Requirement 7 says
"text/email", both disjunctive, so email read on the phone satisfies them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List

from pydantic import BaseModel, Field, model_validator

from .config import DATA_DIR

SETTINGS_PATH: Path = DATA_DIR / "alert-settings.json"


class AlertSettings(BaseModel):
    enabled: bool = True

    # Canonical units: degrees Celsius.
    min_c: float = Field(default=15.0, description="Alert when temperature falls below this")
    max_c: float = Field(default=30.0, description="Alert when temperature rises above this")

    # Where alerts go. Requirement 7 requires this to be editable from the UI.
    email_to: str = ""

    @model_validator(mode="before")
    @classmethod
    def _migrate_old_fields(cls, data: Any) -> Any:
        """Carry older settings files forward.

        `recipient` was the single destination field before email and SMS were
        split apart. A gateway address stored there is still a perfectly good
        email address, so it moves across unchanged. Leftover `sms_number` and
        `sms_carrier` keys are ignored by pydantic and simply disappear on the
        next save.
        """
        if isinstance(data, dict) and data.get("recipient") and not data.get("email_to"):
            data = dict(data)
            data["email_to"] = (data.pop("recipient") or "").strip()
        return data

    def destinations(self) -> List[str]:
        """Everywhere an alert should go. A list rather than a single address so
        the send path and the test endpoint can report per-destination results
        without caring how many there are."""
        return [self.email_to.strip()] if self.email_to.strip() else []

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
