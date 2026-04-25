#!/usr/bin/env python3
"""Standalone animation player for the Arduino-USB LED path.

Plays any procedural animation from core.automations directly to the
Nano via core.drivers.arduino_serial. No Flask, no Socket.IO, no
device.yml, no gamma correction layer in the way.

Usage:
    python3 ledctl/play_animation.py --list
    python3 ledctl/play_animation.py metaballs
    python3 ledctl/play_animation.py tunnel --fps 30 --brightness 0.6
    python3 ledctl/play_animation.py plasma_flow --width 10 --height 10
    python3 ledctl/play_animation.py aurora --port /dev/cu.usbserial-120
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
        print(f"  {name:14s}  {summary}")


def beat_envelope(t: float, bpm: float, shape: str, floor: float,
                  decay: float, offset_beats: float) -> float:
    """Brightness multiplier in [floor, 1.0] synced to BPM.

    punch  - exponential decay each beat (peak on the beat, fade until next)
    sine   - smooth oscillation, peak on the beat
    square - on for first half of each beat, at floor for second half
    """
    if bpm <= 0:
        return 1.0
    beats = t * (bpm / 60.0) - offset_beats
    phase = beats - np.floor(beats)  # 0..1 within current beat
    if shape == "sine":
        # cosine peaks at phase=0 (the beat)
        v = 0.5 + 0.5 * float(np.cos(2.0 * np.pi * phase))
    elif shape == "square":
        v = 1.0 if phase < 0.5 else 0.0
    else:  # "punch"
        v = float(np.exp(-decay * phase))
    return floor + (1.0 - floor) * v


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
    ap.add_argument("--width", type=int, default=10)
    ap.add_argument("--height", type=int, default=10)
    ap.add_argument("--count", type=int, default=None,
                    help="LED count (default = width*height)")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--brightness", type=float, default=1.0,
                    help="0.0 to 1.0 multiplier applied to every pixel")
    ap.add_argument("--duration", type=float, default=None,
                    help="auto-stop after N seconds (default: run until Ctrl-C)")
    ap.add_argument("--port", default=None, help="serial port (default: autodetect)")
    ap.add_argument("--baud", type=int, default=500000)
    ap.add_argument("--order", default="GRB", help="strip color order")
    ap.add_argument("--layout", default="serpentine",
                    choices=["serpentine", "linear"])
    ap.add_argument("--bpm", type=float, default=None,
                    help="pulse brightness to this tempo (e.g. 120). "
                         "Off if not set. Combine with --beat-floor / "
                         "--beat-decay / --beat-shape to tune the pulse.")
    ap.add_argument("--beat-floor", type=float, default=0.2,
                    help="minimum brightness between beats (0..1, default 0.2)")
    ap.add_argument("--beat-decay", type=float, default=4.0,
                    help="exponential decay rate per beat (higher = punchier, "
                         "default 4.0)")
    ap.add_argument("--beat-shape", default="punch",
                    choices=["punch", "sine", "square"],
                    help="envelope shape: punch=exp decay, sine=smooth, "
                         "square=on/off")
    ap.add_argument("--beat-offset", type=float, default=0.0,
                    help="phase offset in beats (e.g. 0.5 to flip pulse)")
    ap.add_argument("--supersample", type=int, default=1, metavar="N",
                    help="render animation at N*width by N*height internally "
                         "and average down. Smooth gradients on a coarse "
                         "strip. 1=off (default), 4 is a good starting point.")
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
    ss = max(1, int(args.supersample))
    inner_w, inner_h = args.width * ss, args.height * ss
    anim = cls(inner_w, inner_h, fps=args.fps)

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

    beat_msg = (f", pulsing at {args.bpm:g} bpm ({args.beat_shape})"
                if args.bpm else "")
    ss_msg = f", supersample {ss}x ({inner_w}x{inner_h} internal)" if ss > 1 else ""
    print(f"playing {args.name!r} on {args.width}x{args.height} "
          f"({count} LEDs) at {args.fps:g} fps{beat_msg}{ss_msg}. "
          f"Ctrl-C to stop.")

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

            anim_t = now - t0
            np_frame = anim.generate_frame(anim_t)
            if ss > 1:
                # Block-average ss x ss neighborhoods down to (height, width).
                np_frame = (
                    np_frame.astype(np.float32)
                    .reshape(args.height, ss, args.width, ss, 3)
                    .mean(axis=(1, 3))
                    .astype(np.uint8)
                )
            beat_mul = beat_envelope(
                anim_t, args.bpm or 0.0, args.beat_shape,
                args.beat_floor, args.beat_decay, args.beat_offset,
            ) if args.bpm else 1.0
            rgb_data = frame_to_rgb_list(np_frame, args.brightness * beat_mul)
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
                # We're behind schedule; reset to avoid runaway catch-up.
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
