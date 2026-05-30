#!/usr/bin/env python3
"""Standalone animation player for the Arduino-USB LED path.

Plays any procedural animation from core.automations directly to the
Nano via core.drivers.arduino_serial. No Flask, no Socket.IO, no
device.yml, no gamma layer. Renders each animation at the strip's
native resolution and sends it straight to the LEDs - what the
animation draws is exactly what you see.

Usage:
    python3 ledctl/play_animation.py --list
    python3 ledctl/play_animation.py metaballs
    python3 ledctl/play_animation.py tunnel --brightness 0.6
    python3 ledctl/play_animation.py aurora --speed 1.5 --rotate 90
    python3 ledctl/play_animation.py metaballs --duration 30   # stop after 30s

Ctrl-C cleanly clears the strip and disconnects.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from pathlib import Path
from typing import List, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.automations import AUTOMATION_REGISTRY  # noqa: E402
from core.drivers.arduino_serial import ArduinoSerialDevice  # noqa: E402


def list_animations() -> None:
    print("Available animations:")
    for name, cls in sorted(AUTOMATION_REGISTRY.items()):
        doc = (cls.__doc__ or "").strip().splitlines()
        summary = doc[0] if doc else ""
        print(f"  {name:18s}  {summary}")


def frame_to_rgb_list(
    frame: np.ndarray, brightness: float
) -> List[Tuple[int, int, int]]:
    if frame.dtype != np.uint8:
        frame = np.clip(frame, 0, 255).astype(np.uint8)
    if brightness < 1.0:
        frame = (frame.astype(np.float32) * brightness).clip(0, 255).astype(np.uint8)
    flat = frame.reshape(-1, 3)
    return [(int(p[0]), int(p[1]), int(p[2])) for p in flat]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("name", nargs="?", help="animation name (omit with --list)")
    ap.add_argument("--list", action="store_true", help="list available animations")

    # Geometry.
    ap.add_argument("--width", type=int, default=10)
    ap.add_argument("--height", type=int, default=10)
    ap.add_argument("--count", type=int, default=None,
                    help="LED count (default = width*height)")
    ap.add_argument("--fps", type=float, default=30.0)

    # Look / timing.
    ap.add_argument("--brightness", type=float, default=1.0,
                    help="0.0 to 1.0 multiplier applied to every pixel")
    ap.add_argument("--speed", type=float, default=1.0, metavar="X",
                    help="animation time multiplier. 1.0=normal, 2.0=2x "
                         "fast, 0.5=half speed.")
    ap.add_argument("--rotate", type=int, default=0, choices=[0, 90, 180, 270],
                    help="rotate the frame this many degrees clockwise to "
                         "match the strip's physical orientation.")
    ap.add_argument("--duration", type=float, default=None,
                    help="auto-stop after N seconds (default: run until Ctrl-C)")

    # Hardware.
    ap.add_argument("--port", default=None, help="serial port (default: autodetect)")
    ap.add_argument("--baud", type=int, default=500000)
    ap.add_argument("--order", default="GRB", help="strip color order")
    ap.add_argument("--layout", default="serpentine",
                    choices=["serpentine", "linear"])

    ap.add_argument("-v", "--verbose", action="store_true")

    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if args.list:
        list_animations()
        return 0

    if not args.name:
        ap.print_help()
        return 0

    if args.name not in AUTOMATION_REGISTRY:
        print(f"unknown animation: {args.name!r}", file=sys.stderr)
        print("run with --list to see options", file=sys.stderr)
        return 2

    cls = AUTOMATION_REGISTRY[args.name]
    anim = cls(args.width, args.height, fps=args.fps)

    count = args.count if args.count is not None else args.width * args.height
    dev = ArduinoSerialDevice({
        "arduino": {
            "port": args.port,
            "baud": args.baud,
            "width": args.width,
            "height": args.height,
            "count": count,
            "pixel_order": args.order,
            "layout": args.layout,
        }
    })

    print(f"playing {args.name!r} on {args.width}x{args.height} "
          f"({count} LEDs) at {args.fps:g} fps. Ctrl-C to stop.")

    dev.open()

    stop_requested = {"value": False}
    def on_signal(signum, frame):
        stop_requested["value"] = True
    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    period = 1.0 / max(args.fps, 0.1)
    t0 = time.monotonic()
    next_tick = t0
    frames_sent = 0
    last_report = t0
    try:
        while not stop_requested["value"]:
            now = time.monotonic()
            if args.duration is not None and (now - t0) >= args.duration:
                break

            anim_t = (now - t0) * args.speed
            np_frame = anim.generate_frame(anim_t)

            if args.rotate:
                # numpy rot90 is counter-clockwise; negate k for clockwise.
                k_cw = {90: -1, 180: -2, 270: -3}[args.rotate]
                np_frame = np.rot90(np_frame, k=k_cw).copy()

            rgb_data = frame_to_rgb_list(np_frame, args.brightness)
            # After a 90/270 rotation the raster is (W, H) not (H, W).
            if args.rotate in (90, 270):
                dev.draw_rgb_frame(args.height, args.width, rgb_data)
            else:
                dev.draw_rgb_frame(args.width, args.height, rgb_data)
            frames_sent += 1

            if now - last_report >= 5.0:
                fps_actual = frames_sent / (now - t0)
                print(f"  ... {frames_sent} frames, {fps_actual:.1f} fps")
                last_report = now

            next_tick += period
            sleep_for = next_tick - time.monotonic()
            if sleep_for > 0:
                time.sleep(sleep_for)
            else:
                # Behind schedule; reset to avoid runaway catch-up.
                next_tick = time.monotonic()
    finally:
        try:
            black = [(0, 0, 0)] * (args.width * args.height)
            dev.draw_rgb_frame(args.width, args.height, black)
        except Exception:
            pass
        dev.close()
        elapsed = time.monotonic() - t0
        if elapsed > 0:
            print(f"stopped: {frames_sent} frames in {elapsed:.1f}s "
                  f"({frames_sent / elapsed:.1f} fps)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
