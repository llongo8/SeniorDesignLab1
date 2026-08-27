#!/usr/bin/env python3
"""End-to-end check of the PC application against the simulator.

This drives the fault-injection endpoints of tools/fake_box.py and asserts that
the PC app reacts the way the handout requires. It is the fastest way to know
that a change has not broken one of the error paths, which are exactly the
paths nobody remembers to test by hand.

Run all three in separate terminals:

    python tools/fake_box.py
    uvicorn app.main:app --port 8000
    python tools/smoke_test.py

Requirements covered: 5a.i, 5a.ii, 5b, 5c, 5c.iv, 6.
"""

from __future__ import annotations

import sys
import time
import urllib.request
import json
from typing import Optional

APP = "http://127.0.0.1:8000"
BOX = "http://127.0.0.1:8080"

passed = 0
failed = 0


def get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read())


def post(url: str) -> dict:
    request = urllib.request.Request(url, method="POST")
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read())


def check(label: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {label}")
    else:
        failed += 1
        print(f"  FAIL  {label}   {detail}")


def wait_for(predicate, timeout_s: float, label: str) -> Optional[dict]:
    """Poll until the predicate holds, returning the payload that satisfied it.

    The timeout is the requirement being tested, not a convenience -- Req 6
    gives us 10 s for the display to come back after the box is switched on.
    """
    deadline = time.monotonic() + timeout_s
    payload = None
    while time.monotonic() < deadline:
        payload = get(f"{APP}/api/live")
        if predicate(payload):
            elapsed = timeout_s - (deadline - time.monotonic())
            print(f"  ....  {label} after {elapsed:.1f} s")
            return payload
        time.sleep(0.4)
    return None


def series_nulls(sensor_id: int, last_n: int = 300) -> int:
    """Missing seconds in the most recent `last_n` seconds of the window.

    Scoped to a recent slice on purpose: the 300 s window can still contain
    gaps from an earlier part of this run, and an assertion that accidentally
    depends on those is an assertion that fails for the wrong reason.
    """
    data = get(f"{APP}/api/series")
    for sensor in data["sensors"]:
        if sensor["id"] == sensor_id:
            return sum(1 for v in sensor["values_c"][-last_n:] if v is None)
    return -1


def main() -> int:
    print("Reset simulator to a known good state")
    get(f"{BOX}/sim/power?on=true")
    get(f"{BOX}/sim/unplug?sensor=1&value=false")
    get(f"{BOX}/sim/unplug?sensor=2&value=false")
    get(f"{BOX}/sim/temp?sensor=1&value=auto")
    get(f"{BOX}/sim/temp?sensor=2&value=auto")
    wait_for(lambda p: p["box_online"] and all(s["present"] for s in p["sensors"]), 15, "steady state")

    # From here on the box is on and both probes are plugged in, so anything we
    # assert about seconds after this instant is under our control. Seconds
    # BEFORE it are not: the 300 s window can still hold real outages from an
    # earlier run, faithfully restored from the ring buffer of the box.
    controlled_start = time.monotonic()

    def controlled_window(cap: int = 30) -> int:
        return max(1, min(cap, int(time.monotonic() - controlled_start)))

    print("\nReq 5c -- 300 s of history is available immediately")
    series = get(f"{APP}/api/series")
    check("window is 300 s", series["window_s"] == 300)
    for sensor in series["sensors"]:
        check(
            f"sensor {sensor['id']} returns exactly 300 points",
            len(sensor["values_c"]) == 300,
            f"got {len(sensor['values_c'])}",
        )

    print("\nReq 5b -- the computer can press the buttons on the box")
    before = get(f"{APP}/api/live")["sensors"][0]["display_on"]
    started = time.monotonic()
    result = post(f"{APP}/api/button/1?state={'off' if before else 'on'}")
    elapsed = time.monotonic() - started
    check("button state changed", result["display_on"] != before, str(result))
    check(f"button responded in under 1 s ({elapsed*1000:.0f} ms)", elapsed < 1.0)

    print("\nReq 5a.i -- an unplugged probe is reported as unplugged")
    get(f"{BOX}/sim/unplug?sensor=1&value=true")
    live = wait_for(
        lambda p: not p["sensors"][0]["present"], 10, "sensor 1 reported unplugged"
    )
    check("sensor 1 present is false", live is not None and not live["sensors"][0]["present"])
    check("sensor 1 temperature is null", live is not None and live["sensors"][0]["temp_c"] is None)
    check("box is still online", live is not None and live["box_online"])
    check("sensor 2 is unaffected", live is not None and live["sensors"][1]["present"])

    print("\nReq 5c.iv -- the gap shows up in the graph as missing data")
    time.sleep(5)
    nulls = series_nulls(1, last_n=4)
    check(f"sensor 1 shows the outage as missing seconds ({nulls} of the last 4)", nulls >= 3)

    # Sensor 2 was never touched during the part of the window we control.
    span = controlled_window()
    quiet = series_nulls(2, last_n=span)
    check(f"sensor 2 kept recording throughout ({quiet} missing in the last {span} s)", quiet == 0)

    get(f"{BOX}/sim/unplug?sensor=1&value=false")
    wait_for(lambda p: p["sensors"][0]["present"], 10, "sensor 1 recovered on replug")
    check("sensor 1 recovered with no user intervention", get(f"{APP}/api/live")["sensors"][0]["present"])

    print("\nReq 5a.ii -- box switched off means no data available")
    get(f"{BOX}/sim/power?on=false")
    live = wait_for(lambda p: not p["box_online"], 10, "box reported offline")
    check("box_online is false", live is not None and not live["box_online"])
    check("an error reason is reported", bool(live and live["box_error"]))

    print("\nReq 6 -- switching the box back on restores everything within 10 s")
    get(f"{BOX}/sim/power?on=true")
    started = time.monotonic()
    live = wait_for(
        lambda p: p["box_online"] and all(s["present"] for s in p["sensors"]),
        10,
        "box back online",
    )
    elapsed = time.monotonic() - started
    check(f"recovered in under 10 s ({elapsed:.1f} s)", live is not None and elapsed < 10.0)
    series = get(f"{APP}/api/series")
    check("history is being served again", len(series["sensors"][0]["values_c"]) == 300)

    # Regression test for sample-time drift. The history is keyed by whole
    # seconds, so if the poll loop ever comes unstuck from the second boundary
    # it silently skips seconds, and the graph grows gaps in data that was
    # actually collected perfectly. Twenty uninterrupted seconds is enough to
    # catch that: the old fixed-delay loop dropped roughly one second in five.
    print("\nReq 5c.iv -- continuous running must not manufacture gaps")
    observe_s = 20
    print(f"  ....  watching {observe_s} s of uninterrupted operation")
    time.sleep(observe_s)
    for sensor_id in (1, 2):
        gaps = series_nulls(sensor_id, last_n=observe_s - 4)
        check(f"sensor {sensor_id} has no phantom gaps ({gaps} missing)", gaps == 0)

    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
