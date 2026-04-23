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

#include <FastLED.h>

// ---- User config ---------------------------------------------------------
#define LED_PIN      6          // Data pin to the WS2811 strip
#define LED_COUNT    100        // MUST match arduino.count in device.default.yml
#define COLOR_ORDER  GRB        // Must match arduino.pixel_order
#define CHIPSET      WS2811     // WS2811 | WS2812 | WS2812B
#define SERIAL_BAUD  500000     // Must match arduino.baud
// -------------------------------------------------------------------------

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

static inline void resetParser() {
  state = WAIT_MAGIC_0;
  pixels_remaining = 0;
  pixel_byte_idx = 0;
  led_index = 0;
}

void setup() {
  FastLED.addLeds<CHIPSET, LED_PIN, COLOR_ORDER>(leds, LED_COUNT);
  FastLED.clear(true);

  Serial.begin(SERIAL_BAUD);
  // Announce readiness. The host waits for "Ada\n".
  Serial.print(F("Ada\n"));
}

void loop() {
  while (Serial.available()) {
    int c = Serial.read();
    if (c < 0) break;
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
        if (state == WAIT_MAGIC_0) FastLED.show();
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
            state = WAIT_MAGIC_0;
          }
        }
        break;
    }
  }
}
