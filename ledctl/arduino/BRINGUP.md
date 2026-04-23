# Arduino Nano + WS2811 Bring-Up Plan

Goal: prove every link in the chain works **before** you wire 100 LEDs.
The sketch uses the Nano's onboard LED (D13) for diagnostics, so the first
four stages need nothing but the Nano and a USB cable.

```
[host / LB3C] --USB-- [Nano + sketch] --data pin-- [WS2811 strip]
  stage 2,3,4                              stage 5,6
```

---

## Stage 0 — Flash the sketch (no strip)

1. Install Arduino IDE + FastLED library.
2. Open `arduino/adalight_ws2811/adalight_ws2811.ino`.
3. Confirm at the top of the file:
   - `LED_COUNT 100`
   - `LED_PIN 6`
   - `COLOR_ORDER GRB`     *(you can change later if colors look swapped)*
   - `SERIAL_BAUD 500000`
4. Board: **Arduino Nano**. Processor: **ATmega328P (Old Bootloader)**
   for cheap clones, **ATmega328P** for genuine. Port: the Nano's.
5. Upload.

**Expected after upload:** onboard LED (labeled `L` or `D13`) blinks
slowly (~1 Hz). That's the sketch's heartbeat — proves it's running.

---

## Stage 1 — Host sees the serial port

```bash
source venv/bin/activate   # if using venv
pip install pyserial
python ledctl/test_arduino.py --list
```

**Expected:** the Nano appears (e.g. `/dev/ttyUSB0` on Pi/Linux,
`COM5` on Windows) and "Autodetect best guess" points at it.
If not, your OS is missing the CH340/CP210x driver.

---

## Stage 2 — Host opens the link and handshakes

```bash
python ledctl/test_arduino.py --probe
```

**Expected output:**
```
OK: opened /dev/ttyUSB0 @ 500000 baud, 100 LEDs
OK: wrote an all-black frame
```

**Expected on Nano:** heartbeat pauses, D13 does one toggle (the black
frame), then heartbeat resumes.

Failure mode: `No Adalight handshake banner seen` is a warning, not
fatal. But if `FAIL: first frame write failed` shows up, the serial
link is broken — check cable/baud/port.

---

## Stage 3 — Continuous frames (still no strip)

```bash
python ledctl/test_arduino.py --pattern chase --fps 2 --seconds 10
```

**Expected on Nano:** D13 toggles twice per second for 10 seconds. If
it does, the full protocol is working end to end. You can now wire LEDs
with confidence.

---

## Stage 4 — Benchmark (optional, still no strip)

```bash
python ledctl/test_arduino.py --benchmark --seconds 5
```

**Expected:** ~50–100 fps at 100 LEDs. D13 will look solid (too fast to
see toggling). This is your real throughput ceiling.

---

## Stage 5 — Wire ONE LED to verify color order

Before building the 100-LED run, confirm the color order on one pixel.

```
Nano D6 ---- 330Ω ---- DIN  of first WS2811
Nano GND --------------- GND of strip  (and GND of PSU)
5V PSU +5V -------------- VCC of strip  (NOT from Nano 5V pin)
```

Then:

```bash
python ledctl/test_arduino.py --pattern rgb --count 1 --width 1 --height 1
```

**Expected:** pixel goes red for 1s, green for 1s, blue for 1s, off.
If colors are swapped:

| You see           | Set `COLOR_ORDER` / `--order` to |
| ----------------- | -------------------------------- |
| G, R, B           | `RGB`                            |
| B, G, R           | `BRG`                            |
| R, B, G           | `RBG`                            |
| G, B, R           | `BGR`                            |
| B, R, G           | `GBR`                            |

Update the sketch **and** `arduino.pixel_order` in
`config/device.default.yml` to match. Real WS2811 chips are commonly
`BRG`; WS2812 is almost always `GRB` (the default).

---

## Stage 6 — Wire the full 100 and run

Power notes for 100 WS2811:
- At full white, 100 LEDs ≈ 6 A @ 5 V (60 mA/LED). Use a PSU rated
  ≥ 5 V / 10 A with good headroom.
- Inject +5V and GND at both ends of the strip for runs > ~30 LEDs.
- 1000 µF cap across the first LED's 5V/GND. 330 Ω inline on DIN.
- **Never** power the strip from the Nano's 5V pin.

Then:

```bash
python ledctl/test_arduino.py --pattern rainbow --seconds 15 --fps 30
```

If that looks right, you're done with bring-up. Launch the full app:

```bash
# Edit config/device.default.yml:  device: ARDUINO
python ledctl/app.py
```

---

## Cheat sheet: what the onboard LED means

| Onboard LED state           | Meaning                                       |
| --------------------------- | --------------------------------------------- |
| Slow blink, ~1 Hz           | Sketch running, no host connected             |
| Toggles on each host frame  | USB link working, frames arriving             |
| Always off                  | Sketch not running — re-check upload / power  |
| Always on, no toggling      | Host stuck mid-frame; check baud match        |
