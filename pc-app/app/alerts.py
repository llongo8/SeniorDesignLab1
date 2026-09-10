"""Threshold alerting to a phone by email / SMS gateway (Requirement 7)."""

from __future__ import annotations

import asyncio
import logging
import smtplib
import time
from email.message import EmailMessage
from typing import Dict, List, Optional, Set

from .config import settings
from .settings_store import AlertSettings

log = logging.getLogger(__name__)

ZONE_OK = "ok"
ZONE_LOW = "low"
ZONE_HIGH = "high"


class AlertEngine:
    """Decides when to send, and sends.

    Two guards keep a noisy sensor from turning into a hundred text messages:

    * Edge triggering -- an alert fires when a sensor *enters* an out-of-range
      zone, not for every reading while it stays there.
    * Hysteresis -- the reading has to come back inside the limit by
      `hysteresis_c` before we call the sensor normal again, so a value resting
      on the threshold does not oscillate.

    A cooldown then backstops both.
    """

    def __init__(self) -> None:
        self._zone: Dict[int, str] = {}
        self._last_sent: Dict[int, float] = {}
        self.last_error: Optional[str] = None
        self.sent_count = 0
        # Strong references to in-flight sends. Without this the event loop only
        # holds a weak reference and a task can be collected mid-send.
        self._pending: Set[asyncio.Task] = set()

    def _next_zone(self, sensor_id: int, temp_c: float, cfg: AlertSettings) -> str:
        previous = self._zone.get(sensor_id, ZONE_OK)
        h = cfg.hysteresis_c

        if previous == ZONE_HIGH:
            return ZONE_HIGH if temp_c > cfg.max_c - h else ZONE_OK
        if previous == ZONE_LOW:
            return ZONE_LOW if temp_c < cfg.min_c + h else ZONE_OK

        if temp_c > cfg.max_c:
            return ZONE_HIGH
        if temp_c < cfg.min_c:
            return ZONE_LOW
        return ZONE_OK

    async def evaluate(self, sensor_id: int, temp_c: Optional[float], cfg: AlertSettings) -> None:
        """Feed one reading in. Sends a message if this reading crosses a limit."""
        if temp_c is None:
            # No reading is not the same as an in-range reading. Forget the zone
            # so that the first good reading after an outage is judged afresh.
            self._zone.pop(sensor_id, None)
            return

        previous = self._zone.get(sensor_id, ZONE_OK)
        current = self._next_zone(sensor_id, temp_c, cfg)
        self._zone[sensor_id] = current

        if current == ZONE_OK or current == previous:
            return
        destinations = cfg.destinations()
        if not cfg.enabled or not destinations:
            return

        now = time.time()
        if now - self._last_sent.get(sensor_id, 0.0) < cfg.cooldown_s:
            log.info("sensor %d entered %s but is still in cooldown", sensor_id, current)
            return

        template = cfg.message_high if current == ZONE_HIGH else cfg.message_low
        limit_c = cfg.max_c if current == ZONE_HIGH else cfg.min_c
        body = template.format(
            sensor=f"Sensor {sensor_id}",
            temp=f"{temp_c:.1f} C",
            limit=f"{limit_c:.1f} C",
            temp_f=f"{temp_c * 9 / 5 + 32:.1f} F",
            limit_f=f"{limit_c * 9 / 5 + 32:.1f} F",
        )

        self._last_sent[sensor_id] = now

        # Fire and forget, deliberately. An SMTP exchange -- connect, STARTTLS,
        # log in, send -- takes seconds, and evaluate() is awaited from inside
        # the 1 Hz poll loop. Awaiting the send here stops polling for the whole
        # exchange: the box goes unread, and the graph grows a gap for an outage
        # that never happened. The alert is not urgent to the millisecond; the
        # sampling cadence is.
        task = asyncio.create_task(self.send(destinations, "Thermometer alert", body))
        self._pending.add(task)
        task.add_done_callback(self._pending.discard)

    async def send(self, recipients: List[str], subject: str, body: str) -> List[str]:
        """Send to every destination, returning the ones that failed.

        Each address is attempted independently: a phone whose carrier gateway
        has stopped accepting mail must not stop the email going out, and vice
        versa. A partial failure is reported but is not treated as a total one.
        """
        if not settings.smtp_configured:
            self.last_error = "SMTP is not configured -- fill in SMTP_* in pc-app/.env"
            log.warning(self.last_error)
            return list(recipients)

        try:
            failures, errors = await asyncio.to_thread(
                self._send_blocking_many, list(recipients), subject, body
            )
        except Exception as exc:  # noqa: BLE001 -- connect or login failed
            self.last_error = f"{type(exc).__name__}: {exc}"
            log.error("alert send failed before any recipient: %s", self.last_error)
            return list(recipients)

        self.sent_count += len(recipients) - len(failures)
        self.last_error = "; ".join(errors) if errors else None
        for recipient in recipients:
            if recipient not in failures:
                log.info("alert sent to %s: %s", recipient, body)
        return failures

    @staticmethod
    def _send_blocking_many(
        recipients: List[str], subject: str, body: str
    ) -> tuple[List[str], List[str]]:
        """One connection for every destination, not one each.

        Connecting, negotiating TLS and authenticating costs far more than the
        message itself, so doing it per recipient doubled the time we spent
        blocked and doubled the login burst Gmail sees. A failure on one
        recipient still leaves the others alone.
        """
        failures: List[str] = []
        errors: List[str] = []

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)

            for recipient in recipients:
                try:
                    msg = EmailMessage()
                    msg["From"] = settings.alert_from or settings.smtp_user
                    msg["To"] = recipient
                    msg["Subject"] = subject
                    msg.set_content(body)
                    smtp.send_message(msg)
                except Exception as exc:  # noqa: BLE001 -- one bad address only
                    failures.append(recipient)
                    errors.append(f"{recipient}: {type(exc).__name__}: {exc}")

        return failures, errors
