# Breadboard Wiring

The week-2 bench prototype. Everything the firmware expects, on a breadboard, powered from USB.

Build it in **five stages** and verify each one before starting the next. It is far quicker than
wiring the whole thing and then trying to work out which of five subsystems is broken.

> This breadboard is temporary. Requirement 2a is a drop test, and a breadboard will not survive
> one — the final build is soldered perfboard or a PCB. See [the BOM](02-bill-of-materials.md).

---

## Before you start

**Everything runs at 3.3 V.** The ESP32 GPIO pins are 3.3 V and are **not** 5 V tolerant. Both the
DS18B20s and the LCD are powered from the **3V3** pin, never from VIN or 5V. Getting this wrong
can damage the ESP32, and it is the single most common way this board gets killed.

**The DevKit is wide.** It spans the centre channel of the breadboard and typically leaves only one
or two free tie points per pin. Use a full-size (830 point) board, and seat the module so its pins
straddle the channel evenly. If you end up with zero free holes on one side, shift the module one
column across rather than fighting it.

**Set up the power rails first.** Jumper the ESP32 `3V3` pin to the red rail and any `GND` pin to
the blue rail, then take every component's power from the rails rather than from the module. It
keeps the layout readable and means you wire the module once.

---

## Complete connection table

| From | To | Notes |
|---|---|---|
| ESP32 `3V3` | breadboard **red** rail | 3.3 V for everything |
| ESP32 `GND` | breadboard **blue** rail | any GND pin |
| **Sensor 1** red | red rail | VDD |
| **Sensor 1** black (or blue) | blue rail | GND |
| **Sensor 1** yellow (or white) | ESP32 `GPIO 4` | data |
| **4.7 kΩ #1** | `GPIO 4` ←→ red rail | **mandatory pull-up** |
| **Sensor 2** red | red rail | VDD |
| **Sensor 2** black (or blue) | blue rail | GND |
| **Sensor 2** yellow (or white) | ESP32 `GPIO 5` | data |
| **4.7 kΩ #2** | `GPIO 5` ←→ red rail | **mandatory pull-up** |
| **LCD** `VCC` | red rail | 3.3 V — see the contrast note below |
| **LCD** `GND` | blue rail | |
| **LCD** `SDA` | ESP32 `GPIO 21` | backpack variant only |
| **LCD** `SCL` | ESP32 `GPIO 22` | backpack variant only |
| **Button 1** leg A | ESP32 `GPIO 18` | |
| **Button 1** leg B | blue rail | |
| **Button 2** leg A | ESP32 `GPIO 19` | |
| **Button 2** leg B | blue rail | |

That is the whole circuit. Two resistors, and nothing else passive.

**Go by the silkscreen labels, not by position.** Backpacks ship with the pin order `GND VCC SDA
SCL` *and* `VCC GND SCL SDA` depending on the batch. Read the labels on your board every time.

### If your LCD has no backpack

A bare 16-pin module runs in 4-bit parallel mode instead: six GPIO plus a contrast pot. Set
`DISPLAY_TYPE` to `DISPLAY_LCD1602_PARALLEL` in `firmware/include/config.h` and wire:

| LCD pin | Label | To |
|---|---|---|
| 1 | `VSS` | blue rail |
| 2 | `VDD` | red rail |
| 3 | `V0` | pot **wiper** — see "Finding the wiper" below |
| 4 | `RS` | `GPIO 23` |
| 5 | `RW` | blue rail (write-only; must be grounded) |
| 6 | `E` | `GPIO 22` |
| 11-14 | `D4 D5 D6 D7` | `GPIO 21`, `17`, `16`, `15` |
| 15 | `A` | red rail through a 220 ohm |
| 16 | `K` | blue rail |

Pins 7-10 stay unconnected -- that is what makes it 4-bit mode.

**Why these six GPIO and not tidier ones.** A DevKit PCB is wider than the span of its own pin
rows, so once it is pushed into a single breadboard the body covers every hole except one column
and only **one of its two headers can be reached at all**. These six are the pins left free on the
same header as the sensors, buttons, 3V3 and GND. The tidy-looking choice (13, 14, 25, 26, 27, 33)
is on the far header and makes the prototype physically impossible to wire on one board.

`VIN` is on that unreachable header too, which is why the LCD runs from 3V3 here rather than 5 V.
Getting both headers back needs a second breadboard butted against the first with the module
straddling the join, or female-to-male jumpers with the module sitting beside the board. Worth
solving before the final build.

### Finding the wiper

Two footprints are common and they do not agree on which leg is which:

* **Three legs in a line** -- the middle one is the wiper.
* **Two legs on one side, one on the other** (ours) -- the *lone* leg is the wiper, and the two
  sharing a side are the ends of the track.

So do not go by position. Measure across the two legs you believe are the track ends: that reading
is the full value and does **not** change as you turn the screw. Any pair including the wiper does
change. Whichever leg is not part of the fixed pair is the wiper, and it goes to LCD pin 3 (`V0`).

Which end leg goes to the positive rail and which to ground makes no difference beyond reversing
the direction you turn.

### Or skip the pot entirely

At 3.3 V the contrast voltage the LCD wants is already close to ground, so a plain jumper from
`V0` to the negative rail often gives a perfectly readable display. One wire instead of a pot and
three jumpers -- worth trying first. Fit the pot if the characters come out too faint, or if the
screen shows solid blocks.

### Contrast, and why we run the LCD at 3.3 V

HD44780 modules are nominally 5 V parts and the contrast is often weak at 3.3 V -- expect to wind
the pot near one extreme before anything appears. We accept that on purpose. A backpack powered at
5 V pulls SDA and SCL up to 5 V, and **the ESP32 is not 5 V tolerant**, so 5 V costs you the board.

If it is genuinely unreadable at 3.3 V, do not simply move it to 5 V. Either add a bidirectional
level shifter on SDA/SCL, or use the parallel variant above, which is electrically clean at 3.3 V
throughout because nothing pulls the GPIO above the rail.

### Layout sketch

```
         ┌──────── ESP32 DevKit v1 ────────┐
         │  (straddling the centre channel) │
         │                                  │
   3V3 ──┤                                  ├── GND
   GPIO4 ┤ ◄─ sensor 1 data  + 4k7 to 3V3   │
   GPIO5 ┤ ◄─ sensor 2 data  + 4k7 to 3V3   │
  GPIO18 ┤ ◄─ button 1 ─────────────► GND   │
  GPIO19 ┤ ◄─ button 2 ─────────────► GND   │
  GPIO21 ┤ ──► LCD SDA  (backpack variant)   │
  GPIO22 ┤ ──► LCD SCL  (backpack variant)   │
         └──────────────────────────────────┘

   red rail  (3V3) ── sensor 1 VDD, sensor 2 VDD, LCD VCC, both 4k7 resistors
   blue rail (GND) ── sensor 1 GND, sensor 2 GND, LCD GND, both button legs
```

### Why the resistors, and why two

The DS18B20 data line is **open-drain**: the sensor can only pull it low, never drive it high. The
4.7 kΩ to 3V3 is what returns the line high, so without it the bus never reads anything and you get
`-127`. This resistor is not optional and it is the first thing to check when a probe is not found.

We use **two** because each probe has its own bus on its own GPIO — one resistor per bus. That
split is what lets the firmware say *which* probe was unplugged, which requirements 4d and 2d need.

### Why the buttons need no resistors

`pinMode(pin, INPUT_PULLUP)` in the firmware enables the ESP32's internal pull-up, so the pin idles
high and reads LOW when the button shorts it to ground. You have external resistors, but do not add
them here — an external pull-**down** fighting the internal pull-**up** gives a permanently
ambiguous input.

Momentary buttons have four legs, which are really two pairs already joined internally. Straddle
the centre channel with the button so the joined pairs land on opposite sides, then wire one leg
from each side. If the button reads as permanently pressed, you have wired an already-joined pair.

---

## Stage 1 — Power and display

Wire the rails, then the display only. Flash and open the monitor:

```bash
cd firmware && pio run --target upload && pio device monitor
```

**Expect:** the LCD shows `ECE:4880 Lab 1 / Third box boot..`, then the sensor rows. The serial
log prints the firmware banner, `[lcd] backpack found at 0x27`, and `[1wire] sensor 1: absent`
(correct — nothing is wired yet).

If the log says no I2C device at `0x27`, change `LCD_I2C_ADDR` in `firmware/include/config.h` to
`0x3F`, the other common backpack address. If the backpack **is** found but the screen is blank or
shows only faint blocks, that is contrast, not wiring — turn the pot on the backpack.

## Stage 2 — Sensor 1

Add probe 1 and its 4.7 kΩ. Reset the board.

**Expect:** `[1wire] sensor 1: found` and a live temperature once you press button 1 — or
immediately on the PC UI. Hold the probe tip and watch it climb. That is requirement 8b in front of
you.

## Stage 3 — Sensor 2

Add probe 2 and its own 4.7 kΩ. Both rows should now read independently.

**Test hot-plug now** (requirement 2d), while it is easy: pull probe 2's data or power wire out,
wait a few seconds for `SENSOR 2 ERROR`, push it back and confirm it recovers on its own within
about four seconds. No reset, no button press.

## Stage 4 — Buttons

Add both buttons.

**Expect:** each press toggles its row between the temperature and `Sensor n off`, with no
perceptible delay. Check all four combinations — that is requirement 4c.

Then read the measured latency:

```bash
curl http://<box-ip>/api/info
```

`max_button_latency_us` is your evidence for requirement 4a. It must be under 20000. Quote the
measured number in the report, not the calculated one.

## Stage 5 — Battery

Only after stages 1–4 all pass on USB.

| From | To |
|---|---|
| Battery + | switch terminal A (see [the switch note](02-bill-of-materials.md#using-a-3-terminal-spdt-switch)) |
| Switch common | 5 V boost `IN+` |
| Battery − | 5 V boost `IN−` and the blue rail |
| Boost `OUT+` (set to 5.0 V) | ESP32 `VIN` |
| Boost `OUT−` | blue rail |

**Set the boost output to 5.0 V with a meter before connecting it to the ESP32.** These modules
ship at arbitrary voltages and a trimmer that is easy to knock. Feeding 12 V into VIN destroys the
board.

**Do not power from USB and battery at the same time** while testing. Pick one.

---

## Troubleshooting

| Symptom | Cause |
|---|---|
| Temperature reads `-127`, or `sensor n: absent` | Missing or wrong 4.7 kΩ pull-up — check first, every time. Then check the probe is on 3V3 and not 5V, and that data goes to the right GPIO. |
| Both sensors absent | Probes powered from VIN/5V instead of 3V3, or the ground rail is not connected to the ESP32 GND. |
| Serial says no I2C device at `0x27` | Try `0x3F` in `config.h`; or SDA/SCL are swapped; or the pin order is not what you assumed — read the silkscreen. |
| Backpack found, but screen blank or showing faint blocks | Contrast. Turn the pot, several full turns if it is a trimmer. Blocks on the top row alone means the LCD is powered but the firmware has not written to it yet. |
| Display garbled or flickering | The 800 kHz I2C is marginal on long breadboard jumpers. Shorten them. If it persists, drop `I2C_CLOCK_HZ` to `400000` **for bench work only** — that breaks the 20 ms budget of requirement 4a, so it cannot ship. |
| Button reads as always pressed | You wired two legs of the same internally-joined pair. Rotate the button 90°. |
| Board reboots when WiFi connects | Brownout from a current spike. Use a better USB cable, and add a 100–470 µF electrolytic across the 3V3 and GND rails. This is common on breadboards and is not a firmware fault. |
| `Brownout detector was triggered` in the serial log | Same as above. |
| Sensor readings jump around | Long unshielded probe leads picking up noise. Fine on the bench; the final build has short runs to panel connectors. |
