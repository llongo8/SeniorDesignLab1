# Bill of Materials

Doubles as the shopping list. Check the lab stockroom (2319 SC / 1313 SC) before ordering anything.
Remember the lab rules: equipment and supplies stay in the lab unless an instructor says otherwise.

**Status:** ✅ have it, verified working · 🛒 still to get · ⚠️ have it but not yet proven

---

## 1. Core electronics — all working on the breadboard

| ✔ | Qty | Item | Notes | Est. |
|---|---|---|---|---|
| ✅ | 1 | ESP32 DevKit v1 (WROOM-32) | The brain. WiFi is why we are not using the ATmega328P — see [ADR-001](decisions/ADR-001-esp32-as-main-mcu.md). | $8 |
| ✅ | 2 | DS18B20 waterproof probe, 1 m stainless lead | Sealed, immersible, −55 to +125 °C. Ice bath measured +0.6 / −0.5 °C. | $4 ea |
| ✅ | 2 | 4.7 kΩ resistor | 1-Wire pull-up, **one per bus**. Came in the box with the probes. | included |
| ✅ | 1 | LCD1602, bare 16-pin, blue backlight | Blue is negative-mode STN, so it needs its backlight lit to be readable at all. Runs from 5 V. | $5 |
| ✅ | 1 | 10 kΩ trimmer potentiometer | LCD contrast on pin 3. Two legs one side, one the other — the lone leg is the wiper. | $1 |
| ✅ | 1 | 220 Ω resistor | LCD backlight current limit, from 5 V. | included |
| ✅ | 2 | Tactile pushbutton (breadboard) | Prototype only — the final build wants panel-mount. | included |
| ⚠️ | 1 | Toggle switch, 3 terminal SPDT, on-on | Marked "T004", cURus stamp. Confirmed on-on by detent count. **Not yet wired.** Check it has a threaded bushing for panel mounting; if not, buy one that does. | $3 |
| ✅ | 1 | Breadboard, 830 point | REXQualis kit. | included |
| ✅ | — | Jumper wires, male-male | REXQualis kit. | included |
| ✅ | 1 | USB data cable | A charge-only cable cost us an hour — this one is known good. | included |

> The **Arduino Uno** currently supplies 5 V to the LCD. It is scaffolding, not part of the design,
> and disappears once we have a real 5 V supply.

## 2. To finish the prototype (requirement 3)

| ✔ | Qty | Item | Why | Est. |
|---|---|---|---|---|
| 🛒 | 1 | **Second breadboard**, 830 or 400 point | The blocker. A DevKit is wider than its own pin span, so on one board its body covers every hole but one column and **only one of its two headers can be reached**. `VIN` and `EN` are both on the unreachable side, and requirement 3 needs to switch the box's power input. Butt two boards together and let the module straddle the join. Female-to-male jumpers also work if the kit has any. | $5 |
| 🛒 | 1 | **5 V power source** — pick one: | | |
| | | *(a)* USB power bank + USB-A breakout board | Cheapest; most of us own the bank. ~12 h from 5000 mAh. Test early — some banks cut out below 50–100 mA. | $3 |
| | | *(b)* 18650 + holder + TP4056 + MT3608 boost | What this BOM specifies. ~7 h, recharges in place, reads better in the report than a power bank cable-tied inside a box. Protected cells only. | $14 |
| | | *(c)* 9 V battery + MB102 module **or** LM2596 buck | Uses the 9 V clip already in the kit. Check for an MB102 before buying — REXQualis kits often include one and it takes the barrel plug directly. Only ~2 h of runtime, which is enough for a checkoff demo. | $0–2 |

See [why the rail must be 5 V](#the-rail-must-be-5-v-however-it-is-generated). A 9 V battery is
fine *behind a regulator* — what it must not do is feed `VIN` directly.

## 3. Enclosure and panel (requirements 1b, 2a–2c)

Longest lead time, and the part that cannot be compressed at the end. Order first.

| ✔ | Qty | Item | Notes | Est. |
|---|---|---|---|---|
| 🛒 | 1 | ABS project box, ~120 × 80 × 40 mm | Must fit the cell, board, LCD and two connectors. | $10 |
| 🛒 | 2 | GX12-3 panel connector, male + female pair | 3 pins = 3V3 / DATA / GND. Threaded, keyed, made for repeated use by a casual user (req 2b), and they pull free rather than transmitting shock into the PCB (req 2c). | $4 pr |
| 🛒 | 2 | Panel-mount momentary pushbutton, 12 mm | The tactile switches are breadboard parts and will not survive a drop test or a panel cutout. | $2 ea |
| 🛒 | 1 | Perfboard, ~70 × 50 mm | **No breadboard in the final build** — requirement 2a is a drop from bench height. | $5 |
| 🛒 | — | M3 standoffs, screws, nuts | Everything inside is fastened. Nothing rests. A loose cell in a dropped box is a hammer. | $5 |
| 🛒 | 2 | Cable gland or rubber grommet | Strain relief where each probe lead enters the box. | $3 |

**LCD panel cutout:** the module is ~80 × 36 mm with mounting holes on 75 × 31 mm centres. The
visible window needs roughly 71 × 26 mm. Cut the rectangle with a rotary tool or drill-and-file, and
mount on M3 standoffs so the glass is not stressed.

**Probe cable length (req 1b: 1.0 ± 0.1 m):** measure from the connector face to the probe tip
*after* terminating the GX12, not the bare lead. The connector adds length.

## 4. Consumables and tools

Mostly stocked in the lab — check before buying.

| ✔ | Item | Notes |
|---|---|---|
| 🛒 | Hookup wire, 22 AWG stranded | Stranded, not solid: solid wire work-hardens and snaps under vibration. |
| 🛒 | Heat-shrink assortment | Every joint outside a connector shell. |
| 🛒 | Solder | Lab restocks it; email TA Joel if it is out. |
| ✅ | Multimeter | Lab bench. Already earned its keep on the switch and the buttons. |
| — | Soldering iron, wire strippers, drill, step bit, file or rotary tool | Lab equipped. |

## Cost

| Group | Est. |
|---|---|
| Already have | ~$30 |
| Finish the prototype | $8–19 |
| Enclosure and panel | ~$35 |
| Consumables | ~$10 |
| **Still to spend** | **$50–65** |

Less whatever the stockroom supplies.

---

## Wiring notes

### One 1-Wire bus per probe

Each DS18B20 gets its own GPIO and its own 4.7 kΩ pull-up to 3V3, rather than sharing one bus.

The requirements are what force this. Requirement 4d needs "sensor 2 is unplugged" to be a
distinguishable condition, and requirement 2d needs recovery with no user intervention. With
separate buses, "no device answers on bus 2" *is* the answer, directly. On a shared bus we would
have to enumerate ROM addresses, remember which serial number is which probe, and handle two
devices that both went quiet — for no benefit, since we have GPIO to spare.

### Pin map

| Signal | ESP32 GPIO |
|---|---|
| Sensor 1 data | 4 |
| Sensor 2 data | 5 |
| Button 1 | 18 |
| Button 2 | 19 |
| LCD RS | 23 |
| LCD E | 22 |
| LCD D4–D7 | 21, 17, 16, 15 |
| Status LED | 2 (onboard) |

Every one of these is on the **same header**, which is not tidiness — see the note in
[the wiring guide](06-breadboard-wiring.md). Avoided deliberately: **GPIO 6–11** are wired to the
SPI flash and using them prevents boot; **GPIO 0, 2, 12** are strapping pins that change boot mode
if held at reset; **GPIO 34–39** are input-only with no internal pull-ups, so they cannot serve as
our buttons.

### Buttons

Wired to ground and using the internal pull-ups (`INPUT_PULLUP`), so pressed reads LOW. No external
resistors. Debounce is 25 ms in firmware.

A 4-leg tactile switch is **two pairs already joined inside the part**, and the joined legs are the
two on the same side of the breadboard channel. Taking both wires from one side shorts the GPIO
straight to ground — which cost us an evening on button 1. One wire each side of the channel, same
row. The firmware prints raw pin levels as `btn HH`; an `L` at rest is always a wiring fault.

### Using a 3-terminal SPDT switch

A 3-terminal toggle is **usually** SPDT: one pole, two throws. The centre terminal is the *common*
(the pole), and each outer terminal connects to it in one lever position. Requirement 3 only needs
on/off, so we use the common and **one** outer terminal, and leave the third unconnected.

Do not take the part marking as authority for this. Ours reads "T004" with a cURus stamp — that
stamp is a UL certification mark, not a manufacturer, and generic toggles carry inconsistent mould
markings that map to no reliable datasheet. **The meter is the authority.** It takes a minute and
it is the only check that cannot be wrong.

Ours is a 2-position **on-on**, confirmed by the detent count. Wire it like this:

```
   battery + ──────────►  [ terminal A ]
                                 │   closed when the lever selects A  ->  ON
                          [ common / centre ] ────────►  5 V rail (VIN + LCD)
                                 │   closed when the lever selects B  ->  OFF
                                 X  [ terminal B ]  left unconnected
```

**Feed the battery into a throw, and take the load off the common — not the other way round.**

It is tempting to put battery + on the common, since that is how an SPST is drawn. Do not. On an
on-on switch there is no open position: the common is always connected to *something*. With
battery + on the common, the off position energises terminal B, leaving battery positive sitting on
a bare unconnected lug inside the enclosure whenever the box is switched off — a short waiting to
find the cell holder, the boost module or a stray strand.

Feeding a throw instead means terminal B is only ever connected to the (now isolated) load side, so
it is never live. Insulate or trim it anyway; free solder lugs move around during a drop test.

**Identify the common pin before soldering.** It is almost always the centre one, but confirm it:

1. Multimeter to continuity (the beeping mode).
2. Probe centre against one outer terminal. Flip the lever back and forth.
3. The centre pin beeps against **one** outer terminal in one position and against **the other**
   outer terminal in the other position. The pin that beeps in *both* positions is the common.
4. If instead one pair beeps in one position only and never involves a third pin, you have an SPST
   with a spare or illuminated terminal — see the warning below.

**Pick the outer terminal so that "up" means on.** On a standard toggle, the lever points *away*
from the contact it closes, so the up position usually closes the *lower* terminal. Do not guess:
put the meter on it, choose the terminal that conducts with the lever up, and wire that one. A
demo where the switch reads backwards is an avoidable way to lose marks on a requirement that is
otherwise free.

> **Careful: not every 3-terminal switch is SPDT.** Illuminated rocker switches also have three
> terminals — line, load, and a lamp ground — and wiring one as if it were SPDT either shorts the
> supply or leaves the lamp permanently lit. If the switch has a window, a coloured lens or an
> internal LED, look up its part number before wiring it. The continuity test above distinguishes
> them: a true SPDT has one pin common to both lever positions, an illuminated SPST does not.

### The rail must be 5 V, however it is generated

Both loads want 5 V. `VIN` is happy there, and so are the LCD `VDD` and backlight, so a single 5 V
rail powers everything with no second regulator.

**Do not feed a 9 V battery straight into `VIN`**, which is the obvious thing to do given the 9 V
clip in the kit:

- The DevKit drops `VIN` to 3.3 V with a linear AMS1117. From 9 V at our ~200 mA that is
  `(9 − 3.3) × 0.2 ≈ 1.1 W` dissipated in a SOT-223 package. It gets very hot and thermally shuts
  down, which presents as an ESP32 that is mysteriously unreliable.
- It does not help the LCD. `VIN` is an input only — the DevKit has no 5 V output — so a 9 V
  battery still leaves the display needing its own regulator.
- A 9 V alkaline is about 500 mAh nominal and much less at 200 mA. One or two hours.

### Resistors cannot substitute for a regulator

Tempting, and wrong: **a resistor divider is not a regulator, because its output moves with the
load.** Our current swings from ~40 mA idle to 400 mA when the WiFi transmits.

Size a series resistor to drop 9 V to 5 V at 200 mA and you get `R = 4 / 0.2 = 20 Ω`. Then:

| State | Current | Drop across 20 Ω | Voltage at the box |
|---|---|---|---|
| Idle | 40 mA | 0.8 V | **8.2 V** — past the LCD 5.5 V limit |
| Average | 200 mA | 4.0 V | 5.0 V |
| WiFi transmit | 400 mA | 8.0 V | **1.0 V** — brownout and reset |

Correct at exactly one current, and the load never holds still. It would damage the LCD at idle and
reset the board on every transmission, while burning 0.8 W in a resistor that would need a 2 W
rating.

### Using the 9 V battery properly

With a **regulator** in front of it, 9 V is fine — the objection above is only to feeding `VIN`
directly. Two ways:

- **MB102 breadboard power supply module.** Clips onto the power rails, takes a barrel jack input
  (which the kit 9 V clip plugs straight into) and outputs switchable 3.3 V / 5 V. Often included in
  REXQualis kits — check before buying anything.
- **LM2596 buck converter, ~$2.** Switching, ~85% efficient, adjustable output trimmed to 5 V.

Runtime is the remaining catch: ~500 mAh at 200 mA is about **2 hours**. Enough for a checkoff
demo, poor for anything else. A USB power bank is also a 5 V battery, gives ~12 hours, and
recharges.

4×AA gives 6 V, which `VIN` handles, but 6 V is above the HD44780 5.5 V limit so the LCD would need
its own regulator. Workable, but it adds a part rather than removing one.

Whichever we choose, write down which and why — the trade-off is worth a paragraph in the report.

### Keep the LCD signal runs short

The display is driven in 4-bit parallel mode, six signal lines at 3.3 V into a 5 V part. That is
inside the HD44780 logic-high threshold with little margin, so keep those runs short and direct on
the perfboard. If the display turns flaky rather than dead once it is boxed, that margin is the
first suspect, and the fix is a level shifter on the six lines — not lowering `VDD`, which costs
contrast.
