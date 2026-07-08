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
import inspect
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


# --- Dithering -------------------------------------------------------------
# We use 1st-order sigma-delta (temporal error feedback) rather than a spatial
# ordered/Bayer pattern. Each pixel carries its quantization remainder -
# positive OR negative ("negative light") - into the next frame, so a value of
# 10.4 emits 10,10,11,10,10,11... averaging exactly 10.4 with no fixed spatial
# texture. There's no grid pattern to translate, so nothing "shimmers"; at
# 60-120fps the per-pixel toggle is above flicker fusion and disappears into
# smooth color. Pairs with --fps: higher fps = smoother / more invisible.


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
    ap.add_argument("--fps", type=float, default=60.0,
                    help="frame rate. Higher = smoother sigma-delta dithering "
                         "(60 default; try 90-120 for ambient).")

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
    ap.add_argument("--palette", default=None,
                    help="recolor noise animations with a named palette: "
                         "cosmic, lava, aurora, colorfield, sky, caustic, ink, "
                         "smoke, fire, forest, sunset, ice, mono.")
    ap.add_argument("--warp", type=float, default=None, metavar="X",
                    help="domain-warp intensity for warp-based noise animations "
                         "(caustics/ink/smoke/marble/lava/wood). 1.0 = default, "
                         "higher = more tendrils/distortion.")
    ap.add_argument("--param", action="append", default=[], metavar="K=V",
                    help="set any animation constructor parameter, e.g. "
                         "--param feather=0.35 --param twist=4. Repeatable. "
                         "Only applied if the animation accepts that param.")

    # Hardware.
    ap.add_argument("--port", default=None, help="serial port (default: autodetect)")
    ap.add_argument("--baud", type=int, default=500000)
    ap.add_argument("--order", default="GRB", help="strip color order")
    ap.add_argument("--layout", default="serpentine",
                    choices=["serpentine", "linear"])

    ap.add_argument("--no-dither", action="store_true",
                    help="disable sigma-delta dithering. Dithering is on by "
                         "default and pulls smooth gradients out of the 8-bit "
                         "panel for float-output animations (ambient_*).")
    ap.add_argument("--dither-strength", type=float, default=1.0, metavar="X",
                    help="0..1, attenuates the sigma-delta error feedback. "
                         "1.0 (default) = full dither, exact average, visible "
                         "per-pixel toggling. 0.5 = half-strength, calmer "
                         "but slight bias. 0.0 = no dither (banding shows). "
                         "Try 0.4-0.6 if dithering is too 'shimmery'.")
    ap.add_argument("--dither-floor", type=float, default=256.0, metavar="N",
                    help="channels dimmer than N (0-255 scale) use steady "
                         "hysteresis rounding; brighter ones get sigma-delta "
                         "temporal dithering. Default 256 = hysteresis "
                         "EVERYWHERE (no temporal modulation at all - dim "
                         "toggles violate Weber's law, bright toggles sit in "
                         "the eye's peak flicker-sensitivity band). Set e.g. "
                         "30 to re-enable dithering of bright regions, 0 for "
                         "classic full sigma-delta.")

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
    # Pass --palette / --warp / --param only to animations whose __init__
    # accepts them, so flags are harmless on animations that don't support them.
    extra = {}
    sig_params = inspect.signature(cls.__init__).parameters
    if args.palette is not None and "palette" in sig_params:
        extra["palette"] = args.palette
    if args.warp is not None and "warp" in sig_params:
        extra["warp"] = args.warp

    def _coerce(v):
        for caster in (int, float):
            try:
                return caster(v)
            except ValueError:
                pass
        if v.lower() in ("true", "false"):
            return v.lower() == "true"
        return v

    for item in args.param:
        if "=" not in item:
            print(f"ignoring malformed --param {item!r} (need K=V)", file=sys.stderr)
            continue
        k, v = item.split("=", 1)
        k = k.strip()
        if k in sig_params:
            extra[k] = _coerce(v.strip())
        else:
            print(f"note: {args.name!r} has no param {k!r}, ignoring", file=sys.stderr)

    anim = cls(args.width, args.height, fps=args.fps, **extra)

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

    # Arduino pipeline budget: a frame must be RECEIVED (10 wire bits per
    # byte at the configured baud) and then SHOWN (WS2811 = 30us per LED,
    # during which FastLED disables interrupts, so overlapping bytes are
    # lost). If the frame period is shorter than receive+show, the Nano
    # silently tears/drops frames - and dropped frames also break the
    # sigma-delta dither's temporal averaging. Warn with the exact ceiling.
    frame_bytes = 6 + count * 3
    send_s = frame_bytes * 10.0 / args.baud
    show_s = count * 30e-6
    max_clean_fps = 1.0 / (send_s + show_s)
    if args.fps > max_clean_fps:
        print(f"  WARNING: {args.fps:g} fps exceeds the serial+show budget "
              f"({send_s*1e3:.1f}ms + {show_s*1e3:.1f}ms per frame). The "
              f"Arduino will tear/drop frames and dithering accuracy "
              f"degrades. Max clean rate for this setup: "
              f"{max_clean_fps:.0f} fps.")

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
    sd_err = None  # sigma-delta per-pixel error accumulator (lazy init)
    try:
        while not stop_requested["value"]:
            now = time.monotonic()
            if args.duration is not None and (now - t0) >= args.duration:
                break

            anim_t = (now - t0) * args.speed
            np_frame = anim.generate_frame(anim_t)

            # Float-output animations (ambient_*) carry sub-8-bit color.
            # Apply brightness in float, then sigma-delta dither to uint8:
            # add the carried error, round, and carry the new remainder
            # (positive or negative) into the next frame. No spatial pattern,
            # so no shimmer; just per-pixel temporal averaging.
            applied_brightness = args.brightness
            if np.issubdtype(np_frame.dtype, np.floating):
                f = np_frame * args.brightness if args.brightness != 1.0 else np_frame
                if not args.no_dither:
                    if sd_err is None or sd_err.shape != f.shape:
                        sd_err = np.zeros_like(f, dtype=np.float32)
                        q_prev = np.round(f).astype(np.float32)
                    target = f + sd_err
                    rounded = np.round(target)
                    err = target - rounded
                    if args.dither_floor > 0:
                        # Dim channels: at low luminance a +/-1 toggle is a
                        # huge RELATIVE brightness jump (Weber's law), so no
                        # dithering there. But plain rounding flickers too:
                        # an input hovering at a .5 boundary hard-toggles on
                        # every tiny drift. So dim channels use a HYSTERESIS
                        # rounder: hold the current level until the input
                        # moves >0.75 of a level away. Boundary wobble = zero
                        # toggles; real ramps step exactly once per level.
                        dim = f < float(args.dither_floor)
                        hold = np.abs(f - q_prev) <= 0.75
                        hys = np.where(hold, q_prev, np.round(f))
                        rounded = np.where(dim, hys, rounded)
                        err = np.where(dim, 0.0, err)
                    q_prev = rounded.astype(np.float32)
                    # Attenuate error feedback so dither can be tuned down.
                    sd_err = (err * float(args.dither_strength)).astype(np.float32)
                    np_frame = np.clip(rounded, 0, 255).astype(np.uint8)
                else:
                    np_frame = np.clip(f, 0, 255).astype(np.uint8)
                applied_brightness = 1.0  # already applied above

            if args.rotate:
                # numpy rot90 is counter-clockwise; negate k for clockwise.
                k_cw = {90: -1, 180: -2, 270: -3}[args.rotate]
                np_frame = np.rot90(np_frame, k=k_cw).copy()

            rgb_data = frame_to_rgb_list(np_frame, applied_brightness)
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
