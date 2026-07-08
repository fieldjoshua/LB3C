#!/usr/bin/env python3
"""Arduino Nano USB viability test for the LB3C ARDUINO driver.

Usage:
    python ledctl/test_arduino.py --list
    python ledctl/test_arduino.py --probe [--port /dev/ttyUSB0]
    python ledctl/test_arduino.py --pattern rgb [--port ...] [--count 100]
    python ledctl/test_arduino.py --benchmark [--seconds 5]

Patterns:
    rgb     - fills strip solid red, green, blue, each for 1s
    chase   - single white pixel walks the strip
    rainbow - hue sweep across the strip for --seconds

This script talks directly to the driver, no Flask / Socket.IO stack.
"""

from __future__ import annotations

import argparse
import logging
import math
import sys
import time
from pathlib import Path
from typing import List, Tuple

# Make `core` importable when run as `python ledctl/test_arduino.py`
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.drivers.arduino_serial import (  # noqa: E402
    ArduinoSerialDevice,
    HAS_PYSERIAL,
)


def cmd_list() -> int:
    if not HAS_PYSERIAL:
        print("pyserial not installed. Run: pip install pyserial")
        return 1
    ports = ArduinoSerialDevice.list_serial_ports()
    if not ports:
        print("No serial ports detected.")
        return 1
    print(f"{'DEVICE':<20}  DESCRIPTION")
    for p in ports:
        print(f"{p['device']:<20}  {p['description']}")
    guess = ArduinoSerialDevice.autodetect_port()
    if guess:
        print(f"\nAutodetect best guess: {guess}")
    else:
        print("\nAutodetect could not identify an Arduino-like port.")
    return 0


def _make_device(args: argparse.Namespace) -> ArduinoSerialDevice:
    cfg = {
        "arduino": {
            "port": args.port,
            "baud": args.baud,
            "width": args.width,
            "height": args.height,
            "count": args.count,
            "pixel_order": args.order,
            "layout": args.layout,
            "wait_for_handshake": not args.no_handshake,
            "reset_on_open": not args.no_reset,
        }
    }
    return ArduinoSerialDevice(cfg)


def cmd_probe(args: argparse.Namespace) -> int:
    dev = _make_device(args)
    try:
        dev.open()
    except Exception as e:
        print(f"FAIL: could not open device: {e}")
        return 1
    print(f"OK: opened {dev.port} @ {dev.baud} baud, {dev.count} LEDs")
    # Send an all-black frame as a sanity check.
    try:
        dev.draw_rgb_frame(
            dev.width, dev.height, [(0, 0, 0)] * (dev.width * dev.height)
        )
        print("OK: wrote an all-black frame")
    except Exception as e:
        print(f"FAIL: first frame write failed: {e}")
        dev.close()
        return 1
    dev.close()
    return 0


def _solid_frame(w: int, h: int, rgb: Tuple[int, int, int]) -> List[Tuple[int, int, int]]:
    return [rgb] * (w * h)


def cmd_pattern(args: argparse.Namespace) -> int:
    dev = _make_device(args)
    dev.open()
    w, h = dev.width, dev.height
    n = w * h
    try:
        if args.pattern == "rgb":
            for rgb in ((255, 0, 0), (0, 255, 0), (0, 0, 255)):
                dev.draw_rgb_frame(w, h, _solid_frame(w, h, rgb))
                time.sleep(1.0)
            dev.draw_rgb_frame(w, h, _solid_frame(w, h, (0, 0, 0)))

        elif args.pattern == "chase":
            deadline = time.monotonic() + args.seconds
            idx = 0
            while time.monotonic() < deadline:
                frame = [(0, 0, 0)] * n
                x = idx % w
                y = (idx // w) % h
                frame[y * w + x] = (255, 255, 255)
                dev.draw_rgb_frame(w, h, frame)
                idx += 1
                time.sleep(1.0 / args.fps)
            dev.draw_rgb_frame(w, h, _solid_frame(w, h, (0, 0, 0)))

        elif args.pattern == "rainbow":
            deadline = time.monotonic() + args.seconds
            t0 = time.monotonic()
            while time.monotonic() < deadline:
                t = time.monotonic() - t0
                frame = []
                for i in range(n):
                    hue = (i / max(1, n) + t * 0.25) % 1.0
                    r, g, b = _hsv_to_rgb(hue, 1.0, 1.0)
                    frame.append((r, g, b))
                dev.draw_rgb_frame(w, h, frame)
                time.sleep(1.0 / args.fps)
            dev.draw_rgb_frame(w, h, _solid_frame(w, h, (0, 0, 0)))

        else:
            print(f"unknown pattern: {args.pattern}")
            return 2
    finally:
        dev.close()
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    dev = _make_device(args)
    dev.open()
    w, h = dev.width, dev.height
    frame = _solid_frame(w, h, (8, 8, 8))  # dim so the PSU doesn't hate you
    count = 0
    t0 = time.monotonic()
    deadline = t0 + args.seconds
    try:
        while time.monotonic() < deadline:
            dev.draw_rgb_frame(w, h, frame)
            count += 1
    finally:
        dev.draw_rgb_frame(w, h, _solid_frame(w, h, (0, 0, 0)))
        dev.close()
    elapsed = time.monotonic() - t0
    fps = count / elapsed if elapsed else 0.0
    bytes_per_frame = 6 + dev.count * 3
    kbps = (bytes_per_frame * count) / elapsed / 1024 if elapsed else 0.0
    print(
        f"benchmark: {count} frames in {elapsed:.2f}s -> {fps:.1f} fps, "
        f"~{kbps:.1f} kB/s at {dev.count} LEDs"
    )
    return 0


def _hsv_to_rgb(h: float, s: float, v: float) -> Tuple[int, int, int]:
    i = int(h * 6.0)
    f = h * 6.0 - i
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)
    i %= 6
    if i == 0: r, g, b = v, t, p
    elif i == 1: r, g, b = q, v, p
    elif i == 2: r, g, b = p, v, t
    elif i == 3: r, g, b = p, q, v
    elif i == 4: r, g, b = t, p, v
    else:        r, g, b = v, p, q
    return int(r * 255), int(g * 255), int(b * 255)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true", help="list serial ports and exit")
    ap.add_argument("--probe", action="store_true", help="open device and write one black frame")
    ap.add_argument("--pattern", choices=["rgb", "chase", "rainbow"], help="run a test pattern")
    ap.add_argument("--benchmark", action="store_true", help="measure achievable frame rate")

    ap.add_argument("--port", default=None, help="serial port (default: autodetect)")
    ap.add_argument("--baud", type=int, default=500000)
    ap.add_argument("--count", type=int, default=100)
    ap.add_argument("--width", type=int, default=10)
    ap.add_argument("--height", type=int, default=10)
    ap.add_argument("--order", default="GRB")
    ap.add_argument("--layout", default="serpentine", choices=["serpentine", "linear"])
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--seconds", type=float, default=5.0)
    ap.add_argument("--no-reset", action="store_true", help="don't pulse DTR on open")
    ap.add_argument("--no-handshake", action="store_true", help="don't wait for 'Ada' banner")
    ap.add_argument("-v", "--verbose", action="store_true")

    args = ap.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if args.list:
        return cmd_list()
    if args.probe:
        return cmd_probe(args)
    if args.pattern:
        return cmd_pattern(args)
    if args.benchmark:
        return cmd_benchmark(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
