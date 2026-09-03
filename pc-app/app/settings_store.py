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
import re
from pathlib import Path
from typing import Any, Dict, List

from pydantic import BaseModel, Field, computed_field, model_validator

from .config import DATA_DIR

SETTINGS_PATH: Path = DATA_DIR / "alert-settings.json"

# Email-to-SMS gateways for the US carriers a class in Iowa is likely to be on.
#
# There is no free way to go from a bare phone number to a carrier: the gateway
# domain IS the carrier, so the carrier has to be known before an address can be
# built. Paid lookup APIs exist (Twilio Lookup and similar) but they cost money,
# need an account, and number portability means they can still be wrong. A
# dropdown the user picks once is free, exact, and takes two seconds.
#
# These domains do change, and carriers have been quietly retiring the service.
# Test delivery early rather than discovering it at checkoff.
SMS_GATEWAYS: Dict[str, str] = {
    "att": "txt.att.net",
    "verizon": "vtext.com",
    "tmobile": "tmomail.net",
    "uscellular": "email.uscc.net",
    "cricket": "sms.cricketwireless.net",
    "boost": "sms.myboostmobile.com",
    "metro": "mymetropcs.com",
    "googlefi": "msg.fi.google.com",
    "consumercellular": "mailmymobile.net",
    "tracfone": "mmst5.tracfone.com",
}

CARRIER_LABELS: Dict[str, str] = {
    "att": "AT&T",
    "verizon": "Verizon",
    "tmobile": "T-Mobile",
    "uscellular": "US Cellular",
    "cricket": "Cricket",
    "boost": "Boost Mobile",
    "metro": "Metro by T-Mobile",
    "googlefi": "Google Fi",
    "consumercellular": "Consumer Cellular",
    "tracfone": "TracFone",
}


def carrier_choices() -> List[Dict[str, str]]:
    """For the dropdown. Served by the API so the list lives in one place."""
    return [{"id": k, "label": CARRIER_LABELS[k]} for k in SMS_GATEWAYS]


class AlertSettings(BaseModel):
    enabled: bool = True

    # Canonical units: degrees Celsius.
    min_c: float = Field(default=15.0, description="Alert when temperature falls below this")
    max_c: float = Field(default=30.0, description="Alert when temperature rises above this")

    # Requirement 7 names "phone number/email address" as the destination, so
    # they are two fields rather than one box the user has to know how to fill.
    # Both are optional; alerts go to whichever are set.
    email_to: str = ""
    sms_number: str = ""     # digits as typed; normalised on the way out
    sms_carrier: str = ""    # a key of SMS_GATEWAYS

    @model_validator(mode="before")
    @classmethod
    def _migrate_recipient(cls, data: Any) -> Any:
        """Older settings files had a single `recipient` holding either an email
        address or a hand-typed SMS gateway address.

        A gateway address is split back into the number and carrier fields,
        where it now belongs -- otherwise it would sit in the email box looking
        like an email, and the phone fields would look unconfigured.
        """
        if not (isinstance(data, dict) and "recipient" in data and not data.get("email_to")):
            return data

        data = dict(data)
        old = (data.pop("recipient") or "").strip()
        local, _, domain = old.partition("@")

        for key, gateway in SMS_GATEWAYS.items():
            if domain.lower() == gateway and local.isdigit():
                data.setdefault("sms_number", local)
                data.setdefault("sms_carrier", key)
                return data

        data["email_to"] = old
        return data

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sms_address(self) -> str:
        """The gateway address the phone number and carrier resolve to, or "" if
        either is missing or the number is not 10 digits. Exposed so the UI can
        show exactly what will be sent to rather than leaving it a mystery."""
        digits = re.sub(r"\D", "", self.sms_number or "")
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]          # tolerate a leading country code
        domain = SMS_GATEWAYS.get(self.sms_carrier or "")
        if len(digits) != 10 or not domain:
            return ""
        return f"{digits}@{domain}"

    def destinations(self) -> List[str]:
        """Everywhere an alert should go. Requirement 7 is satisfied by either
        channel, but nothing stops us using both."""
        out = []
        if self.email_to.strip():
            out.append(self.email_to.strip())
        if self.sms_address:
            out.append(self.sms_address)
        return out

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
