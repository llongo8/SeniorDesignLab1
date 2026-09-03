// =============================================================================
// ECE:4880 Lab 1 -- "Third Box" firmware
// University of Iowa, Capstone Senior Design, Fall 2026
//
// Responsibilities:
//   * Sample two DS18B20 probes once per second, non-blocking.
//   * Drive a local OLED showing per-sensor temperature / OFF / ERROR.
//   * Toggle each sensor local display from a physical button OR the network.
//   * Keep the last 300 s of readings so the PC can draw history the instant
//     its software starts.
//   * Serve a small JSON API over WiFi.
//
// See docs/00-requirements-traceability.md for the requirement each block maps to.
// =============================================================================

#include <Arduino.h>
#include <Wire.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <ArduinoJson.h>

#include "config.h"
#include "secrets.h"

// -----------------------------------------------------------------------------
// Hardware objects
// -----------------------------------------------------------------------------
static const uint8_t SENSOR_COUNT = 2;

static Adafruit_SSD1306 oled(OLED_WIDTH, OLED_HEIGHT, &Wire, -1);
static WebServer        server(HTTP_PORT);

static const uint8_t buttonPins[SENSOR_COUNT] = { PIN_BUTTON_1, PIN_BUTTON_2 };

// One independent 1-Wire bus per probe -- see the note in config.h.
static OneWire           oneWire[SENSOR_COUNT] = { OneWire(PIN_SENSOR_1),
                                                   OneWire(PIN_SENSOR_2) };
static DallasTemperature bus[SENSOR_COUNT]     = { DallasTemperature(&oneWire[0]),
                                                   DallasTemperature(&oneWire[1]) };

// -----------------------------------------------------------------------------
// State
// -----------------------------------------------------------------------------
struct SensorState {
    bool  present   = false;   // probe is plugged in and answering  (Req 4d)
    bool  displayOn = false;   // button state, local or virtual     (Req 4, 5b)
    float tempC     = NAN;
};
static SensorState sensor[SENSOR_COUNT];

struct ButtonState {
    bool     stablePressed = false;
    bool     lastRaw       = false;
    uint32_t lastChangeMs  = 0;
};
static ButtonState button[SENSOR_COUNT];

// Ring buffer of 1 Hz samples, centi-degrees C, HISTORY_INVALID == no reading.
static int16_t  history[SENSOR_COUNT][HISTORY_LEN];
static uint16_t histHead   = 0;   // index of the next slot to write
static uint16_t histFilled = 0;   // how many slots hold real samples

// Non-blocking sampling state machine.
enum SampleState { SAMPLE_IDLE, SAMPLE_CONVERTING };
static SampleState sampleState    = SAMPLE_IDLE;
static uint32_t    samplePeriodMs = 0;   // start of the current 1 s period
static uint32_t    convStartMs    = 0;

// Instrumentation -- this is the evidence for the Req 4a timing claim in the
// report. Exposed at GET /api/info so we can quote measured numbers, not guesses.
static uint32_t maxRenderUs        = 0;
static uint32_t maxButtonLatencyUs = 0;

// -----------------------------------------------------------------------------
// Display
// -----------------------------------------------------------------------------
static void renderDisplay()
{
    const uint32_t t0 = micros();

    oled.clearDisplay();
    oled.setTextColor(SSD1306_WHITE);

    // Header: how to reach us on the network.
    oled.setTextSize(1);
    oled.setCursor(0, 0);
    if (WiFi.status() == WL_CONNECTED) {
        oled.print(WiFi.localIP());
    } else {
        oled.print(F("WiFi: connecting..."));
    }
    oled.drawFastHLine(0, 10, OLED_WIDTH, SSD1306_WHITE);

    for (uint8_t i = 0; i < SENSOR_COUNT; i++) {
        const int16_t y = 14 + i * 26;

        if (sensor[i].displayOn && sensor[i].present) {
            // Normal case: "S1  22.5C"
            oled.setTextSize(1);
            oled.setCursor(0, y + 4);
            oled.printf("S%u", i + 1);

            oled.setTextSize(2);
            oled.setCursor(20, y);
            oled.printf("%.1fC", sensor[i].tempC);

        } else if (sensor[i].displayOn && !sensor[i].present) {
            // Req 4d: sensor unplugged or faulty while its button is on.
            // Inverted text so the fault is unmistakable at a glance.
            oled.setTextSize(1);
            oled.setTextColor(SSD1306_BLACK, SSD1306_WHITE);
            oled.setCursor(0, y + 4);
            oled.printf(" SENSOR %u ERROR ", i + 1);
            oled.setTextColor(SSD1306_WHITE);

        } else {
            // Req 4: the screen must say so when the button for a sensor is off.
            oled.setTextSize(1);
            oled.setCursor(0, y + 4);
            oled.printf("Sensor %u off", i + 1);

            // Req 4d says "if ANY temperature sensor is not plugged into the
            // third box ... the display should notify the user". We therefore
            // still flag the fault while the button is off.
            // ACTION: confirm this reading with the TA -- see docs/05-open-questions.md
            if (!sensor[i].present) {
                oled.setTextColor(SSD1306_BLACK, SSD1306_WHITE);
                oled.setCursor(92, y + 4);
                oled.print(F("ERR"));
                oled.setTextColor(SSD1306_WHITE);
            }
        }
    }

    oled.display();   // the expensive part: one full 1024-byte I2C frame

    const uint32_t dt = micros() - t0;
    if (dt > maxRenderUs) maxRenderUs = dt;
}

// -----------------------------------------------------------------------------
// Sensors
// -----------------------------------------------------------------------------
// Re-enumerate one bus. This is the whole of our hot-plug support: a probe that
// reappears is found here and reconfigured with no user action. (Req 2d)
static bool discoverBus(uint8_t i)
{
    bus[i].begin();
    if (bus[i].getDeviceCount() < 1) return false;
    bus[i].setResolution(SENSOR_RESOLUTION_BITS);
    bus[i].setWaitForConversion(false);   // we never block on a conversion
    return true;
}

static void pollRediscovery()
{
    static uint32_t lastMs = 0;
    if (millis() - lastMs < REDISCOVER_PERIOD_MS) return;
    lastMs = millis();

    for (uint8_t i = 0; i < SENSOR_COUNT; i++) {
        if (!sensor[i].present) discoverBus(i);
    }
}

static void pushHistory()
{
    for (uint8_t i = 0; i < SENSOR_COUNT; i++) {
        history[i][histHead] = sensor[i].present
                                 ? (int16_t)lroundf(sensor[i].tempC * 100.0f)
                                 : HISTORY_INVALID;
    }
    histHead = (uint16_t)((histHead + 1) % HISTORY_LEN);
    if (histFilled < HISTORY_LEN) histFilled++;
}

// One line per sample on the serial port. During bench bring-up this is the
// only window into the box: no display wired, and WiFi possibly not configured.
static void reportSerial()
{
#if SERIAL_TELEMETRY
    Serial.print(F("[temp]"));
    for (uint8_t i = 0; i < SENSOR_COUNT; i++) {
        Serial.printf("  S%u ", i + 1);
        if (sensor[i].present) Serial.printf("%6.2f C", sensor[i].tempC);
        else                   Serial.print(F("  --.-- ?"));
        Serial.print(sensor[i].displayOn ? F(" [on] ") : F(" [off]"));
    }
    Serial.println();
#endif
}

static void pollSensors()
{
    const uint32_t now = millis();

    switch (sampleState) {
    case SAMPLE_IDLE:
        if (now - samplePeriodMs >= SAMPLE_PERIOD_MS) {
            samplePeriodMs = now;
            convStartMs    = now;
            for (uint8_t i = 0; i < SENSOR_COUNT; i++) {
                bus[i].requestTemperatures();   // returns immediately
            }
            sampleState = SAMPLE_CONVERTING;
        }
        break;

    case SAMPLE_CONVERTING:
        if (now - convStartMs >= CONVERSION_WAIT_MS) {
            for (uint8_t i = 0; i < SENSOR_COUNT; i++) {
                const float t = bus[i].getTempCByIndex(0);

                // A DS18B20 whose scratchpad has never been converted reads
                // exactly 85.00 C -- its power-on reset value. Treat that as
                // "not ready yet" on the first read after a probe appears,
                // rather than reporting a bogus 85 C.
                const bool powerOnArtifact = (!sensor[i].present && t == 85.0f);
                const bool ok = !isnan(t) && t > -100.0f && !powerOnArtifact;

                sensor[i].present = ok;
                sensor[i].tempC   = ok ? t : NAN;
            }
            pushHistory();
            renderDisplay();
            reportSerial();
            sampleState = SAMPLE_IDLE;
        }
        break;
    }
}

// -----------------------------------------------------------------------------
// Buttons
// -----------------------------------------------------------------------------
// Req 4a: the display must reflect a press within 20 ms. We therefore repaint
// straight from the debounce edge instead of waiting for the next sample tick.
static void pollButtons()
{
    const uint32_t now = millis();

    for (uint8_t i = 0; i < SENSOR_COUNT; i++) {
        const bool raw = (digitalRead(buttonPins[i]) == LOW);   // pull-up: LOW == pressed

        if (raw != button[i].lastRaw) {
            button[i].lastRaw      = raw;
            button[i].lastChangeMs = now;
        } else if (raw != button[i].stablePressed &&
                   (now - button[i].lastChangeMs) >= DEBOUNCE_MS) {
            button[i].stablePressed = raw;

            if (raw) {   // act on the press edge, not the release
                const uint32_t t0 = micros();
                sensor[i].displayOn = !sensor[i].displayOn;
                renderDisplay();
                const uint32_t dt = micros() - t0;
                if (dt > maxButtonLatencyUs) maxButtonLatencyUs = dt;
            }
        }
    }
}

// -----------------------------------------------------------------------------
// HTTP API
// -----------------------------------------------------------------------------
static void sendJson(int code, const String &body)
{
    // Permissive CORS so we can poke the box straight from a browser tab while
    // debugging. The PC app itself polls server-side and does not need this.
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.sendHeader("Cache-Control", "no-store");
    server.send(code, "application/json", body);
}

static void handleState()
{
    JsonDocument doc;
    doc["fw"]        = FIRMWARE_VERSION;
    doc["uptime_ms"] = millis();

    JsonArray arr = doc["sensors"].to<JsonArray>();
    for (uint8_t i = 0; i < SENSOR_COUNT; i++) {
        JsonObject o    = arr.add<JsonObject>();
        o["id"]         = i + 1;
        o["present"]    = sensor[i].present;
        o["display_on"] = sensor[i].displayOn;
        if (sensor[i].present) {
            o["temp_c"] = lroundf(sensor[i].tempC * 100.0f) / 100.0;
        } else {
            o["temp_c"] = (const char *)nullptr;   // serialises as JSON null
        }
    }

    String out;
    serializeJson(doc, out);
    sendJson(200, out);
}

// Built by hand rather than with ArduinoJson: this is the one large response
// (up to 600 values) and a flat numeric array is trivial to emit directly,
// with completely predictable memory use.
static void handleHistory()
{
    String out;
    out.reserve(5120);
    out += F("{\"period_ms\":");
    out += SAMPLE_PERIOD_MS;
    out += F(",\"len\":");
    out += histFilled;
    out += F(",\"sensors\":[");

    for (uint8_t i = 0; i < SENSOR_COUNT; i++) {
        if (i) out += ',';
        out += F("{\"id\":");
        out += (i + 1);
        out += F(",\"samples_c100\":[");

        // Oldest sample first. When the buffer is full the oldest sits at histHead.
        for (uint16_t k = 0; k < histFilled; k++) {
            const uint16_t idx =
                (uint16_t)((histHead + HISTORY_LEN - histFilled + k) % HISTORY_LEN);
            if (k) out += ',';
            const int16_t v = history[i][idx];
            if (v == HISTORY_INVALID) out += F("null");
            else                      out += v;
        }
        out += F("]}");
    }
    out += F("]}");

    sendJson(200, out);
}

// Req 5b: let the PC "press" a button. Responds immediately; the display is
// repainted synchronously before we reply, so the round trip is the only delay.
static void handleButton()
{
    const int    id = server.arg("sensor").toInt();
    const String st = server.arg("state");

    if (id < 1 || id > (int)SENSOR_COUNT) {
        sendJson(400, F("{\"error\":\"sensor must be 1 or 2\"}"));
        return;
    }
    const uint8_t i = (uint8_t)(id - 1);

    if      (st == "on")     sensor[i].displayOn = true;
    else if (st == "off")    sensor[i].displayOn = false;
    else if (st == "toggle") sensor[i].displayOn = !sensor[i].displayOn;
    else {
        sendJson(400, F("{\"error\":\"state must be on, off or toggle\"}"));
        return;
    }

    renderDisplay();

    String out = F("{\"id\":");
    out += id;
    out += F(",\"display_on\":");
    out += (sensor[i].displayOn ? F("true") : F("false"));
    out += F("}");
    sendJson(200, out);
}

static void handleInfo()
{
    JsonDocument doc;
    doc["fw"]          = FIRMWARE_VERSION;
    doc["ip"]          = WiFi.localIP().toString();
    doc["mac"]         = WiFi.macAddress();
    doc["rssi_dbm"]    = WiFi.RSSI();
    doc["uptime_ms"]   = millis();
    doc["free_heap"]   = ESP.getFreeHeap();
    doc["history_len"] = histFilled;
    doc["i2c_hz"]      = I2C_CLOCK_HZ;
    // Measured worst cases since boot -- quote these in the lab report.
    doc["max_render_us"]         = maxRenderUs;
    doc["max_button_latency_us"] = maxButtonLatencyUs;

    String out;
    serializeJson(doc, out);
    sendJson(200, out);
}

static void handleRoot()
{
    server.send(200, "text/plain",
                F("ECE:4880 Lab 1 third box\n"
                  "GET  /api/state\n"
                  "GET  /api/history\n"
                  "GET  /api/info\n"
                  "POST /api/button?sensor=1&state=toggle\n"));
}

// -----------------------------------------------------------------------------
// WiFi
// -----------------------------------------------------------------------------
static void pollWiFi()
{
    static uint32_t lastTryMs    = 0;
    static bool     wasConnected = false;

    if (WiFi.status() == WL_CONNECTED) {
        if (!wasConnected) {
            wasConnected = true;
            Serial.printf("[wifi] connected, IP %s\n", WiFi.localIP().toString().c_str());
            if (MDNS.begin(MDNS_HOSTNAME)) {
                MDNS.addService("http", "tcp", HTTP_PORT);
                Serial.printf("[wifi] mDNS: http://%s.local/\n", MDNS_HOSTNAME);
            }
            renderDisplay();   // show the IP the moment we have one
        }
        return;
    }

    if (wasConnected) {
        wasConnected = false;
        Serial.println(F("[wifi] connection lost"));
        renderDisplay();
    }

    if (millis() - lastTryMs >= WIFI_RETRY_PERIOD_MS) {
        lastTryMs = millis();
        WiFi.disconnect();
        WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    }
}

// -----------------------------------------------------------------------------
// setup / loop
// -----------------------------------------------------------------------------
void setup()
{
    Serial.begin(115200);
    delay(200);
    Serial.printf("\n[boot] ECE:4880 Lab 1 third box, fw %s\n", FIRMWARE_VERSION);

    pinMode(PIN_STATUS_LED, OUTPUT);
    for (uint8_t i = 0; i < SENSOR_COUNT; i++) pinMode(buttonPins[i], INPUT_PULLUP);

    for (uint8_t i = 0; i < SENSOR_COUNT; i++)
        for (uint16_t k = 0; k < HISTORY_LEN; k++) history[i][k] = HISTORY_INVALID;

    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, I2C_CLOCK_HZ);
    if (!oled.begin(SSD1306_SWITCHCAPVCC, OLED_I2C_ADDR)) {
        // Nothing more we can usefully do -- but say so loudly on the serial
        // port so a dead display is not mistaken for dead firmware.
        Serial.println(F("[oled] NOT FOUND -- check wiring and the 0x3C/0x3D address"));
    }
    oled.clearDisplay();
    oled.setTextColor(SSD1306_WHITE);
    oled.setTextSize(1);
    oled.setCursor(0, 0);
    oled.println(F("ECE:4880 Lab 1"));
    oled.println(F("Third box booting"));
    oled.display();

    for (uint8_t i = 0; i < SENSOR_COUNT; i++) {
        const bool found = discoverBus(i);
        Serial.printf("[1wire] sensor %u: %s\n", i + 1, found ? "found" : "absent");
    }

    WiFi.mode(WIFI_STA);
    WiFi.setHostname(MDNS_HOSTNAME);
    // Modem sleep on: roughly halves average current, at the cost of up to one
    // beacon interval (~100 ms) of extra latency. Well inside the 1 s budget of
    // Req 5b, and battery life matters more here. See docs/01-system-design.md.
    WiFi.setSleep(true);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    server.on("/",            HTTP_GET,     handleRoot);
    server.on("/api/state",   HTTP_GET,     handleState);
    server.on("/api/history", HTTP_GET,     handleHistory);
    server.on("/api/info",    HTTP_GET,     handleInfo);
    server.on("/api/button",  HTTP_POST,    handleButton);
    server.on("/api/button",  HTTP_GET,     handleButton);   // convenience for manual testing
    server.on("/api/button",  HTTP_OPTIONS, []() {
        server.sendHeader("Access-Control-Allow-Origin",  "*");
        server.sendHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
        server.send(204);
    });
    server.begin();

    samplePeriodMs = millis();
    renderDisplay();
}

void loop()
{
    // Buttons first, so a press is serviced with the least possible delay.
    pollButtons();

    server.handleClient();
    pollSensors();

    // Again: the 1-Wire scratchpad read inside pollSensors() bit-bangs for a few
    // milliseconds, and a press landing during that window must not be delayed
    // until the next iteration.
    pollButtons();

    pollRediscovery();
    pollWiFi();

    // Heartbeat -- a slow blink means the main loop is still running.
    digitalWrite(PIN_STATUS_LED, (millis() / 500) % 2);
}
