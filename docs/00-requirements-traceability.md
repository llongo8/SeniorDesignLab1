# Requirements Traceability Matrix

Every numbered requirement from *Laboratory #1, ECE:4880, Fall 2026*, mapped to the design
element that satisfies it and the test that proves it.

**This is the master checklist.** Update it in the same pull request that implements or tests a
requirement. When we hand in the report, this table is the evidence that we met the spec, and the
handout is explicit that documentation quality largely determines the grade.

Status key: **DONE** verified · **SW** software complete, needs hardware to verify ·
**TODO** not started · **ASK** needs clarification from the instructors

---

## 1. General description

| # | Requirement | How we satisfy it | Where | Verified by | Status |
|---|---|---|---|---|---|
| 1a | PC for user interface, display, control | FastAPI service + browser UI | [`pc-app/`](../pc-app/) | `smoke_test.py` | DONE |
| 1b | Two probes, 1.0 ±0.1 m cable, robust, survive ice water | DS18B20 sealed stainless probes, 1 m lead, strain relief at both ends | [BOM](02-bill-of-materials.md) | T-8d ice bath | TODO |
| 1c | Third box: display, buttons, battery, power switch; battery operated; data on internet | ESP32 + 16x2 LCD1602 + 2 buttons + 18650 pack + SPDT panel switch; WiFi station serving JSON | [`firmware/`](../firmware/) | T-3, T-4 | SW |
| 1d | Cellphone receives texts/emails | SMTP email; carrier SMS gateway address for texts | [`alerts.py`](../pc-app/app/alerts.py) | T-7 | SW |

## 2. Mechanical requirements of the third box

| # | Requirement | How we satisfy it | Where | Verified by | Status |
|---|---|---|---|---|---|
| 2a | Enclosed, survives a drop from the bench, works upside down | ABS project box, PCB and battery mechanically fastened (not loose), no gravity-dependent parts | [Design §6](01-system-design.md) | T-2a drop test | TODO |
| 2b | Panel-mounted connectors, easy for a casual user | GX12-3 panel connectors, nut-secured through the enclosure wall | [BOM](02-bill-of-materials.md) | T-2b | TODO |
| 2c | Dropped with cables attached, nothing breaks (disconnection is OK) | Connectors chosen to pull free rather than transmit shock to the PCB; internal wiring strain-relieved | [Design §6](01-system-design.md) | T-2c | TODO |
| 2d | Sensor unplugged and replugged, normal operation resumes with no user action | Each probe on its own 1-Wire bus; `pollRediscovery()` re-enumerates a silent bus every 2 s and restores resolution automatically | [`main.cpp` `pollRediscovery`](../firmware/src/main.cpp) | T-2d, smoke test | SW |

## 3. Power switch

| # | Requirement | How we satisfy it | Where | Verified by | Status |
|---|---|---|---|---|---|
| 3 | Switch off: no display, and no temperature data available from the internet | A hard mechanical break in the battery line, so the whole box is unpowered. Nothing can serve data because nothing is running. The PC then shows "no data available". Implemented with a 3-terminal SPDT wired as on/off (common + one throw). | [Design §5](01-system-design.md) | T-3 | SW |

## 4. Local features at the third box

| # | Requirement | How we satisfy it | Where | Verified by | Status |
|---|---|---|---|---|---|
| 4a | Correct temperature appears when the button is pressed, no delay above ~20 ms **(MEASURED 7.3 ms)** | Buttons polled at the top of `loop()` and again after the 1-Wire read; the display is repainted straight from the debounce edge using the cached reading, never waiting for the next sample tick. A full 32-character LCD refresh measures 7.3 ms against the 20 ms budget. Worst case measured at runtime, printed on serial and reported at `GET /api/info`. | [`main.cpp` `pollButtons`](../firmware/src/main.cpp), [`config.h`](../firmware/include/config.h) | T-4a scope capture | SW |
| 4b | Readable under normal indoor lighting, all in-range temperatures shown correctly | Blue negative-mode LCD1602, backlit from 5 V. One 16-character row per sensor, so the screen shows the handout wording ("Sensor 1 off") rather than an abbreviation | [`main.cpp` `formatRow`](../firmware/src/main.cpp) | T-4b | SW |
| 4c | Both buttons independently on or off, screen shows the right thing | Per-sensor `displayOn` flag; all four combinations rendered by the same loop | [`main.cpp` `formatRow`](../firmware/src/main.cpp) | T-4c | SW |
| 4d | Sensor not plugged in or not working: display notifies the user of an error | `present` false renders "Sensor n ERROR"; a fault is still flagged as "Sensor n off ERR" while the button is off, so a fault is never hidden by a switched-off sensor | [`main.cpp` `formatRow`](../firmware/src/main.cpp) | T-4d | SW / **ASK** |

> **ASK (4d):** the requirement says the display must notify the user if *any* sensor is faulty,
> but requirement 4 also says a sensor whose button is off should read "Sensor n off". We currently
> show both. Confirm this is what is wanted — see [open questions](05-open-questions.md).

## 5. Features available from the computer

| # | Requirement | How we satisfy it | Where | Verified by | Status |
|---|---|---|---|---|---|
| 5a | Real-time temperature for both sensors, C or F chosen by the user, large font, updated once a second | 1 Hz poll loop locked to the wall-clock second; `clamp(3rem, 11vw, 6rem)` readout; unit toggle persisted in the browser | [`app.js` `renderLive`](../pc-app/static/app.js) | smoke test | DONE |
| 5a.i | Unplugged sensor shows "unplugged sensor" instead of a temperature | Rendered from `present: false` | [`app.js`](../pc-app/static/app.js) | smoke test | DONE |
| 5a.ii | Box switch off shows "no data available" | Rendered from `box_online: false`, declared after 3 s of failed polls | [`poller.py`](../pc-app/app/poller.py) | smoke test | DONE |
| 5b | The computer can virtually press a button; response under 1 second | `POST /api/button/{id}` proxies to the box, which repaints before replying | [`main.py`](../pc-app/app/main.py) | smoke test (measured 16-47 ms) | DONE |
| 5c | Graph of past readings; last 300 s available within 10 s of the software starting | **The box holds the history, not the PC.** A 300-entry ring buffer in firmware is downloaded on connect, so the PC has a full window immediately after launch. | [`main.cpp` `handleHistory`](../firmware/src/main.cpp), [`history.py`](../pc-app/app/history.py) | smoke test | DONE |
| 5c.i | C/F switchable; top of graph always 50 °C (122 °F), bottom always 10 °C (50 °F) | `Y_MIN_C`/`Y_MAX_C` are constants, never autoscaled; axis ticks relabel per unit | [`app.js` `drawChart`](../pc-app/static/app.js) | T-5c.i | DONE |
| 5c.ii | Scrolls horizontally, newest on the right, one new value per second | Series is redrawn each second from a window ending at "now" | [`app.js`](../pc-app/static/app.js) | T-5c.ii | DONE |
| 5c.iii | 300 s total, x axis labelled in seconds ago, 300 → 0 | Gridlines every 60 s, labelled 300…0 | [`app.js` `drawChart`](../pc-app/static/app.js) | T-5c.iii | DONE |
| 5c.iv | Missing data obvious, and clearly different from off-scale data | Two distinct treatments: a gap breaks the trace **and** draws a hatched grey band; an off-scale reading is clamped to the axis **and** marked with a red triangle at the edge | [`app.js` `drawGapBand`](../pc-app/static/app.js) | smoke test + visual | DONE |
| 5c.v | Graph keeps scrolling during a fault and resumes cleanly | History is keyed by absolute second, so an outage occupies its true width and later data lands in the right place | [`history.py`](../pc-app/app/history.py) | smoke test | DONE |

## 6. Recovery

| # | Requirement | How we satisfy it | Where | Verified by | Status |
|---|---|---|---|---|---|
| 6 | Box switched on while the computer is running: graph and live display appear within 10 s | The poller notices the box within one poll and re-downloads the ring buffer immediately | [`poller.py` `_backfill`](../pc-app/app/poller.py) | smoke test (measured 1.2 s) | DONE |

## 7. Alerts

| # | Requirement | How we satisfy it | Where | Verified by | Status |
|---|---|---|---|---|---|
| 7 | Text/email when the temperature goes above a maximum or below a minimum; both messages, both limits and the destination all editable from the computer UI | `AlertEngine` with edge triggering, hysteresis and a cooldown; all six fields edited in the Alerts panel and persisted to `data/alert-settings.json` | [`alerts.py`](../pc-app/app/alerts.py), [`settings_store.py`](../pc-app/app/settings_store.py) | T-7 | SW |

## 8. Range of operation

| # | Requirement | How we satisfy it | Where | Verified by | Status |
|---|---|---|---|---|---|
| 8a | Design range at least −10 to +63 °C (by design, not by test) | DS18B20 is specified −55 to +125 °C, ±0.5 °C over −10 to +85 °C. Firmware stores centi-degrees in `int16_t`, range ±327 °C. The graph clamps at 10/50 °C for display only — the data path is never clamped. | [Design §3](01-system-design.md) | Datasheet argument | SW |
| 8b | Holding a probe warms it in seconds; a soldering iron does so faster | Thermal mass limited to the probe tip; 11-bit resolution (0.125 °C) resolves the change immediately | — | T-8b | TODO |
| 8c | Room temperature reads 22 ±4 °C | DS18B20 factory calibration, no user calibration needed. Probes must be clear of the board — resting them beside the ESP32 adds ~4 °C of self-heating | — | T-8c | **DONE** 21.7–22.2 °C |
| 8d | Ice-water mixture reads 0 ±2 °C | Sealed stainless probe, fully immersible. Needs a crushed-ice slurry, not cubes in water — cubes read 2–5 °C and fail a good sensor | — | T-8d | **DONE** +0.6 / −0.5 °C |

---

## Summary

| Status | Count |
|---|---|
| DONE (verified end to end) | 14 |
| SW (software done, awaiting hardware) | 10 |
| TODO (mechanical / bench measurement) | 5 |

The software risk is retired and both temperature-accuracy requirements are measured and
passing. **The remaining risk is entirely mechanical, and it is the part with
the longest lead time** — enclosure, connectors, probe strain relief and the drop test. Order those
parts first; see [the schedule](04-team-and-schedule.md).
