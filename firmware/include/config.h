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

// SSD1306 OLED, I2C.
#define PIN_I2C_SDA    21
#define PIN_I2C_SCL    22

// Onboard LED -- heartbeat, so you can tell the firmware is alive at a glance.
#define PIN_STATUS_LED 2

// -----------------------------------------------------------------------------
// Display
// -----------------------------------------------------------------------------
#define OLED_WIDTH     128
#define OLED_HEIGHT    64
#define OLED_I2C_ADDR  0x3C   // some modules are 0x3D -- check the silkscreen

// TIMING BUDGET -- Requirement 4a: display must update within 20 ms of a press.
// A full 128x64 SSD1306 frame is 1024 payload bytes. Over I2C each byte costs
// ~9 bit-times, so the transfer alone is:
//     400 kHz -> 1024 * 9 / 400000  = 23.0 ms   <-- BLOWS THE 20 ms BUDGET
//     800 kHz -> 1024 * 9 / 800000  = 11.5 ms   <-- fits, with room to spare
// We therefore run the bus at 800 kHz. Most SSD1306 modules are specified for
// 400 kHz but run reliably well past 1 MHz on short (<15 cm) traces. If your
// display glitches, drop to 400000 and switch to a partial-window update.
// The firmware measures the real worst case at runtime -- see /api/info.
#define I2C_CLOCK_HZ   800000

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
// Network
// -----------------------------------------------------------------------------
#define HTTP_PORT              80
#define MDNS_HOSTNAME          "thermobox"   // -> http://thermobox.local
#define WIFI_RETRY_PERIOD_MS   5000
