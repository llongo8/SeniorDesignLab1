"""The 300-second rolling history behind the chart recorder.

Requirement 5c asks for a graph of the last 300 seconds, labelled in "seconds
ago", where missing data is clearly distinguishable from data that is merely
off-scale. Two design consequences follow, and both are load-bearing:

1.  Samples are keyed by absolute wall-clock second, not by array position.
    A gap in the record is then simply a second with no key, and it stays in
    the right place on the x-axis no matter how long the outage lasted. If we
    appended to a list instead, a 60-second outage would silently compress
    into nothing and the graph would lie.

2.  `series()` always returns exactly `window_s` entries, with `None` for any
    second we have no reading for. The browser draws `None` as a break in the
    trace, which is visually distinct from a value clamped to the top or the
    bottom of the fixed 10-50 C axis.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

log = logging.getLogger(__name__)

WINDOW_S = 300

# Bumped if the file layout ever changes, so an old file is ignored rather
# than misread.
FILE_VERSION = 1


class HistoryStore:
    """Sparse, second-resolution store of temperature readings."""

    def __init__(self, sensor_ids: Iterable[int] = (1, 2), window_s: int = WINDOW_S):
        self.window_s = window_s
        self._data: Dict[int, Dict[int, float]] = {sid: {} for sid in sensor_ids}

    def record(self, sensor_id: int, temp_c: Optional[float], ts: Optional[float] = None) -> None:
        """Store one live reading. `None` means no reading, so we store nothing
        and the second stays a hole."""
        now = int(ts if ts is not None else time.time())
        if temp_c is not None:
            self._data[sensor_id][now] = float(temp_c)
        self._prune(now)

    def backfill(
        self,
        sensor_id: int,
        samples_c: Sequence[Optional[float]],
        end_ts: Optional[float] = None,
    ) -> None:
        """Absorb the ring buffer the box hands us on connect.

        `samples_c` is oldest-first at 1 Hz, with the last entry being the most
        recent sample. This is what lets the graph show 300 s of history within
        10 s of the PC software starting (Req 5c) and within 10 s of the box
        being switched on (Req 6).

        Live readings win over backfilled ones: we only fill seconds we have
        nothing for, because our own timestamps are more trustworthy than an
        offset computed from the box uptime.
        """
        end = int(end_ts if end_ts is not None else time.time())
        n = len(samples_c)
        bucket = self._data[sensor_id]
        for k, value in enumerate(samples_c):
            if value is None:
                continue
            bucket.setdefault(end - (n - 1 - k), float(value))
        self._prune(end)

    def series(self, sensor_id: int, now: Optional[float] = None) -> List[Optional[float]]:
        """Exactly `window_s` values, oldest first.

        Index 0 is (window_s - 1) seconds ago; the last index is the current
        second. `None` marks a second with no data.
        """
        end = int(now if now is not None else time.time())
        bucket = self._data[sensor_id]
        first = end - self.window_s + 1
        return [bucket.get(t) for t in range(first, end + 1)]

    def save(self, path: Path, box: str) -> None:
        """Write the store to disk.

        Called every few seconds, not only at shutdown: the server is as likely
        to be killed (terminal closed, process ended) as stopped cleanly, and a
        kill runs no shutdown code. The write goes to a temporary file that then
        replaces the real one, so a kill mid-write leaves the previous save
        intact rather than a half-written file.
        """
        payload = {
            "version": FILE_VERSION,
            "box": box,
            "sensors": {
                str(sid): {str(t): v for t, v in bucket.items()}
                for sid, bucket in self._data.items()
            },
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        os.replace(tmp, path)

    def load(self, path: Path, box: str) -> int:
        """Restore a previous save, returning how many readings came back.

        Anything that does not fit is dropped rather than trusted: a corrupt
        file, readings older than the window, or a file saved while talking to
        a different box. That last one matters most. Pointing BOX_HOST at the
        simulator and back must never put simulated readings on the real graph.

        Call before the poller starts. Its backfill only fills seconds that are
        still empty, so the restored readings survive it and the box's ring
        buffer fills in whatever the server missed while it was down.
        """
        if not path.exists():
            return 0
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("version") != FILE_VERSION:
                log.info("ignoring history file %s: unknown format", path)
                return 0
            if payload.get("box") != box:
                log.info("ignoring history file %s: it was saved for %s, not %s",
                         path, payload.get("box"), box)
                return 0
            saved = {
                int(sid): {int(t): float(v) for t, v in bucket.items() if v is not None}
                for sid, bucket in payload["sensors"].items()
            }
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            # A damaged file should not stop the app from starting.
            log.warning("ignoring unreadable history file %s: %s", path, exc)
            return 0

        cutoff = int(time.time()) - self.window_s
        restored = 0
        for sid, bucket in saved.items():
            if sid not in self._data:
                continue
            for t, value in bucket.items():
                if t >= cutoff:
                    self._data[sid][t] = value
                    restored += 1
        return restored

    def _prune(self, now: int) -> None:
        cutoff = now - self.window_s
        for bucket in self._data.values():
            stale = [t for t in bucket if t < cutoff]
            for t in stale:
                del bucket[t]
