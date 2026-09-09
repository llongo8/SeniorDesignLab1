# Breadboard Build

Follow this top to bottom with the board in front of you. Eight steps, each small enough to check
before moving on. If a check fails, the fault is in the step you just did — you don't have to hunt.

All the reasoning is at the end, in [Why it's built this way](#why-its-built-this-way). Skip it
while you're wiring.

---

## Before you start

**Write down where your ESP32 pins are.** Every board lays them out differently, so read the labels
printed on your module and fill this in. The whole build refers back to it.

| ESP32 pin | Row it's in |
|---|---|
| `3V3` | |
| `GND` | |
| `D4` | |
| `D5` | |
| `D15` | |
| `RX2` (D16) | |
| `TX2` (D17) | |
| `D18` | |
| `D19` | |
| `D21` | |
| `D22` | |
| `D23` | |

**How holes are written.** `a18` means column a, row 18. Columns run `a b c d e` — gap — `f g h i j`
left to right. Rows run 1 at the top to 65 at the bottom.

**Three rails, by name.** Put tape on each and label it. From here on the steps say "5V rail", never
"left rail", so it doesn't matter which physical side each ends up on.

- **5V rail** — one `+` rail, fed by the supply module
- **3V3 rail** — the other `+` rail, fed by the ESP32 itself
- **GND rail** — either `−` rail; both are joined through the module

**What goes where:**

```
rows  1-15   ESP32
rows 18, 21  temperature probes
rows 25-32   buttons
row  35      contrast resistors
rows 37-52   LCD
rows 60-65   supply module
off-board    switch (only its wires touch the board)
```

---

## Step 1 — Power rails

Nothing on the board but the supply module.

1. Clip the module onto the rails at the **bottom** of the board.
2. Plug the 9 V battery into its barrel jack. **Straight in — no switch yet.**
3. Press the module's white button. The green LED comes on.
4. Set the jumpers — see below.

**The module has two jumper headers, one per rail.** They are independent, not alternatives. Each
has three pins, and the jumper block bridges two adjacent pins:

```
[5V]  [middle]  [3.3]
  └──────┘             jumper here  =  5 V out
         └───────┘     jumper here  =  3.3 V out
  (jumper removed)     =  OFF
```

**`OFF` is not a position you slide to — it is the jumper taken off.** The silkscreen does not make
that obvious.

- On **one** header: jumper on the two pins at the `5V` end.
- On the **other**: pull the jumper off. Park it on a single pin so it cannot be lost; hanging on
  one pin it bridges nothing.

**Check:** meter each `+` rail against a `−` rail. One reads **5 V**, the other reads **0**.

Tape-label the 5 V one. The other is your 3V3 rail — the module leaves it alone, and the ESP32 will
feed it in step 3.

> Both rails reading 5 V means both jumpers are still fitted. Remove one.

---

## Step 2 — Switch

The switch sits off the board. Only its wires reach it.

Ours is marked **`ON  ON`** on the side — a 2-position on-on toggle, rated 2 A at 250 V against our
250 mA. Its three pins are **in a line**, and on that footprint the **middle pin is the common**.

1. Cut the **red** wire of the battery clip.
2. Battery side of the cut → either **outer** pin.
3. Module side of the cut → **middle** pin.
4. Third pin: leave empty. Insulate or trim it — loose lugs move during a drop test.

**Check:** meter on continuity, middle to the outer pin you used. It should beep in one lever
position and not the other. Choose the outer pin that conducts with the lever **up**, so up means
on. Then reconnect and confirm the green LED follows the lever.

> Battery to an *outer* pin, module to the *middle*. The other way round leaves the battery live on
> a bare lug whenever the box is off.

---

## Step 3 — ESP32

1. Push the ESP32 in at the top, rows 1–15, straddling the gap. Column `a` stays free.
2. Unplug the battery. Power the ESP32 from your **laptop USB** for now.

| # | Wire from | To |
|---|---|---|
| 1 | `a` + `GND` row | GND rail |
| 2 | `a` + `3V3` row | 3V3 rail |

**Check:** the 3V3 rail now reads **3.3 V**, and serial shows the boot banner.

```powershell
python -m platformio device monitor -d firmware
```

---

## Step 4 — Probe 1 (row 18)

| # | Wire from | To |
|---|---|---|
| 3 | probe 1 **red** | 3V3 rail |
| 4 | probe 1 **black** | GND rail |
| 5 | probe 1 **yellow** | `a18` |
| 6 | `b18` | 3V3 rail — **through the 4.7 kΩ** |
| 7 | `c18` | `a` + `D4` row |

**Check:** serial says `[1wire] sensor 1: found`.

> `absent` means wire 6. Without that resistor the probe can never be seen.

---

## Step 5 — Probe 2 (row 21)

Same pattern, its own resistor.

| # | Wire from | To |
|---|---|---|
| 8 | probe 2 **red** | 3V3 rail |
| 9 | probe 2 **black** | GND rail |
| 10 | probe 2 **yellow** | `a21` |
| 11 | `b21` | 3V3 rail — **through the second 4.7 kΩ** |
| 12 | `c21` | `a` + `D5` row |

**Check:** serial says `sensor 2: found`, and `[temp]` lines show two readings.

---

## Step 6 — Buttons

Push each button in so it **straddles the gap**. Legs land in rows 25 and 27, then 30 and 32.

| # | Wire from | To |
|---|---|---|
| 13 | `d25` | `a` + `D18` row |
| 14 | `g25` | GND rail |
| 15 | `d30` | `a` + `D19` row |
| 16 | `g30` | GND rail |

**Check:** serial shows `btn HH` when you're not touching anything. Hold button 1 → `LH`. Hold
button 2 → `HL`.

> One wire each side of the gap. Both on the same side ties the pin to ground permanently and the
> button does nothing — that's the `L`-at-rest fault.

---

## Step 7 — Contrast resistors (row 35)

Two resistors, no potentiometer.

| # | Wire from | To |
|---|---|---|
| 17 | `a35` | 5V rail — **through the 10 kΩ** |
| 18 | `b35` | GND rail — **through the 1 kΩ** |

**Check:** meter `c35` against GND. You want about **0.45 V**.

> Too dark or too faint later? Change only the 1 kΩ. Bigger (1.5 kΩ) → lighter. Smaller (680 Ω) →
> darker.

---

## Step 8 — LCD (rows 37–52)

**Find pin 1 first** — it's marked on the back of the LCD. Seat the module in **column `i`** with
pin 1 at row 37, display body hanging off the **right edge** of the board.

> If pin 1 is at the other end, flip the whole table: pin 1 at `i52`, pin 16 at `i37`. Backwards
> puts 5 V where ground belongs.

| # | LCD pin | Wire from | To |
|---|---|---|---|
| 19 | 1 `VSS` | `f37` | GND rail |
| 20 | 2 `VDD` | `f38` | 5V rail |
| 21 | 3 `V0` | `f39` | `c35` |
| 22 | 4 `RS` | `f40` | `a` + `D23` row |
| 23 | 5 `RW` | `f41` | GND rail |
| 24 | 6 `E` | `f42` | `a` + `D22` row |
| — | 7–10 | — | **leave empty** |
| 25 | 11 `D4` | `f47` | `a` + `D21` row |
| 26 | 12 `D5` | `f48` | `a` + `TX2` row |
| 27 | 13 `D6` | `f49` | `a` + `RX2` row |
| 28 | 14 `D7` | `f50` | `a` + `D15` row |
| 29 | 15 `A` | `h51` → `d51` **through the 220 Ω** | then `c51` → 5V rail |
| 30 | 16 `K` | `f52` | GND rail |

**Check:** the LCD shows `Sensor 1 off` / `Sensor 2 off`. Press a button and that row becomes a
temperature.

---

## Done — now test on battery

Unplug the laptop USB. Run a cable from the module's **USB-A socket** to the ESP32's USB port, then
plug the battery back in.

**Never both at once.** Laptop USB for flashing and serial; battery for the demo.

Flip the switch off: the LCD goes dark and the web page says "no data available". That's
requirement 3 demonstrated.

---

## If something's wrong

| What you see | It's almost always |
|---|---|
| Probe says `absent` or `-127` | Its 4.7 kΩ — wire 6 or 11 |
| Button does nothing, serial shows `L` at rest | Both button wires on the same side of the gap |
| LCD dark and unlit | Backlight — wire 29, and it needs 5 V not 3.3 V |
| LCD lit but blank | Contrast — meter `c35`, want 0.45 V |
| LCD shows solid blocks | Contrast too high, or `RW` (wire 23) not grounded |
| LCD shows garbage | `D4`–`D7` order — wires 25–28 go to `D21`, `TX2`, `RX2`, `D15` in that order |
| Whole board dead on battery | The module's white button, or the switch is off |
| Odd faults after moving wires | Both `−` rails must be joined; the module does this, but check |

---

## Why it's built this way

**Two voltages.** The LCD needs 5 V or its contrast and backlight don't work. The probes and the
ESP32's pins run at 3.3 V. So the module supplies 5 V, and the ESP32's own regulator supplies 3.3 V
out of its `3V3` pin. That's why one module jumper is set to `OFF` — if the module also drove the
3.3 V rail, two regulators would fight over it.

**The 4.7 kΩ resistors aren't optional.** A DS18B20 can only pull its data line *low*. The resistor
pulls it back high. Without one the line never moves and the probe is invisible. One per probe,
because each has its own bus — which is how the firmware can tell you *which* probe was unplugged.

**The buttons have no resistors** because the ESP32 has built-in pull-ups, switched on in firmware.
Adding your own would fight them.

**Contrast is two fixed resistors, not a pot.** At 5 V the usable range is a few tenths of a volt
wide — hard to hit with a pot, easy to knock out of adjustment, and one more thing to work loose
when the box gets dropped.

**The LCD overhangs right** because the display is deeper than the board is wide. Overhanging left
would bury every hole in those rows underneath it.

**The ESP32 is powered through its USB socket**, not its `VIN` pin, because `VIN` is on the header
the module's body covers. The switch still kills everything, since it's upstream of the supply.

**Only the switch's wires touch the board.** It gets panel-mounted in the finished box, so wiring it
on flying leads now means nothing changes later.
