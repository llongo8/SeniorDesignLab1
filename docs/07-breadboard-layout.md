# Tidy Breadboard Layout

The organised version of the prototype: HW-131 supply module on a 9 V battery, panel switch in the battery
line, everything on one 830-point board. Build from [the staged guide](06-breadboard-wiring.md)
first if nothing is wired yet — this is about *placement*, not about bringing subsystems up.

Board convention used throughout: columns **a b c d e** | channel | **f g h i j**, a `+` and `−`
rail down each outside edge, rows numbered **1 at the top to 65 at the bottom**. A hole is written
column-then-row, so `a18` is column a, row 18.

---

## 1. Two supply rails, and which is which

| Rail | Voltage | Source | Feeds |
|---|---|---|---|
| **LEFT `+`** | 5 V | supply module, its jumper on **5 V** | LCD `VDD`, LCD backlight, contrast divider |
| **LEFT `−`** | ground | supply module | everything |
| **RIGHT `+`** | 3.3 V | **ESP32 `3V3` pin**, not the module | both probes, both 4.7 kΩ pull-ups |
| **RIGHT `−`** | ground | supply module (both `−` rails are common through it) | everything |

> **Set the module's jumper for the 3.3 V rail to OFF.** That rail is driven by the ESP32's own
> regulator; if the module drives it too, two regulators fight over a rail neither controls. The
> other jumper goes to 5 V.

Ours is an **HW-131**, the same design as an MB102. Worth knowing about it:

- Two 3-pin jumpers, each labelled `5V / OFF / 3.3`, one per rail pair. **Which jumper feeds which
  rail depends on how the module is seated**, so do not guess — set them differently, meter both
  rails, and note which is which. Thirty seconds, and it removes a whole class of confusion.
- It carries a **USB-A output socket**. A spare cable from there to the ESP32's own USB port is how
  we power the board without needing `VIN`, which is on the header a single breadboard cannot reach.
- It has its **own white power button**, which is not the requirement 3 switch and cannot be panel
  mounted. Leave it on. Remember it exists: "dead board with the battery connected" is usually
  nothing more than this button.
- A green LED lights when the module is powered, which is the quickest check that the battery,
  switch and barrel plug are all doing their job.
- There are extra `3.3V / 5V / GND` header pins in the middle, useful for tapping 5 V without
  going through a rail.

## 2. Where each part sits

```
row  1 ┬───────────────────────────────┐
       │  ESP32 DevKit                 │   pins in column b (left) and j (right)
       │  straddling the channel       │   the body covers c-i, so column a is the
row 15 ┴───────────────────────────────┘   only place to land an ESP32 wire

row 18    sensor 1 data + its 4.7k
row 21    sensor 2 data + its 4.7k

row 25/27 button 1        (straddles the channel)
row 30/32 button 2        (straddles the channel)

row 35    contrast divider (two fixed resistors, no pot)

row 37-52 LCD             (column i, body overhanging the right edge)

row 60-65 supply module   (clips onto the rails, spans the board)

off-board  SPDT switch, wires only, in the battery + line
```

**Leave a clear row between blocks.** It costs nothing on a 65-row board and it makes a misplaced
wire visible instead of hidden.

## 3. Connection table

ESP32 pins are written as **`a` + the row that pin sits in** — read the row off your own board,
since pin order differs between DevKit variants. Everything else is an exact hole.

### Power in

| # | From | To | Note |
|---|---|---|---|
| 1 | 9 V battery **+** (red) | switch **terminal A** | switch is off-board, wires only |
| 2 | switch **common** | module barrel plug **centre** | battery feeds a throw, load off the common |
| 3 | 9 V battery **−** (black) | module barrel plug **sleeve** | |
| 4 | module USB-A output | ESP32 USB port, via a spare cable | **powers the ESP32** — see §5 |
| 5 | ESP32 `GND` | `a`(GND row) → **LEFT −** rail | one ground for the whole board |
| 6 | ESP32 `3V3` | `a`(3V3 row) → **RIGHT +** rail | makes the right rail the 3.3 V rail |

### Sensor 1 — row 18

| # | From | To |
|---|---|---|
| 7 | probe 1 **red** | RIGHT `+` rail (3.3 V) |
| 8 | probe 1 **black** | LEFT `−` rail |
| 9 | probe 1 **yellow** | `a18` |
| 10 | 4.7 kΩ, one leg `b18` | other leg to RIGHT `+` rail |
| 11 | `c18` | `a`(D4 row) |

### Sensor 2 — row 21

| # | From | To |
|---|---|---|
| 12 | probe 2 **red** | RIGHT `+` rail |
| 13 | probe 2 **black** | LEFT `−` rail |
| 14 | probe 2 **yellow** | `a21` |
| 15 | 4.7 kΩ, one leg `b21` | other leg to RIGHT `+` rail |
| 16 | `c21` | `a`(D5 row) |

### Buttons — straddling the channel

Legs land in `e25 e27 f25 f27` and `e30 e32 f30 f32`.

| # | From | To |
|---|---|---|
| 17 | `d25` | `a`(D18 row) |
| 18 | `g25` | LEFT `−` rail |
| 19 | `d30` | `a`(D19 row) |
| 20 | `g30` | LEFT `−` rail |

> One wire each **side of the channel**. Both wires on the same side connects the GPIO straight to
> ground through the switch's internal link — the fault that cost an evening. Serial prints
> `btn HH` when both are correct; an `L` at rest is always a wiring error.

### Contrast — fixed divider, row 35

No pot. Contrast on an HD44780 is `VDD − V0`, and at `VDD` = 5 V the useful `V0` sits only a few
tenths of a volt above ground — a narrow window a pot makes fiddly to hit and easy to knock out of
adjustment. Two fixed resistors put it exactly where it belongs and cannot drift:

| # | From | To | Gives |
|---|---|---|---|
| 21 | **10 kΩ**, one leg `a35` | other leg to LEFT `+` rail (5 V) | |
| 22 | **1 kΩ**, one leg `b35` | other leg to LEFT `−` rail | `V0` = 5 × 1/11 ≈ **0.45 V** |
| 23 | `c35` | LCD `V0` (pin 3) | |

All three share row 35, the divider's midpoint. If the display comes out too dark or too faint,
change only the lower resistor: **1.5 kΩ** raises `V0` to 0.65 V (lighter), **680 Ω** drops it to
0.32 V (darker).

Tying `V0` straight to ground also works on some modules, but at 5 V it asks for maximum contrast
and usually fills the screen with solid blocks. The divider is two parts and no guesswork.

### LCD — 16 pins in column `i`, rows 37–52

Seated in column `i` with the **body overhanging the right edge of the board**. That is what makes
plugging it in workable at all: the module is about 36 mm deep, so if it overhung to the left it
would bury every hole in these rows. Overhanging right, it covers only column `j` and the right
rail across rows 37–52 — neither of which is needed there — and leaves `f`, `g`, `h` clear for
every jumper.

**Check which end is pin 1** on the silkscreen before seating it. This table assumes pin 1 at the
top. If it is at the bottom, flip the table end for end: pin 1 at `i52`, pin 16 at `i37`. Getting it
backwards puts 5 V where ground belongs.

| LCD pin | Label | Hole | Wire from | To |
|---|---|---|---|---|
| 1 | `VSS` | `i37` | `f37` | LEFT `−` rail |
| 2 | `VDD` | `i38` | `f38` | LEFT `+` rail (5 V) |
| 3 | `V0` | `i39` | `f39` | `c35`, the divider midpoint |
| 4 | `RS` | `i40` | `f40` | `a`(D23 row) |
| 5 | `RW` | `i41` | `f41` | LEFT `−` rail — **mandatory** |
| 6 | `E` | `i42` | `f42` | `a`(D22 row) |
| 7–10 | `D0`–`D3` | `i43`–`i46` | — | nothing — this is what makes it 4-bit mode |
| 11 | `D4` | `i47` | `f47` | `a`(D21 row) |
| 12 | `D5` | `i48` | `f48` | `a`(TX2 / D17 row) |
| 13 | `D6` | `i49` | `f49` | `a`(RX2 / D16 row) |
| 14 | `D7` | `i50` | `f50` | `a`(D15 row) |
| 15 | `A` | `i51` | 220 Ω from `h51` to `d51` | `c51` → LEFT `+` rail |
| 16 | `K` | `i52` | `f52` | LEFT `−` rail |

The backlight resistor straddles the centre channel — `h51` to `d51` — because resistor leads reach
across the 0.3 in gap but nowhere near the rail. A jumper covers the rest of the distance.

In the finished box the LCD is panel-mounted on flying leads instead, but the pin-for-pin
connections are identical, so nothing here has to be rethought.

## 4. Verify before applying power

1. **Meter the rails with the battery connected and the switch on**, before any component is in.
   Left `+` to left `−` should read 5 V. Right `+` should read nothing yet — it only comes alive once
   the ESP32 is powered and its `3V3` pin is jumpered across.
2. **Meter the switch**: on in one position, open in the other, and confirm the lever direction you
   want to mean "on".
3. **Check the jumper feeding the 3.3 V rail is OFF** so the module is not driving it against
   the ESP32 regulator. Which jumper that is, you established by metering in step 1.
4. Only then plug the probes and LCD in.

## 5. Powering the ESP32 without reaching VIN

The DevKit's `VIN` is on the header the board covers, so it cannot be reached on a single
breadboard. Two ways round it:

**Use the module's USB-A output**, which ours has. A spare USB cable from that socket to the
ESP32's own USB port powers it at 5 V through the normal path. No `VIN` needed, one breadboard, and
the switch still kills everything because it is upstream of the module.

**Or reach `VIN` directly** with a second breadboard butted against the first so the module straddles
the join, or with female-to-male jumpers onto the far header. Then LEFT `+` (5 V) goes to `VIN`.

Either way: **never power from the laptop USB and the battery at the same time.** Both arrive at the
same regulator input. USB alone for flashing and serial, battery alone for the demo.

## 6. What changes for the soldered build

This layout is deliberately close to the final wiring so the transition is mechanical, not a
redesign:

- Breadboard becomes perfboard; every joint soldered.
- Tactile buttons become panel-mount buttons; same two wires each.
- The probe leads terminate in GX12 panel connectors instead of running to the board directly.
- The LCD moves from the breadboard to flying leads and a panel cutout. Pin for pin the
  connections are identical, so it is a re-termination rather than a redesign.
- The switch is already off-board on wires, so it just moves to the panel.
- The supply module either mounts inside on standoffs, or is replaced by the 18650 + boost if
  runtime becomes a problem.
