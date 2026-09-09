# Tidy Breadboard Layout

The organised version of the prototype: MB102 module on a 9 V battery, panel switch in the battery
line, everything on one 830-point board. Build from [the staged guide](06-breadboard-wiring.md)
first if nothing is wired yet — this is about *placement*, not about bringing subsystems up.

Board convention used throughout: columns **a b c d e** | channel | **f g h i j**, a `+` and `−`
rail down each outside edge, rows numbered **1 at the top to 65 at the bottom**. A hole is written
column-then-row, so `a18` is column a, row 18.

---

## 1. Two supply rails, and which is which

| Rail | Voltage | Source | Feeds |
|---|---|---|---|
| **LEFT `+`** | 5 V | MB102, left jumper on **5 V** | LCD `VDD`, LCD backlight, contrast pot high end |
| **LEFT `−`** | ground | MB102 | everything |
| **RIGHT `+`** | 3.3 V | **ESP32 `3V3` pin**, not the module | both probes, both 4.7 kΩ pull-ups |
| **RIGHT `−`** | ground | MB102 (both `−` rails are common through the module) | everything |

> **Set the MB102's RIGHT jumper to OFF.** The right `+` rail is driven by the ESP32's own regulator.
> If the module also drives it, two regulators fight over a rail neither controls. The left jumper
> goes to 5 V. Meter both rails before connecting anything — the jumpers do not always ship where
> you expect.

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

row 35/37 contrast pot    (paired legs one side, lone leg the other)

row 40-55 LCD             (see the note below - wires, not plugged in)

row 60-65 MB102 module    (clips onto the rails, spans the board)

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
| 2 | switch **common** | MB102 barrel plug **centre** | battery feeds a throw, load off the common |
| 3 | 9 V battery **−** (black) | MB102 barrel plug **sleeve** | |
| 4 | MB102 USB-A output | ESP32 USB port, via a spare cable | **powers the ESP32** — see §5 |
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

### Contrast pot — rows 35–37

| # | From | To |
|---|---|---|
| 21 | paired leg `f35` | `g35` → LEFT `+` rail (5 V) |
| 22 | **lone leg (wiper)** `j36` | `i36` → LCD `V0` |
| 23 | paired leg `f37` | `g37` → LEFT `−` rail |

Three legs, three different rows, three separate nodes. If the paired legs land in the same row you
have shorted the track and the pot does nothing.

### LCD — 16 pins

| LCD pin | Label | To |
|---|---|---|
| 1 | `VSS` | LEFT `−` rail |
| 2 | `VDD` | LEFT `+` rail (5 V) |
| 3 | `V0` | pot wiper (`i36`) |
| 4 | `RS` | `a`(D23 row) |
| 5 | `RW` | LEFT `−` rail — **mandatory** |
| 6 | `E` | `a`(D22 row) |
| 7–10 | `D0`–`D3` | nothing (4-bit mode) |
| 11 | `D4` | `a`(D21 row) |
| 12 | `D5` | `a`(TX2 / D17 row) |
| 13 | `D6` | `a`(RX2 / D16 row) |
| 14 | `D7` | `a`(D15 row) |
| 15 | `A` | 220 Ω → LEFT `+` rail (5 V) |
| 16 | `K` | LEFT `−` rail |

> **Do not plug the LCD into the breadboard.** Its body is about 36 mm deep, wider than the board's
> whole terminal area, so plugging it in buries every hole in those rows underneath it. Connect it
> with female-to-male jumpers and let it sit beside the board. That is also how it will be in the
> finished box, where it is panel-mounted and wired — so doing it now means the wiring does not
> change when the enclosure arrives.

## 4. Verify before applying power

1. **Meter the rails with the battery connected and the switch on**, before any component is in.
   Left `+` to left `−` should read 5 V. Right `+` should read nothing yet — it only comes alive once
   the ESP32 is powered and its `3V3` pin is jumpered across.
2. **Meter the switch**: on in one position, open in the other, and confirm the lever direction you
   want to mean "on".
3. **Check the MB102 right jumper is OFF** so it is not driving the 3.3 V rail.
4. Only then plug the probes and LCD in.

## 5. Powering the ESP32 without reaching VIN

The DevKit's `VIN` is on the header the board covers, so it cannot be reached on a single
breadboard. Two ways round it:

**Use the MB102's USB-A output** (most modules have one). A spare USB cable from that socket to the
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
- The LCD is already on wires, so it just moves to the panel cutout.
- The switch is already off-board on wires, so it just moves to the panel.
- The MB102 either mounts inside on standoffs, or is replaced by the 18650 + boost if runtime
  becomes a problem.
