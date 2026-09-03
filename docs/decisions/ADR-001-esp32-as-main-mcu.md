# ADR-001: Use an ESP32 as the main MCU, not the ATmega328P

**Date:** 2026-08-27 · **Status:** Accepted

## Context

We own an Arduino Uno/Nano (ATmega328P). Requirement 1c says the third box is battery operated and
that "the temperature data is then available on the internet". Requirement 5 says a networked
computer displays that data live.

The ATmega328P has no network interface. If the box is running on its own battery, there is no USB
tether to the PC, so the data has to leave the box over a radio. Something in the box must speak
WiFi.

## Options considered

**A. ESP32 as the sole MCU.** WiFi and TCP/IP on-chip, 320 kB RAM, 34 GPIO, programmed with the
same Arduino C++ we already know.

**B. ATmega328P plus an ESP8266 (ESP-01) WiFi co-processor.** Keeps the board we own. The 328P
handles sensors, display and buttons; the ESP-01 bridges to WiFi over UART.

**C. ATmega328P tethered to the PC over USB serial.** No radio at all; the PC relays to the
network.

## Decision

**Option A.** The ESP32 becomes the brain of the third box. The ATmega328P stays as a bench spare.

## Rationale

- **Option C conflicts with requirement 1c.** A box that only works while tethered to a PC by USB
  is not a battery-operated thermometer whose data is on the internet. We would be arguing with the
  requirement at checkoff, which is not a position worth being in for the sake of an $8 part.
- **Option B doubles the firmware.** Two toolchains, two binaries, and a hand-rolled serial
  protocol between them — plus a new class of bug where the two halves disagree about state.
  The 328P also has 2 kB of RAM, and our 300-sample ring buffer needs 1.2 kB of it, leaving almost
  nothing for the display buffer and the UART buffers.
- **Option A makes the hard requirement easy.** The 300-sample history costs 1200 bytes of 320 kB.
  We have GPIO to spare, so each probe gets its own 1-Wire bus, which is what makes "sensor 2 is
  unplugged" directly detectable (requirements 4d and 2d).
- Cost is about $8 and we already have a board.

## Consequences

- The ATmega328P is not part of the delivered design. Say so in the report, with this reasoning —
  a documented trade-off is worth more than an unexplained parts list.
- Firmware targets `espressif32` under PlatformIO; the build is verified in CI-style by
  `pio run` (currently: RAM 14.8%, Flash 62.5%, zero warnings under `-Wall -Wextra`).
- The box needs a WiFi network at demo time. We supply our own hotspot rather than depending on
  campus WPA2-Enterprise — see [system design §8](../01-system-design.md#8-network).
- 3.3 V logic throughout. The DS18B20s run at 3.3 V. The LCD1602 needs a 5 V supply for contrast
  and backlight, but its signal lines are driven at 3.3 V and pin 5 `RW` is grounded so it never
  drives back — no level shifting needed. See the wiring guide.
