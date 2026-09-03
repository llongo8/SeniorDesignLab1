# Team, Roles and Schedule

> **Dates are provisional.** The Lab 01 slides give "Sunday, September 23", but September 23 2026
> is a Wednesday, so that deck looks recycled from an earlier year. Confirm the real dates at the
> first TA contact — this is [Q1 in the open questions](05-open-questions.md) — and correct this
> file. The plan below assumes checkoff in the week of **Sept 14–20** and submission by the end of
> the week of **Sept 21–27**.

## Team

| Name | Role | Owns |
|---|---|---|
| Lucas Longo | | |
| | | |
| | | |

Fill this in at the first meeting. The handout grades "roles and responsibilities are clearly
understood" and "team members are accountable", so write it down rather than assuming it.

### Suggested split

The work divides into three genuinely parallel tracks, which is convenient with three people.
Rotate the reviewer so everyone sees all of it.

- **Firmware** — sensors, display, buttons, ring buffer, HTTP API. Owns `firmware/`.
- **PC application** — poller, chart, alerting, UI. Owns `pc-app/`. Can work entirely against
  `tools/fake_box.py` with no hardware.
- **Mechanical and integration** — enclosure, connectors, probe assembly, power, drop testing.
  Owns the BOM and the physical build. **This track has the longest lead time and is the one that
  sinks projects**, because it cannot be compressed at the end: glue cures, parts ship, and a
  failed drop test needs a rebuild.

Documentation is not a fourth track. Everyone writes the parts they own, in the same PR as the work.

## Schedule

| Week | Dates | Milestone | Firmware | PC app | Mechanical |
|---|---|---|---|---|---|
| 1 | Aug 27 – Aug 30 | **Repo and toolchain live.** Everyone can build and run. | Flash the ESP32, confirm boot, blink | Run the app against the simulator | **Order parts today** — probes, connectors, enclosure, cell |
| 2 | Aug 31 – Sep 6 | **Breadboard prototype reads temperature.** | Both DS18B20s reading; LCD showing values; buttons toggling | Point the app at the real box; end-to-end 1 Hz data | Mock up the panel layout; confirm the box fits everything |
| 3 | Sep 7 – Sep 13 | **TA progress update.** Bring the open-questions list. | Ring buffer + `/api/history`; hot-plug recovery | Chart, C/F, virtual buttons all verified on hardware | Drill and mount the panel; connectors terminated |
| 4 | Sep 14 – Sep 20 | **Lab checkoff.** Full manual test pass. | Timing measurements captured from `/api/info` | Alerts delivering to a real phone | Final assembly, soldered, fastened; **drop test** |
| 5 | Sep 21 – Sep 27 | **Report and submission.** | Freeze; fix only what checkoff found | Freeze | Photographs for the report |

### Do these first, this week

1. **Order the long-lead parts.** Probes, GX12 connectors and the enclosure. Everything else can be
   worked around; these cannot. If they arrive in week 4 the project fails on requirements 2a–2c
   regardless of how good the software is.
2. **Confirm the dates** with the TA (Q1).
3. **Get all three machines building.** See [SETUP.md](../SETUP.md).
4. **Book a standing meeting time.** The handout is blunt that these labs cannot be completed at
   the last minute.

## How we work

- **Branch per feature**, pull request into `main`, one teammate reviews before merge. Nobody
  pushes to `main` directly.
- **Update [the traceability matrix](00-requirements-traceability.md) in the same PR** as the work
  it describes. Not at the end.
- **Run the smoke test before pushing.** It is fast and it catches the error paths nobody checks by
  hand.
- **Never commit secrets.** `firmware/include/secrets.h` and `pc-app/.env` are gitignored; commit
  the `.example` files instead.
- **Record measurements, not impressions.** "22.3 °C against a lab thermometer reading 22.0" is
  evidence. "Reads about right" is not.

## Rapid prototyping

The handout asks specifically for rapid prototyping: get something working end to end early, then
add features and rework until it meets every requirement. Resist the urge to perfect the firmware
before the box exists. A prototype that reads one sensor onto a breadboarded LCD in week 2 is
worth more than a beautiful architecture in week 4.
