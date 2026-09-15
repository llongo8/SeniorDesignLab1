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
| T-4c | 4c | Exercise all four button combinations: off/off, on/off, off/on, on/on. | Correct value or "Sensor n off" in every case. | **PASS** 2026-09-15: all four confirmed on the LCD by eye. The state machine was also driven independently through `POST /api/button` — all four combinations correct. |
| T-4d | 4d | With a button on, unplug that probe. Repeat with the button off. | Error is shown in both cases. | |
| T-2d | 2d | Unplug a probe for 30 s, plug it back in. Touch nothing else. | Reading returns within ~4 s with no reset, no button press, no reconnection. | **PASS** 2026-09-15 on a real probe at the connector — resumed unaided. Simulator run measured recovery at **0.9 s**. |
| T-8b | 8b | Hold the probe tip in a closed hand. Then bring a hot soldering iron close to it. | Rises within a few seconds; faster with the iron. | |
| T-8c | 8c | Leave both probes in still air **away from the ESP32** for 5 minutes — a board running WiFi is a small heater. Compare against a lab thermometer. | **22 ±4 °C** (18–26 °C). | **PASS** 2026-08-27: **21.7–22.2 °C** with the probes in free air. An earlier 26.7 °C reading was taken with the probes lying on the breadboard beside the ESP32 — self-heating, not the room and not the parts. Keep probes clear of the board when measuring. |
| T-8e | 8c | Bundle both probe tips together in still air for 5 minutes. | The two agree within ~1 °C. A larger gap means at least one part is outside its ±0.5 °C spec. | **PASS** 2026-08-27: spread 0.5–1.1 °C across three samples in the ice bath. Two parts at ±0.5 °C may legitimately sit 1.0 °C apart, and a stirred slurry always carries some gradient. Both in spec. |
| T-8d | 8d | Stirred ice-and-water mixture, probe fully immersed, 2 minutes to settle. | **0 ±2 °C**. Record both probes. | **PASS** 2026-08-27, attempt 2 (crushed-ice slurry): **+0.6 °C and −0.5 °C**, inside ±1 °C. Attempt 1 with cubes-plus-water read 2.2/3.8 °C — technique, not the parts. |
| T-8a | 8a | Design argument only — the handout says this need not be tested. | Datasheet range cited in the report. | |

> **T-8d technique matters, and it already cost us one run.** An ice bath only sits at 0 °C
> if it is a *stirred slurry of crushed ice and water* — mostly ice, with just enough water
> to fill the voids. It is the ice surface area in contact with the water that pins the
> mixture to 0 °C. A cup of water with cubes floating in it is not an ice bath and will
> read 2–5 °C, which is precisely what attempt 1 measured. Let it equilibrate, keep stirring, and immerse the probe
> tip well below the surface without touching the container wall. Getting this wrong is the usual
> reason a perfectly good thermometer appears to read 2 °C high.

## RESOLVED — the 85.00 °C readings were a swapped rail wire

**Found 2026-09-14, root cause found and fixed 2026-09-15.**

Sensor 1 returned exactly 85.00 °C for 45 consecutive samples, then recovered unaided. 85.00 °C is
the DS18B20 power-on-reset value of the temperature register, so the part was losing its supply.

It was first attributed to a marginal probe connector, with a flat 9 V battery as a secondary
suspect. **Both were wrong.** The actual cause was a **swapped red and blue rail wire**. That single
error reverse-powered both probes, stopped the ESP32 running on module power, and left the LCD
backlight lit with no text — three symptoms that presented as three separate faults and sent the
diagnosis in three wrong directions at once.

Not seen since the wires were corrected: clean across an 18/18 smoke run and a 5-minute battery run
with both probes reading and zero reboots.

> **Keep this for the report, because it outlived its cause.** A DS18B20 reporting 85.00 °C still
> sets `present = true`, so **requirement 4d does not fire** and the bogus value is rendered as a
> good reading on both the LCD and the PC. That is a real gap in the error detection regardless of
> what pulls the supply down. A firmware guard — treat a sustained exact 85.00 °C as suspect and
> re-read — is worth proposing in the report as future work. It is deliberately not implemented,
> because the hardware fault is fixed and a guard would only have masked it.

### What the episode is worth as evidence

Three symptoms, one wire. Worth writing up as a debugging narrative: the backlight staying lit while
the text vanished is what made it look like a power-supply problem rather than a wiring error, and
the decisive test was polling the box over WiFi with USB unplugged — it answered nothing, which
ruled out a display-contrast explanation in one step.

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
| T-5b | 5b | Press the on-screen button 10 times, alternating sensors. Time each round trip and confirm the box actually toggled. | Under **1 s** per press, state flips every time. | **PASS** 2026-09-14: **10/10** flipped. Worst **487 ms**, median 154 ms, best 100 ms. |
| T-5c | 5c | Kill the PC app, restart it, and time how long until the full 300 s window is populated. | Full history **within 10 s** of the software starting. | **PASS** 2026-09-14: **1.56 s** from process launch to a populated window, **300/300 slots on both sensors**. This is the ring-buffer-in-firmware decision paying off — the PC downloads the box's history rather than accumulating its own. |
| T-5c.i | 5c.i | Toggle C/F. Warm a probe past 50 °C. | Axis stays pinned at 10–50 °C / 50–122 °F. Off-scale marker appears; the axis never rescales. | |
| T-5c.ii | 5c.ii | Watch the graph for 60 s. | New data enters on the right, scrolls left, one point per second. | |
| T-5c.iii | 5c.iii | Read the x axis. | Labelled in seconds ago, 300 → 0. | |
| T-5c.iv | 5c.iv | Unplug a probe for 20 s, then take a probe outside the 10–50 °C band. | The gap and the off-scale region are obviously different from each other. | **PASS** 2026-08-27: ice bath drove both traces below the 10 °C floor — clamped at the axis with red off-scale markers — while reflashing left hatched no-data bands. Both visible on one screen; screenshot kept for the report. |
| T-6 | 6 | With the PC app running, switch the box off, wait 30 s, switch it on. Time it. | Live display and 300 s of graph return **within 10 s**. | **PASS** 2026-09-15: **1.3 s**, history served again immediately. Re-run against the simulator after the firmware changes, so a real power-cycle at checkoff is still worth doing. |
| T-7-0 | 7 | Press "Send a test message" with a destination configured. | An email arrives. | **PASS** 2026-09-03 on both channels. **2026-09-10: email still reliable, the SMS gateway stopped delivering** after roughly two dozen near-identical messages in a few minutes — the app reported every one as sent with no error, so T-Mobile is filtering at `tmomail.net`. Email is our channel; the SMS path has since been removed from the code. |
| T-7-1 | 7 | Set the max below room temperature. Wait. | The email arrives, readable on the phone. | **PASS** 2026-09-14: alert fired **3.1 s** after the limit was lowered, both sensors. |
| T-7-2 | 7 | Set the min above room temperature. Wait. | The low-temperature message arrives. | **PASS** 2026-09-14: fired **3.0 s** after the limit was raised. |
| T-7-3 | 7 | Change both messages, both limits and the destination in the UI. Trigger again. | The new message arrives at the new destination. | **PASS** 2026-09-14 for message text and limits: an edited `message_low` carrying a timestamp was the text delivered, fired in **2.5 s**. **Destination change still to do by hand** — it needs a second mailbox to prove delivery moved. |
| T-7-4 | 7 | Leave a sensor out of range for 10 minutes. | Alerts are rate-limited by the cooldown, not sent every second. | **PASS** 2026-09-14: **0** repeat sends across 60 s held out of range, against ~120 if every poll sent. Note the rate limiting here is *edge triggering* — the sensor never re-entered the zone, so the cooldown was not even the binding constraint. Worth saying that in the report rather than claiming the cooldown did it. |

## Checkoff dry run

Run the entire manual list start to finish, in order, in the lab, at least **two days before**
checkoff week. Not the night before. Anything that fails needs time to fix, and the parts that fail
are usually the mechanical ones, which need glue, solder or a reprint.
