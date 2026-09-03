# Breadboard Wiring

The week-2 bench prototype. Everything the firmware expects, on a breadboard, powered from USB.

Build it in **five stages** and verify each one before starting the next. It is far quicker than
wiring the whole thing and then trying to work out which of five subsystems is broken.

> This breadboard is temporary. Requirement 2a is a drop test, and a breadboard will not survive
> one — the final build is soldered perfboard or a PCB. See [the BOM](02-bill-of-materials.md).

---

## Before you start

**All logic runs at 3.3 V.** The ESP32 GPIO pins are 3.3 V and are **not** 5 V tolerant. The
DS18B20s are powered from the **3V3** pin, never from VIN or 5V. Getting this wrong can damage the
ESP32, and it is the single most common way this board gets killed.

The LCD is the exception: our module runs its controller and its backlight from 5 V, because a
5 V HD44780 cannot reach usable contrast on a 3.3 V supply. Only its six signal lines are 3.3 V,
and pin 5 `RW` tied to ground is what stops it driving anything back. See
[the contrast section](#contrast-the-lcd-itself-also-needs-5-v).

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
| **LCD** `VDD` | **5 V** | not the 3V3 rail — see the contrast section |
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
| 2 | `VDD` | **5 V** — not the 3V3 rail, see the contrast section |
| 3 | `V0` | pot **wiper** — see "Finding the wiper" below; pot ends to 5 V and ground |
| 4 | `RS` | `GPIO 23` |
| 5 | `RW` | blue rail (write-only; must be grounded) |
| 6 | `E` | `GPIO 22` |
| 11-14 | `D4 D5 D6 D7` | `GPIO 21`, `17`, `16`, `15` |
| 15 | `A` | 220 ohm to **5 V** -- not the 3V3 rail, see below |
| 16 | `K` | blue rail |

Pins 7-10 stay unconnected -- that is what makes it 4-bit mode.

**Why these six GPIO and not tidier ones.** A DevKit PCB is wider than the span of its own pin
rows, so once it is pushed into a single breadboard the body covers every hole except one column
and only **one of its two headers can be reached at all**. These six are the pins left free on the
same header as the sensors, buttons, 3V3 and GND. The tidy-looking choice (13, 14, 25, 26, 27, 33)
is on the far header and makes the prototype physically impossible to wire on one board.

`VIN` is on that unreachable header too, so the 5 V the LCD needs -- for both its controller and
its backlight -- has to come from somewhere else for now; see the two sections below. Getting both headers back needs a second
breadboard butted against the first with the module straddling the join, or female-to-male jumpers
with the module sitting beside the board. Worth solving before the final build.

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

### The pot is not optional at 5 V

An earlier version of this guide suggested tying `V0` straight to ground to save fitting the pot.
That worked only while `VDD` was 3.3 V. With `VDD` at 5 V, grounding `V0` asks for maximum
contrast and the screen fills with solid blocks instead of text. The useful setting is a few
tenths of a volt above ground, which is exactly the fine adjustment a pot exists to provide.

### A blue LCD needs 5 V for its backlight

Ours is the blue module, and that is not just a colour choice. Blue LCD1602s are negative-mode
STN -- white characters on a blue field -- which is **transmissive**: the characters are lit from
behind and the display is unreadable with the backlight off. The yellow-green modules are the
opposite, reflective, and perfectly readable unlit. So on a blue module the backlight is not
cosmetic, and requirement 4b depends on it.

A blue LED has a forward voltage of about 3.2 V. On a 3.3 V rail that leaves ~0.1 V across the
series resistor, so no resistor value produces useful current. **The backlight has to run from 5 V.**

The backlight is electrically independent of the HD44780 -- just an LED across pins 15 and 16,
sharing only ground:

| LCD pin | To |
|---|---|
| 15 `A` | 220 ohm to **5 V** |
| 16 `K` | blue rail (ground, shared with the ESP32) |

(5 - 3.2) / 220 is about 8 mA, a normal backlight current.

The controller needs 5 V as well, for a different reason -- see the contrast section below.

Sources of 5 V, given that `VIN` is on the unreachable header: the kit Uno powered from its own USB
(run its `5V` to a spare row and **tie its `GND` to our negative rail** so the boards share a
reference), a breadboard power module such as an MB102, or -- properly -- a second breadboard or
female-to-male jumpers so `VIN` becomes reachable.

### Contrast: the LCD itself also needs 5 V

Contrast on an HD44780 is set by the difference `VDD - V0`, and a 5 V module wants roughly 4.2 to
4.7 V of it. Run `VDD` at 3.3 V and the most you can produce is 3.3 V even with `V0` pulled all the
way to ground -- so the screen stays uniformly blank at **every** pot setting. That is not a wiring
fault and no amount of adjusting fixes it.

So the module runs from 5 V: pin 2 `VDD`, the backlight, and the pot high end. Only the six signal
lines stay at 3.3 V, driven by the ESP32.

**Why this is safe, and what makes it safe.** Pin 5 `RW` is hardwired to ground, so the HD44780 is
permanently in write mode and never drives its data pins -- `D4`-`D7`, `RS` and `E` are all inputs,
always. Nothing can push 5 V back into a 3.3 V GPIO. Grounding `RW` is therefore not housekeeping,
it is the interlock that makes a 5 V display safe to drive from 3.3 V logic. If `RW` were ever
allowed to float high, the display would drive 5 V straight into the ESP32.

The remaining wrinkle is the other direction: at `VDD` = 5 V the HD44780 wants a logic high of
0.7 x 5 = 3.5 V, and the ESP32 delivers 3.3 V. That is marginally out of spec and works on the
large majority of modules. If yours proves flaky, the fix is a level shifter on the six signal
lines, not lowering `VDD`.

**The I2C backpack variant is the opposite case.** There the backpack pulls SDA and SCL up to its
own supply, so powering *it* at 5 V would put 5 V on two ESP32 pins with nothing to stop it. A
backpack must either run at 3.3 V or go through a bidirectional level shifter.

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
python -m platformio run -d firmware --target upload
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
