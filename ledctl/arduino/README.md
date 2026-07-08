# Arduino Nano USB Driver for LB3C

This path lets the LB3C host drive WS2811/WS2812 LEDs through an Arduino Nano
(or Uno / Pro Mini / any ATmega328P-class board) over USB. The Nano runs an
Adalight-compatible sketch; LB3C streams frames via `pyserial`.

## When to use it vs. the Pi GPIO drivers

| Path                       | Pros                                         | Cons                                   |
| -------------------------- | -------------------------------------------- | -------------------------------------- |
| `WS2811_PI` (direct GPIO)  | Higher throughput, no middle MCU             | Requires sudo, Pi-only, GPIO wiring    |
| `ARDUINO` (this)           | Runs on any host (Pi, laptop), no sudo       | Capped by USB-serial bandwidth and RAM |

## Hard limits on a stock Nano (ATmega328P, 2 KB SRAM)

- **Practical max LEDs:** ~500 (LED buffer + serial parser fit comfortably).
- **USB-serial bandwidth at 500 kbaud:** ~50 kB/s, i.e. ~16,600 pixels/sec.
  - 100 LEDs at 60 fps = 18 kB/s  (easy)
  - 300 LEDs at 60 fps = 54 kB/s  (right at the ceiling — drop to 30 fps)
  - 500 LEDs at 30 fps = 45 kB/s  (fine)

If you need more, step up to a board with native USB (Leonardo, Micro) or
use an ESP32 with WLED and point LB3C at it via the `WLED` driver.

## Flashing the sketch

1. Install the [Arduino IDE](https://www.arduino.cc/en/software) (or use
   `arduino-cli`).
2. Install the `FastLED` library (Library Manager > search "FastLED").
3. Open `adalight_ws2811/adalight_ws2811.ino`.
4. At the top of the file, match these to your hardware:
   - `LED_PIN` (default `6`) — data pin to the WS2811 strip.
   - `LED_COUNT` — total LED count, **must equal `arduino.count` in
     `config/device.default.yml`**.
   - `COLOR_ORDER` (default `GRB`) — match `arduino.pixel_order`.
   - `SERIAL_BAUD` (default `500000`) — match `arduino.baud`.
5. Board: "Arduino Nano", Processor: usually "ATmega328P (Old Bootloader)"
   for cheap clones, "ATmega328P" for genuine.
6. Upload.

## Wiring

```
Arduino Nano          WS2811 strip
    D6       --->     DIN
    GND      --->     GND  (also tie to strip PSU GND)
    -               +5V from external PSU  ---> VCC of strip
```

**Do not** power a long WS2811 run from the Nano's 5V pin — it can only
supply a few LEDs. Use an external 5V supply sized for the strip; share
ground with the Nano.

A 330–470 Ω resistor inline on the data pin and a 1000 µF cap across the
strip's power rails is the standard recommendation.

## Running LB3C with the Arduino

In `config/device.default.yml`:

```yaml
device: ARDUINO

arduino:
  port: null              # or "/dev/ttyUSB0" / "COM5" to pin it
  baud: 500000
  width: 10
  height: 10
  count: 100
  pixel_order: GRB
  layout: serpentine      # zigzag grid wiring
```

Then:

```bash
python ledctl/app.py
```

## Quick viability check (no UI)

```bash
python ledctl/test_arduino.py --list          # show serial ports
python ledctl/test_arduino.py --probe         # open + handshake, no frames
python ledctl/test_arduino.py --pattern rgb   # send a color sweep
```
