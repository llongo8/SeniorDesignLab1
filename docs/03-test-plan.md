# Test Plan

Test IDs are referenced from the [traceability matrix](00-requirements-traceability.md). Record
the date, who ran it, and the actual measured value — not just a tick. A measured number in the
report is worth far more than an assertion that something worked.

## Automated

Run before every push. Three terminals:

```bash
cd pc-app
python tools/fake_box.py
```

```bash
cd pc-app
uvicorn app.main:app --port 8000
```

```bash
cd pc-app
python tools/smoke_test.py
```

The smoke test drives the simulator fault-injection endpoints and covers requirements 5a.i, 5a.ii,
5b, 5c, 5c.iv and 6 — including a regression check that continuous operation never manufactures
phantom gaps in the graph. Current status: **18 passed, 0 failed**.

## Manual — electrical and firmware

| ID | Requirement | Procedure | Pass criterion | Result |
|---|---|---|---|---|
| T-3 | 3 | Switch the box off. Observe the display and the PC UI. | Display dark. PC shows "no data available" within 10 s. | |
| T-3b | 3 | Check the switch sense: lever **up** should be on. | Up = powered, down = dark. A backwards switch is an avoidable mark to lose. | |
| T-4a | 4a | Press each button ~20 times with the serial monitor open. The firmware prints a `[perf]` line whenever the worst case grows. Cross-check against `max_button_latency_us` at `GET /api/info` once WiFi is up. For an independent check, scope the button pin against the LCD `E` line (GPIO 22). | **< 20 ms**, worst of 20 presses. | **7.3 ms** (bench, 2026-08-27) |
| T-4b | 4b | View the display under normal room lighting from 1 m, at eye level and at 45°. | All digits legible. | |
| T-4c | 4c | Exercise all four button combinations: off/off, on/off, off/on, on/on. | Correct value or "Sensor n off" in every case. | |
| T-4d | 4d | With a button on, unplug that probe. Repeat with the button off. | Error is shown in both cases. | |
| T-2d | 2d | Unplug a probe for 30 s, plug it back in. Touch nothing else. | Reading returns within ~4 s with no reset, no button press, no reconnection. | |
| T-8b | 8b | Hold the probe tip in a closed hand. Then bring a hot soldering iron close to it. | Rises within a few seconds; faster with the iron. | |
| T-8c | 8c | Leave both probes in still air **away from the ESP32** for 5 minutes — a board running WiFi is a small heater. Compare against a lab thermometer. | **22 ±4 °C** (18–26 °C). | Bench 2026-08-27: **26.7 °C, marginally over.** See T-8d and Q10. |
| T-8e | 8c | Bundle both probe tips together in still air for 5 minutes. | The two agree within ~1 °C. A larger gap means at least one part is outside its ±0.5 °C spec. | |
| T-8d | 8d | Stirred ice-and-water mixture, probe fully immersed, 2 minutes to settle. | **0 ±2 °C**. Record both probes. | Attempt 1, 2026-08-27: **2.2 °C and 3.8 °C** — both high, spread 1.6 °C. Bath was ice cubes plus added water, not a crushed-ice slurry, which typically sits 2–5 °C. Retest before drawing any conclusion about the parts. |
| T-8a | 8a | Design argument only — the handout says this need not be tested. | Datasheet range cited in the report. | |

> **T-8d technique matters, and it already cost us one run.** An ice bath only sits at 0 °C
> if it is a *stirred slurry of crushed ice and water* — mostly ice, with just enough water
> to fill the voids. It is the ice surface area in contact with the water that pins the
> mixture to 0 °C. A cup of water with cubes floating in it is not an ice bath and will
> read 2–5 °C, which is precisely what attempt 1 measured. Let it equilibrate, keep stirring, and immerse the probe
> tip well below the surface without touching the container wall. Getting this wrong is the usual
> reason a perfectly good thermometer appears to read 2 °C high.

## Manual — mechanical

Do these **last**, and do them deliberately. They can break the prototype.

| ID | Requirement | Procedure | Pass criterion | Result |
|---|---|---|---|---|
| T-2a-1 | 2a | Drop the closed box from workbench height (~1 m) onto the lab floor. | Powers up and operates normally afterwards. | |
| T-2a-2 | 2a | Operate the box upside down and on each side. | Full function in every orientation. | |
| T-2b | 2b | Have someone **outside the team** connect and disconnect both probes. | They manage it without instruction or tools. | |
| T-2c | 2c | Repeat the drop with both probes connected. | No cable, connector or solder joint breaks. Probes coming unplugged is acceptable. | |
| T-1b | 1b | Measure each probe cable. | **1.0 ±0.1 m**. | |

Record for each drop: the height, the surface, the orientation, and what if anything changed. Take
a photograph before and after — a photograph of a box that survived a drop is good evidence.

## Manual — computer and alerts

| ID | Requirement | Procedure | Pass criterion | Result |
|---|---|---|---|---|
| T-5a | 5a | Watch the live readout for 60 s. | Updates once a second, large font, both sensors. | |
| T-5c.i | 5c.i | Toggle C/F. Warm a probe past 50 °C. | Axis stays pinned at 10–50 °C / 50–122 °F. Off-scale marker appears; the axis never rescales. | |
| T-5c.ii | 5c.ii | Watch the graph for 60 s. | New data enters on the right, scrolls left, one point per second. | |
| T-5c.iii | 5c.iii | Read the x axis. | Labelled in seconds ago, 300 → 0. | |
| T-5c.iv | 5c.iv | Unplug a probe for 20 s, then take a probe outside the 10–50 °C band. | The gap and the off-scale region are obviously different from each other. | **PASS** 2026-08-27: ice bath drove both traces below the 10 °C floor — clamped at the axis with red off-scale markers — while reflashing left hatched no-data bands. Both visible on one screen; screenshot kept for the report. |
| T-6 | 6 | With the PC app running, switch the box off, wait 30 s, switch it on. Time it. | Live display and 300 s of graph return **within 10 s**. | |
| T-7-1 | 7 | Set the max below room temperature. Wait. | Text/email arrives at the configured phone. | |
| T-7-2 | 7 | Set the min above room temperature. Wait. | The low-temperature message arrives. | |
| T-7-3 | 7 | Change both messages, both limits and the destination in the UI. Trigger again. | The new text arrives at the new destination. | |
| T-7-4 | 7 | Leave a sensor out of range for 10 minutes. | Alerts are rate-limited by the cooldown, not sent every second. | |

## Checkoff dry run

Run the entire manual list start to finish, in order, in the lab, at least **two days before**
checkoff week. Not the night before. Anything that fails needs time to fix, and the parts that fail
are usually the mechanical ones, which need glue, solder or a reprint.
