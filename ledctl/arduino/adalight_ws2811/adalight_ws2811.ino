// Adalight-compatible WS2811/WS2812 sketch for Arduino Nano / Uno.
//
// Receives RGB frames over USB serial from the LB3C host and drives
// WS2811/WS2812 LEDs via FastLED.
//
// Wire protocol (Adalight):
//     'A' 'd' 'a'  hi  lo  chk   R0 G0 B0  R1 G1 B1  ...
//   where:
//     hi  = (LED_COUNT - 1) >> 8
//     lo  = (LED_COUNT - 1) & 0xFF
//     chk = hi ^ lo ^ 0x55
//
// Install FastLED via the Arduino Library Manager before compiling.
//
// Nano (ATmega328P) RAM budget: ~2 KB. Each LED costs 3 bytes + overhead,
// so keep LED_COUNT <= ~500.

// Let the UART interrupt fire while FastLED is driving the strip. Without
// this, show() disables interrupts for ~3ms; at 500k baud up to 150 bytes
// can arrive in that window but the 64-byte serial buffer overflows, so
// bytes are LOST and the frame stream desyncs (random full-panel flashes).
// FastLED detects an interrupt that disturbed bit timing and retries the
// frame, so the cost is an occasional repeated frame instead of corruption.
#define FASTLED_ALLOW_INTERRUPTS 1

#include <FastLED.h>

// ---- User config ---------------------------------------------------------
#define LED_PIN      6          // Data pin to the WS2811 strip
#define LED_COUNT    100        // MUST match arduino.count in device.default.yml
#define COLOR_ORDER  GRB        // Must match arduino.pixel_order
#define CHIPSET      WS2811     // WS2811 | WS2812 | WS2812B
#define SERIAL_BAUD  500000     // Must match arduino.baud
#define DIAG_PIN     LED_BUILTIN // Onboard LED for bring-up diagnostics
// -------------------------------------------------------------------------

// Bring-up aid: the onboard LED pulses ~1 Hz when idle so you know the
// sketch is alive, and toggles on every completed frame so you can
// confirm USB->Nano traffic even with NO WS2811 strip connected.

CRGB leds[LED_COUNT];

// Magic header bytes.
static const uint8_t kMagic[3] = { 'A', 'd', 'a' };

enum State {
  WAIT_MAGIC_0,
  WAIT_MAGIC_1,
  WAIT_MAGIC_2,
  READ_HI,
  READ_LO,
  READ_CHK,
  READ_PIXELS,
};

static State state = WAIT_MAGIC_0;
static uint16_t pixels_remaining = 0;
static uint16_t pixel_byte_idx = 0;  // 0, 1, 2 -> R, G, B within a pixel
static uint16_t led_index = 0;
static uint8_t  cur_r = 0, cur_g = 0;
static uint8_t  hi = 0, lo = 0;

static uint32_t last_byte_ms = 0;
static uint32_t last_frame_ms = 0;
static uint32_t last_heartbeat_ms = 0;
static bool     diag_state = false;

static inline void resetParser() {
  state = WAIT_MAGIC_0;
  pixels_remaining = 0;
  pixel_byte_idx = 0;
  led_index = 0;
}

void setup() {
  pinMode(DIAG_PIN, OUTPUT);
  digitalWrite(DIAG_PIN, LOW);

  FastLED.addLeds<CHIPSET, LED_PIN, COLOR_ORDER>(leds, LED_COUNT);
  FastLED.clear(true);

  Serial.begin(SERIAL_BAUD);
  // Announce readiness. The host waits for "Ada\n".
  Serial.print(F("Ada\n"));
}

static inline void onFrameComplete() {
  diag_state = !diag_state;
  digitalWrite(DIAG_PIN, diag_state ? HIGH : LOW);
  last_frame_ms = millis();
}

static inline void tickHeartbeat() {
  // If no frames have arrived recently, pulse the diag LED at ~1 Hz so
  // you can tell the sketch is running even before the host connects.
  uint32_t now = millis();
  if (now - last_frame_ms < 500) return;  // actively receiving
  if (now - last_heartbeat_ms >= 1000) {
    last_heartbeat_ms = now;
    diag_state = !diag_state;
    digitalWrite(DIAG_PIN, diag_state ? HIGH : LOW);
  }
}

void loop() {
  tickHeartbeat();

  // Parser watchdog: if we are part-way through a frame and the stream
  // stalls, abandon it and wait for a fresh magic word. Without this a
  // single lost byte leaves the parser permanently misaligned - it eats
  // the next frame's bytes as this frame's pixels and paints garbage.
  if (state != WAIT_MAGIC_0 && (millis() - last_byte_ms) > 50) {
    resetParser();
  }

  while (Serial.available()) {
    int c = Serial.read();
    if (c < 0) break;
    last_byte_ms = millis();
    uint8_t b = (uint8_t) c;

    switch (state) {
      case WAIT_MAGIC_0:
        if (b == kMagic[0]) state = WAIT_MAGIC_1;
        break;
      case WAIT_MAGIC_1:
        state = (b == kMagic[1]) ? WAIT_MAGIC_2 : WAIT_MAGIC_0;
        break;
      case WAIT_MAGIC_2:
        state = (b == kMagic[2]) ? READ_HI : WAIT_MAGIC_0;
        break;
      case READ_HI:
        hi = b;
        state = READ_LO;
        break;
      case READ_LO:
        lo = b;
        state = READ_CHK;
        break;
      case READ_CHK: {
        uint8_t expected = hi ^ lo ^ 0x55;
        if (b != expected) {
          // Bad checksum: resync on next magic word.
          resetParser();
          break;
        }
        uint16_t count = ((uint16_t) hi << 8) | lo;
        count += 1;  // header encodes count-1
        if (count > LED_COUNT) count = LED_COUNT;
        pixels_remaining = count;
        pixel_byte_idx = 0;
        led_index = 0;
        state = (pixels_remaining > 0) ? READ_PIXELS : WAIT_MAGIC_0;
        if (state == WAIT_MAGIC_0) { FastLED.show(); onFrameComplete(); }
        break;
      }
      case READ_PIXELS:
        if (pixel_byte_idx == 0) {
          cur_r = b;
          pixel_byte_idx = 1;
        } else if (pixel_byte_idx == 1) {
          cur_g = b;
          pixel_byte_idx = 2;
        } else {
          if (led_index < LED_COUNT) {
            // CRGB is always R,G,B in memory; FastLED handles COLOR_ORDER
            // on output.
            leds[led_index] = CRGB(cur_r, cur_g, b);
          }
          led_index++;
          pixel_byte_idx = 0;
          pixels_remaining--;
          if (pixels_remaining == 0) {
            FastLED.show();
            onFrameComplete();
            state = WAIT_MAGIC_0;
          }
        }
        break;
    }
  }
}
