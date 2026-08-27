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
| 1 | SPST panel-mount toggle switch | Requirement 3. Must break the battery line, rated for the pack current. | $3 |

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

### Keep the I2C run short

The display bus runs at 800 kHz to meet the 20 ms budget of requirement 4a — see
[the timing analysis](01-system-design.md#the-20-ms-trap). Keep SDA/SCL under about 15 cm inside
the box. If the display glitches, drop `I2C_CLOCK_HZ` to 400000 and expect to redesign the update
path to a partial window instead of a full frame.
