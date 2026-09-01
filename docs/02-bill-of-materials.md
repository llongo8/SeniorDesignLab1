# Bill of Materials

Check the lab stockroom (2319 SC / 1313 SC) before ordering anything. Remember the lab rules:
equipment and supplies stay in the lab unless an instructor says otherwise.

## Core electronics

| Qty | Item | Notes | Est. |
|---|---|---|---|
| 1 | ESP32 DevKit v1 (WROOM-32) | The brain. WiFi is the reason we are not using the ATmega328P. | $8 |
| 2 | DS18B20 waterproof probe, 1 m stainless lead | Sealed, immersible, −55 to +125 °C, ±0.5 °C. Buy a spare. | $4 ea |
| 1 | SSD1306 OLED, 128×64, I2C, 0.96" | Check whether yours is address 0x3C or 0x3D. | $5 |
| 2 | 4.7 kΩ resistor | 1-Wire pull-up, **one per bus** — see the wiring note below. | — |
| 2 | Momentary panel-mount pushbutton | One per sensor. | $2 ea |
| 1 | Toggle switch, 3 terminal SPDT, on-on | Requirement 3. Breaks the battery line; any toggle handles our ~250 mA easily. **Ours is marked "T004"** with a cURus stamp (a UL certification mark, not a brand — there is no datasheet to find under it). Confirmed 2-position on-on. [Wiring note](#using-a-3-terminal-spdt-switch) — the battery feeds a throw, not the common. | $3 |

## Connectors and cable (requirement 2b)

| Qty | Item | Notes | Est. |
|---|---|---|---|
| 2 | GX12-3 panel connector, male + female pair | 3 pins = 3V3 / DATA / GND. Threaded, keyed, meant for repeated use by a casual user. | $4 pr |
| — | Heat-shrink, cable glands or grommets | Strain relief at both ends of every probe lead. | $5 |

3.5 mm TRS jacks are the cheap alternative and also carry three conductors, but they are easy to
short while being inserted (the sleeve sweeps across the ring and tip on the way in). With 3V3 and
GND on those contacts, that is a momentary short of the supply on every plug-in. GX12 avoids it.

## Power (requirement 1c)

| Qty | Item | Notes | Est. |
|---|---|---|---|
| 1 | Protected 18650 cell, ~3000 mAh | Protected only. Never an unprotected cell in a student enclosure. | $8 |
| 1 | 18650 holder | Must be **screwed down**, not loose — requirement 2a is a drop test. | $2 |
| 1 | TP4056 charge module with protection | USB charging without opening the box. | $2 |
| 1 | MT3608 or similar 5 V boost | 3.7 V cell → 5 V into ESP32 VIN. | $2 |

4×AA in a holder is a perfectly good alternative and avoids all lithium handling questions. It is
bulkier and not rechargeable. Either is defensible; write down which you chose and why.

## Enclosure and mechanical (requirements 2a–2c)

| Qty | Item | Notes | Est. |
|---|---|---|---|
| 1 | ABS project box, ~120 × 80 × 40 mm | Room for the cell, board, display and two connectors. | $10 |
| — | M3 standoffs, screws, nuts | Everything inside is fastened. Nothing rests. | $5 |
| — | Perfboard or a small custom PCB | **No breadboard in the final build.** It will not survive the drop test. | $5 |

**Estimated total: $75–90**, less whatever the stockroom supplies.

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
| OLED SDA | 21 |
| OLED SCL | 22 |
| Status LED | 2 (onboard) |

Avoided deliberately: **GPIO 6–11** are wired to the SPI flash and using them prevents boot;
**GPIO 0, 2, 12, 15** are strapping pins that change boot mode if held at reset; **GPIO 34–39** are
input-only with no internal pull-ups, so they cannot serve as our buttons.

### Buttons

Wired to ground and using the internal pull-ups (`INPUT_PULLUP`), so pressed reads LOW. No external
resistors. Debounce is 25 ms in firmware.

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
                          [ common / centre ] ────────►  5 V boost input
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

**Identify the common pin before soldering.** It is almost always the centre one, but confirm it
rather than assume:

1. Multimeter to continuity (the beeping mode).
2. Probe centre against one outer terminal. Flip the lever back and forth.
3. The centre pin beeps against **one** outer terminal in one position and against **the other**
   outer terminal in the other position. The pin that beeps in *both* positions is the common.
4. If instead one pair beeps in one position only and never involves a third pin, you have an SPST
   with a spare or illuminated terminal — see the warning below.

**Ours is on-on** (two detents), so the box is powered in one position and unpowered in the other.
That is exactly what requirement 3 needs. The only thing still to determine at the bench is which
pin is the common and which throw gives lever-up = on.

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

### Keep the I2C run short

The display bus runs at 800 kHz to meet the 20 ms budget of requirement 4a — see
[the timing analysis](01-system-design.md#the-20-ms-trap). Keep SDA/SCL under about 15 cm inside
the box. If the display glitches, drop `I2C_CLOCK_HZ` to 400000 and expect to redesign the update
path to a partial window instead of a full frame.
