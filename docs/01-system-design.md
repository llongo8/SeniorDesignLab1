# System Design

## 1. Architecture

```
   DS18B20 #1 ──1-Wire(GPIO4)──┐
                               │   ┌──────────────────────────────┐
   DS18B20 #2 ──1-Wire(GPIO5)──┼──►│  ESP32-WROOM-32              │
                               │   │                              │
   Button 1 ────────(GPIO18)───┤   │  1 Hz sampler (non-blocking) │
   Button 2 ────────(GPIO19)───┤   │  300-entry ring buffer       │
                               │   │  SSD1306 renderer            │
   OLED ──────I2C(GPIO21/22)───┘   │  HTTP JSON server :80        │
                                   └──────────────┬───────────────┘
   Battery ──[SPST panel switch]──► 5 V boost ────┘        │ WiFi
                                                           │
                                   ┌───────────────────────▼──────┐
                                   │  PC: FastAPI on :8000        │
                                   │  1 Hz poller, 300 s history  │
                                   │  alert engine (SMTP)         │
                                   └───────────┬──────────────────┘
                                    browser UI │        │ SMTP
                                               ▼        ▼
                                        chart recorder  phone
```

Three processes, one protocol. The box owns *measurement and its own recent past*. The PC owns
*presentation, thresholds and notification*. Nothing is duplicated between them.

## 2. Why the box holds the history

This is the single most important design decision in the project, and it comes straight out of
requirement 5c:

> The graph of the past 300 seconds of data should be available within 10 seconds of starting the
> software on the computer.

The PC software has just started. It cannot possibly have recorded the last 300 seconds. Therefore
the history has to already exist somewhere else, and the only other thing in the system is the box.
So the firmware keeps a 300-entry ring buffer per sensor and serves it at `GET /api/history`; the
PC downloads it the moment it connects, and again whenever the box reappears after being off
(requirement 6).

Cost: 300 samples × 2 sensors × 2 bytes = **1200 bytes**, against 320 kB of ESP32 RAM.

Samples are stored as `int16_t` centi-degrees. `INT16_MIN` is the "no reading" sentinel, which is
outside any physically meaningful value, so missing data can never be confused with real data.

## 3. Temperature range and resolution

| Property | Value | Source |
|---|---|---|
| Sensor range | −55 to +125 °C | DS18B20 datasheet |
| Sensor accuracy | ±0.5 °C over −10 to +85 °C | DS18B20 datasheet |
| Required design range | −10 to +63 °C | Requirement 8a |
| Configured resolution | 11 bit = 0.125 °C, 375 ms conversion | [`config.h`](../firmware/include/config.h) |
| Wire format | `int16_t` centi-degrees, ±327.67 °C | [`main.cpp`](../firmware/src/main.cpp) |

The required range sits comfortably inside the part's specified accuracy band, so **no calibration
step is needed** to meet requirements 8c and 8d. That is worth stating explicitly in the report:
choosing a digital sensor with factory calibration is what removes a whole task from the project.

The 10–50 °C graph limits of requirement 5c.i apply to **display only**. Values outside that band
are transported and stored at full precision and are drawn clamped to the axis with an off-scale
marker — never discarded.

## 4. Timing budgets

| Requirement | Budget | Design | Measured |
|---|---|---|---|
| 4a display responds to a button | 20 ms | 800 kHz I2C, full frame ≈ 11.5 ms; buttons polled twice per loop iteration | `GET /api/info` → `max_button_latency_us` |
| 5a live readout updates | 1 s | Poll loop locked to the wall-clock second | 1.00 s |
| 5b virtual button responds | 1 s | One HTTP round trip on the LAN | 16–47 ms |
| 5c first graph after PC start | 10 s | Ring buffer downloaded on the first poll | ~1 s |
| 6 recovery after box switched on | 10 s | Reconnect detected within one poll, then backfill | 1.2 s |

### The 20 ms trap

An SSD1306 frame is 1024 bytes. Over I2C each byte costs about 9 bit-times:

```
400 kHz → 1024 × 9 / 400 000 = 23.0 ms   ← exceeds the 20 ms budget on its own
800 kHz → 1024 × 9 / 800 000 = 11.5 ms   ← what we run
```

Running the default 400 kHz would have failed requirement 4a with no other mistake anywhere in the
system. Two further precautions:

- The sensor conversion never blocks. `setWaitForConversion(false)` means the 375 ms conversion
  overlaps normal loop execution instead of stalling it.
- `pollButtons()` runs both before and after the 1-Wire scratchpad read, because that read
  bit-bangs for several milliseconds and a press landing inside it must not wait for the next
  iteration.

### The wall-clock lock

The PC history is keyed by whole seconds. A poll loop that simply sleeps "one second minus the work
time" drifts, and the moment two samples land in the same integer second, the next second gets
none — the graph then shows a gap in data that was collected perfectly. The loop therefore sleeps
to `floor(now) + 1 + 0.1 s`, which absorbs ±100 ms of jitter without ever changing which second a
sample belongs to. This is covered by a regression test in `smoke_test.py`.

## 5. Power

The switch of requirement 3 is a **hard mechanical break in the battery line**, not a firmware mode.
With the switch off the box is unpowered, so it cannot display anything and cannot serve data —
which is exactly what requirement 3 demands, achieved with a component rather than with code that
could have a bug in it.

Our switch is a 3-terminal **SPDT**. We use the common terminal and one throw, leaving the other
throw unconnected, which makes it behave as a plain on/off switch. The spare throw is deliberately
left idle: there is nothing useful for it to do, because when the switch is off the entire box is
dead and no circuit inside it can be signalled. See
[the wiring note](02-bill-of-materials.md#using-a-3-terminal-spdt-switch).

Rough budget for an ESP32 with WiFi modem sleep enabled:

| State | Current |
|---|---|
| Active, WiFi associated, modem sleep on | ~80–120 mA average |
| OLED at typical duty | ~10–20 mA |
| Budget | ~150 mA average |

A single protected 18650 (3000 mAh) through a 5 V boost gives roughly **12–15 hours**, which is far
more than any demo needs. `WiFi.setSleep(true)` roughly halves the radio current at the cost of up
to one beacon interval (~100 ms) of latency — irrelevant against the 1 s budget of requirement 5b.

## 6. Mechanical

Requirements 2a–2c are graded on a drop test, so they are design constraints, not afterthoughts:

- **Enclosure**: ABS project box with an internal boss or standoffs. The PCB and the battery are
  both *fastened*, not resting. A loose 18650 inside a dropped box is a hammer.
- **Connectors**: GX12-3 panel connectors, nut-secured through the wall. Three conductors carry
  exactly what a DS18B20 needs — 3V3, DATA, GND. They are threaded, keyed and meant for repeated
  use by a casual user (requirement 2b), and they pull free rather than transmitting shock into the
  PCB (requirement 2c).
- **Strain relief** at both ends of every probe cable: at the connector shell and where the lead
  meets the probe body.
- **Orientation independence** (requirement 2a): nothing may depend on gravity. No unsecured cells,
  no press-fit modules, no breadboard anywhere in the final build.

## 7. Protocol

The box serves JSON over HTTP on port 80. Polling, not websockets: every timing requirement is
generous, and a request/response loop is far easier to reason about, to test against the simulator,
and to debug from a browser on demo day.

### `GET /api/state`

```json
{
  "fw": "0.1.0",
  "uptime_ms": 123456,
  "sensors": [
    {"id": 1, "present": true,  "display_on": true,  "temp_c": 22.5},
    {"id": 2, "present": false, "display_on": false, "temp_c": null}
  ]
}
```

### `GET /api/history`

```json
{
  "period_ms": 1000,
  "len": 300,
  "sensors": [
    {"id": 1, "samples_c100": [2250, 2251, null, 2249, "..."]}
  ]
}
```

Oldest sample first, centi-degrees, `null` for a second with no reading.

### `POST /api/button?sensor=1&state=toggle`

`state` is `on`, `off` or `toggle`. The display is repainted before the reply is sent, so the round
trip is the only latency. Returns `{"id": 1, "display_on": true}`.

### `GET /api/info`

Diagnostics, including the **measured** worst-case render and button latencies since boot. Quote
these in the report rather than the calculated figures.

## 8. Network

The box joins a WiFi network as a station and prints its IP on the OLED and the serial port at
boot. The PC finds it by IP, set in `pc-app/.env`.

**Use a phone hotspot or a personal travel router, not campus WiFi.** eduroam is WPA2-Enterprise,
which needs a different and much fussier connection routine, and client isolation on many campus
networks blocks the PC from reaching the box at all. A network you control is also the right choice
for a demo you cannot afford to have fail.

mDNS (`thermobox.local`) is registered as a convenience but is not depended on: Windows only
resolves it with Bonjour installed.
