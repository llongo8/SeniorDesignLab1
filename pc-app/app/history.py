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

import time
from typing import Dict, Iterable, List, Optional, Sequence

WINDOW_S = 300


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

    def _prune(self, now: int) -> None:
        cutoff = now - self.window_s
        for bucket in self._data.values():
            stale = [t for t in bucket if t < cutoff]
            for t in stale:
                del bucket[t]
