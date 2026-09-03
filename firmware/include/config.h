#pragma once
// =============================================================================
// ECE:4880 Lab 1 -- Third Box configuration
// All pin assignments and tunable constants live here so that nobody has to
// go hunting through main.cpp to re-wire the prototype.
// =============================================================================

#define FIRMWARE_VERSION "0.1.0"

// -----------------------------------------------------------------------------
// Pin map -- ESP32 DevKit v1 (WROOM-32)
//
// Avoided on purpose:
//   GPIO 6-11  : wired to the SPI flash chip, using them bricks the boot
//   GPIO 0,2,12,15 : strapping pins, they change boot mode if pulled at reset
//   GPIO 34-39 : input-only, no internal pull-ups (useless for our buttons)
// -----------------------------------------------------------------------------

// Each DS18B20 gets its OWN 1-Wire bus rather than sharing one.
// Why: with separate buses, "sensor 2 is unplugged" is a trivially detectable
// condition (bus 2 has no devices). On a shared bus we would have to track ROM
// addresses and could not tell which probe vanished. Requirement 4d and 2d.
#define PIN_SENSOR_1   4
#define PIN_SENSOR_2   5

// Momentary push buttons to GND, using the internal pull-ups (pressed == LOW).
#define PIN_BUTTON_1   18
#define PIN_BUTTON_2   19

// I2C bus -- used by the LCD1602 backpack variant.
#define PIN_I2C_SDA    21
#define PIN_I2C_SCL    22

// Onboard LED -- heartbeat, so you can tell the firmware is alive at a glance.
#define PIN_STATUS_LED 2

// -----------------------------------------------------------------------------
// Display -- HD44780 16x2 character LCD ("LCD1602")
//
// 16 columns x 2 rows is a good fit for requirement 4: one row per sensor, and
// "Sensor 1 off" is 12 characters, so the display can say exactly what the
// handout asks for rather than an abbreviation.
//
// Set DISPLAY_TYPE to match the module you actually have:
//
//   DISPLAY_LCD1602_I2C       a small daughterboard is soldered to the back
//                             (chip + blue trimmer pot), 4 pins: GND VCC SDA SCL
//   DISPLAY_LCD1602_PARALLEL  bare module, one row of 16 pins, no daughterboard
// -----------------------------------------------------------------------------
#define DISPLAY_LCD1602_I2C       1
#define DISPLAY_LCD1602_PARALLEL  2

#define DISPLAY_TYPE   DISPLAY_LCD1602_PARALLEL

#define LCD_COLS       16
#define LCD_ROWS       2

// -- I2C backpack variant -----------------------------------------------------
#define LCD_I2C_ADDR   0x27   // most PCF8574 backpacks; some are 0x3F

// TIMING BUDGET -- Requirement 4a: the display must update within 20 ms of a
// button press. LiquidCrystal_I2C sends each character as two 4-bit nibbles,
// and each nibble costs three single-byte I2C transactions (data, data|EN,
// data) to strobe the enable line. At ~20 bit-times per transaction that is
// about 120 bit-times per character, so a full 32-character refresh is ~3840:
//     100 kHz -> 3840 / 100000 = 38.4 ms   <-- BLOWS THE 20 ms BUDGET
//     400 kHz -> 3840 / 400000 =  9.6 ms   <-- fits
// We therefore run the bus at 400 kHz. The PCF8574 is specified for 100 kHz
// standard mode, so this is outside its datasheet; it works on typical modules
// but it is exactly the sort of claim that must be measured rather than
// assumed. The firmware reports the real worst case at GET /api/info.
// If the display glitches, drop to 100000 -- and then requirement 4a needs a
// different approach, most likely the parallel variant below.
#define I2C_CLOCK_HZ   400000

// -- Parallel variant (bare 16-pin module, 4-bit mode) ------------------------
// Direct GPIO, so speed is set by the HD44780 itself: ~37 us execution per
// character, hence ~1.2 ms for a full 32-character refresh. Comfortably inside
// requirement 4a, at the cost of six GPIO and a contrast pot.
//
// ALL SIX PINS ARE ON THE SAME HEADER as the sensors, buttons, 3V3 and GND.
// That is deliberate, not tidiness. A DevKit PCB is wider than the span of its
// own pin rows, so once it is pushed into a single breadboard the body covers
// every hole except one column, and only ONE of its two headers can be reached.
// Wiring the display to the far header (13/14/25/26/27/33, the obvious choice
// on paper) makes the prototype physically impossible to build on one board.
//
// Free pins remaining on this header after sensors and buttons: 23, 22, 21, 17,
// 16, 15 -- exactly six, which is what a 4-bit HD44780 needs.
//   GPIO 15 is a strapping pin, but it is safe here: an LCD data pin is a
//   high-impedance input and cannot pull it at reset.
//   GPIO 16/17 are free on a WROOM-32. On a WROVER they are wired to the PSRAM
//   and must not be used -- check which module you have before assuming.
//   GPIO 21/22 are the I2C pins, unused in parallel mode.
#define PIN_LCD_RS     23
#define PIN_LCD_EN     22
#define PIN_LCD_D4     21
#define PIN_LCD_D5     17
#define PIN_LCD_D6     16
#define PIN_LCD_D7     15

// -----------------------------------------------------------------------------
// Sensing
// -----------------------------------------------------------------------------
// DS18B20 conversion time vs. resolution:
//   9 bit  = 0.5    C,  93.75 ms
//  10 bit  = 0.25   C, 187.5  ms
//  11 bit  = 0.125  C, 375    ms   <-- our choice
//  12 bit  = 0.0625 C, 750    ms
// Requirement 8c/8d need +/-4 C and +/-2 C accuracy; the DS18B20 part accuracy
// is +/-0.5 C, so quantisation is nowhere near the limiting factor. 11 bits
// leaves generous margin inside our 1 Hz sample period.
#define SENSOR_RESOLUTION_BITS 11
#define SAMPLE_PERIOD_MS       1000   // Requirement 5a: one update per second
#define CONVERSION_WAIT_MS     400    // > 375 ms conversion at 11-bit

// How often to re-scan a bus that currently reports no device. This is what
// makes hot-plug work with no user intervention (Requirement 2d).
#define REDISCOVER_PERIOD_MS   2000

// DallasTemperature returns this sentinel when the probe does not answer.
#define TEMP_DISCONNECTED_C    -127.0f

// -----------------------------------------------------------------------------
// History ring buffer
// -----------------------------------------------------------------------------
// Requirement 5c: the PC must be able to draw the last 300 s within 10 s of the
// PC software starting. The PC cannot have data from before it launched, so the
// history has to live HERE, in the box, and be handed over on connect.
// Storage: 300 samples * 2 sensors * 2 bytes = 1200 bytes. Trivial on ESP32.
#define HISTORY_LEN            300
#define HISTORY_INVALID        INT16_MIN   // "no reading" -- distinct from any real value

// -----------------------------------------------------------------------------
// Buttons
// -----------------------------------------------------------------------------
#define DEBOUNCE_MS            25

// -----------------------------------------------------------------------------
// Diagnostics
// -----------------------------------------------------------------------------
// Print one temperature line per sample on the serial port. Essential during
// bench bring-up, when the display is not wired yet and WiFi may not be
// configured either -- it is then the only way to see whether the probes are
// actually reading. Set to 0 once the box is assembled and the log is noise.
#define SERIAL_TELEMETRY       1

// -----------------------------------------------------------------------------
// Network
// -----------------------------------------------------------------------------
#define HTTP_PORT              80
#define MDNS_HOSTNAME          "thermobox"   // -> http://thermobox.local
#define WIFI_RETRY_PERIOD_MS   5000
