# ECE:4880 Lab 1 — Networked Two-Sensor Thermometer

Capstone Senior Design, Fall 2026 · University of Iowa
Instructors: Prof. Najeeb Najeeb, Prof. Fatima Toor · TA: Joel Dillman

A two-probe digital thermometer with a standalone battery-powered display unit
("the third box") and a networked PC interface with live charting and
temperature-threshold alerts.

---

## System at a glance

```
   ┌──────────────┐  1-Wire   ┌─────────────────────┐   WiFi    ┌──────────────┐
   │ DS18B20 #1   ├──────────►│                     │  (HTTP)   │  PC / laptop │
   │ 1 m probe    │           │   THIRD BOX         │◄─────────►│  FastAPI +   │
   └──────────────┘           │   ESP32             │           │  browser UI  │
                              │   OLED display      │           └──────┬───────┘
   ┌──────────────┐  1-Wire   │   2 buttons         │                  │ SMTP
   │ DS18B20 #2   ├──────────►│   power switch      │                  ▼
   │ 1 m probe    │           │   battery           │           ┌──────────────┐
   └──────────────┘           │   300 s ring buffer │           │ Phone: email │
                              └─────────────────────┘           │ / SMS alert  │
                                                                └──────────────┘
```

| Assembly | Requirement | Lives in |
|---|---|---|
| Third box firmware | 1c, 2, 3, 4, 5b | [`firmware/`](firmware/) |
| PC application | 1a, 5, 6, 7 | [`pc-app/`](pc-app/) |
| Probes + enclosure | 1b, 2, 8 | [`docs/02-bill-of-materials.md`](docs/02-bill-of-materials.md) |
| Alerts to phone | 1d, 7 | [`pc-app/app/alerts.py`](pc-app/app/alerts.py) |

## Start here

1. **[`docs/00-requirements-traceability.md`](docs/00-requirements-traceability.md)** — every numbered
   requirement from the lab handout, mapped to the design element that satisfies it and the test
   that proves it. This is the master checklist. Keep it current; it drives the grade.
2. **[`docs/01-system-design.md`](docs/01-system-design.md)** — architecture, pinout, protocol, timing budgets.
3. **[`docs/04-team-and-schedule.md`](docs/04-team-and-schedule.md)** — who owns what, and the week-by-week plan.
4. **[`SETUP.md`](SETUP.md)** — get your machine building and running in ~20 minutes.

## Quick start (after SETUP.md)

Run the PC app against the simulator — no hardware needed, works for all three of us in parallel:

```bash
cd pc-app && python tools/fake_box.py
```

```bash
cd pc-app && uvicorn app.main:app --reload --port 8000
```

Then open <http://localhost:8000>.

Build and flash the third box:

```bash
cd firmware && pio run --target upload && pio device monitor
```

## Repository layout

```
firmware/        ESP32 firmware (PlatformIO, Arduino framework, C++)
  src/main.cpp     sensor sampling, display, buttons, ring buffer, HTTP API
  include/         config.h (pins, tunables), secrets.h (gitignored)
pc-app/          PC-side application (Python 3.11, FastAPI)
  app/             poller, alert engine, REST API
  static/          browser UI: large readout, chart recorder, settings
  tools/fake_box.py  hardware simulator for parallel development
docs/            requirements traceability, design, BOM, test plan, schedule
  decisions/       architecture decision records (ADRs)
```

## Rules of the road

- **Never commit secrets.** `firmware/include/secrets.h` and `pc-app/.env` are gitignored.
  Copy the `.example` versions and fill in your own WiFi and email credentials locally.
- **Branch per feature**, PR into `main`, one teammate reviews. No direct pushes to `main`.
- **Update the traceability matrix in the same PR** that implements or tests a requirement.
