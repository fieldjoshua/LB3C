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
    python3 ledctl/play_animation.py ambient_sweep --rotate 45
    python3 ledctl/play_animation.py metaballs --duration 30   # stop after 30s
    python3 ledctl/play_animation.py aurora ambient_marble --each 300

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
    ap.add_argument("names", nargs="*", metavar="name",
                    help="animation name(s). Give several to cycle through "
                         "them (see --each). Omit with --list.")
    ap.add_argument("--each", type=float, default=300.0, metavar="SECONDS",
                    help="with several names: seconds on each before "
                         "crossfading to the next (default 300)")
    ap.add_argument("--fade", type=float, default=4.0, metavar="SECONDS",
                    help="with several names: crossfade length (default 4)")
    ap.add_argument("--hue-shift", type=float, default=0.0, metavar="DEG",
                    help="with several names: after each full pass through "
                         "the list, turn every colour this many degrees "
                         "around the colour wheel (e.g. 72 = five different "
                         "palettes before it repeats). Brightness of every "
                         "pixel is kept, so contrast is unchanged. The change "
                         "happens gradually during the crossfade back to the "
                         "first animation. Default 0 = off.")
    ap.add_argument("--list", action="store_true", help="list available animations")

    # Geometry.
    ap.add_argument("--device", choices=["arduino", "hub75"], default="arduino",
                    help="output: 'arduino' = Nano over USB (Adalight), "
                         "'hub75' = RGB matrix on a Pi via rpi-rgb-led-matrix "
                         "(run with sudo).")
    ap.add_argument("--width", type=int, default=None,
                    help="render width (default: 10 for arduino, panel size "
                         "for hub75)")
    ap.add_argument("--height", type=int, default=None)
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
    ap.add_argument("--rotate", type=float, default=0.0, metavar="DEG",
                    help="rotate the picture this many degrees clockwise. "
                         "90/180/270 are exact; any other angle (e.g. 45) "
                         "renders a larger canvas and resamples it smoothly, "
                         "which costs extra render time.")
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

    # HUB75 matrix (Adafruit RGB Matrix Bonnet/HAT on a Raspberry Pi).
    ap.add_argument("--panel", default="64x64", metavar="ROWSxCOLS",
                    help="hub75: one panel's size, e.g. 32x64 (default 64x64)")
    ap.add_argument("--no-e", action="store_true",
                    help="hub75: workaround for a 64-row panel whose E "
                         "address jumper is not soldered yet. Without E the "
                         "panel can only address 16-row bands, and each band "
                         "repeats. This renders a thin strip and mirrors it "
                         "so the repeats join seamlessly (a kaleidoscope "
                         "tiling) instead of showing broken copies.")
    ap.add_argument("--chain", type=int, default=1,
                    help="hub75: panels daisy-chained horizontally")
    ap.add_argument("--parallel", type=int, default=1)
    ap.add_argument("--hardware-mapping", default="adafruit-hat",
                    help="hub75: 'adafruit-hat', or 'adafruit-hat-pwm' if the "
                         "GPIO4-GPIO18 quality jumper is soldered")
    ap.add_argument("--gpio-slowdown", type=int, default=2,
                    help="hub75: 2 for a Pi 3 (raise if the panel flickers "
                         "or shows garbage)")
    ap.add_argument("--matrix-brightness", type=int, default=80,
                    help="hub75: panel brightness 1-100 (hardware PWM)")
    ap.add_argument("--pwm-bits", type=int, default=11)
    ap.add_argument("--pwm-lsb-ns", type=int, default=130)
    ap.add_argument("--limit-refresh", type=int, default=0,
                    help="hub75: cap panel refresh Hz (0 = unlimited)")
    ap.add_argument("--balance", action="append", default=[],
                    metavar="START:END:R,G,B",
                    help="per-LED white-balance gains over an LED-index range, "
                         "e.g. --balance 50:100:1.0,0.94,0.82 . Repeatable. "
                         "Use this when a panel built from two strip batches "
                         "shows different hues on grey/mixed colours (they "
                         "match on saturated single-channel colours).")

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

    if args.device == "hub75":
        try:
            p_rows, p_cols = (int(v) for v in args.panel.lower().split("x"))
        except ValueError:
            print(f"--panel must look like 64x64 (got {args.panel!r})",
                  file=sys.stderr)
            return 2
        args.width = args.width or p_cols * args.chain
        args.height = args.height or p_rows * args.parallel
        if args.no_e:
            if args.parallel != 1 or args.rotate % 180 == 90 or p_rows < 8:
                print("--no-e needs one panel row (--parallel 1), a panel of "
                      "at least 8 rows, and no --rotate 90/270",
                      file=sys.stderr)
                return 2
            # Drive the panel as if it had half the rows, which only uses
            # address lines A-D. The panel then shows four 16-row bands
            # (for 64 rows); we fill each band with a strip plus its mirror.
            args.height = p_rows // 2
            no_e_strip = p_rows // 8
    elif args.no_e:
        print("--no-e only applies to --device hub75", file=sys.stderr)
        return 2
    else:
        args.width = args.width or 10
        args.height = args.height or 10

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if args.list:
        list_animations()
        return 0

    if not args.names:
        ap.print_help()
        return 0

    for name in args.names:
        if name not in AUTOMATION_REGISTRY:
            print(f"unknown animation: {name!r}", file=sys.stderr)
            print("run with --list to see options", file=sys.stderr)
            return 2
    args.name = ", ".join(args.names)

    def _coerce(v):
        for caster in (int, float):
            try:
                return caster(v)
            except ValueError:
                pass
        if v.lower() in ("true", "false"):
            return v.lower() == "true"
        return v

    params = {}
    for item in args.param:
        if "=" not in item:
            print(f"ignoring malformed --param {item!r} (need K=V)", file=sys.stderr)
            continue
        k, v = item.split("=", 1)
        params[k.strip()] = _coerce(v.strip())

    def make_anim(name):
        cls = AUTOMATION_REGISTRY[name]
        # Pass --palette / --warp / --param only to animations whose __init__
        # accepts them, so flags are harmless on ones that don't support them.
        sig_params = inspect.signature(cls.__init__).parameters
        extra = {}
        if args.palette is not None and "palette" in sig_params:
            extra["palette"] = args.palette
        if args.warp is not None and "warp" in sig_params:
            extra["warp"] = args.warp
        for k, v in params.items():
            if k in sig_params:
                extra[k] = v
            elif len(args.names) == 1:
                print(f"note: {name!r} has no param {k!r}, ignoring",
                      file=sys.stderr)
        return cls(rw, rh, fps=args.fps, **extra)

    # Render at the pre-rotation size, so after --rotate the frame lands
    # exactly on the output's width x height (matters for non-square panels).
    args.rotate %= 360
    quarter = args.rotate in (0, 90, 180, 270)
    out_w, out_h = (args.width, no_e_strip) if args.no_e else (args.width, args.height)
    if not quarter:
        # Any other angle: render a square canvas big enough that the
        # rotated output rectangle fits inside it, then bilinear-sample the
        # output pixels from it (inverse rotation about the centres).
        rw = rh = int(np.ceil(np.hypot(out_w, out_h))) + 1
        th = np.radians(args.rotate)
        oy, ox = np.mgrid[0:out_h, 0:out_w].astype(np.float32)
        ox -= (out_w - 1) / 2.0
        oy -= (out_h - 1) / 2.0
        # Content turns clockwise on screen (y down), so sample the canvas
        # at the counter-clockwise rotation of each output pixel.
        sx = ox * np.cos(th) + oy * np.sin(th) + (rw - 1) / 2.0
        sy = -ox * np.sin(th) + oy * np.cos(th) + (rh - 1) / 2.0
        x0 = np.clip(np.floor(sx).astype(np.int32), 0, rw - 2)
        y0 = np.clip(np.floor(sy).astype(np.int32), 0, rh - 2)
        fx = np.clip(sx - x0, 0.0, 1.0)[..., None]
        fy = np.clip(sy - y0, 0.0, 1.0)[..., None]

        def rotate_frame(fr):
            fr = fr.astype(np.float32)
            top = fr[y0, x0] * (1 - fx) + fr[y0, x0 + 1] * fx
            bot = fr[y0 + 1, x0] * (1 - fx) + fr[y0 + 1, x0 + 1] * fx
            return top * (1 - fy) + bot * fy
    elif args.no_e:
        rw, rh = out_w, out_h
    elif args.rotate in (90, 270):
        rw, rh = args.height, args.width
    else:
        rw, rh = args.width, args.height
    anim = make_anim(args.names[0])
    anim_idx = 0
    cycles = 0.0        # completed passes through the list (fractional mid-fade)

    # Hue rotation that keeps luminance: go to YIQ (Y = luma), turn the
    # I/Q chroma plane by the angle, come back. Y is untouched, so every
    # pixel keeps its brightness and the picture keeps its contrast.
    rgb2yiq = np.array([[0.299, 0.587, 0.114],
                        [0.596, -0.274, -0.322],
                        [0.211, -0.523, 0.312]], dtype=np.float32)
    yiq2rgb = np.linalg.inv(rgb2yiq).astype(np.float32)

    def hue_matrix(deg):
        c, s_ = np.cos(np.radians(deg)), np.sin(np.radians(deg))
        rot = np.array([[1, 0, 0], [0, c, -s_], [0, s_, c]], dtype=np.float32)
        return (yiq2rgb @ rot @ rgb2yiq).T
    anim_start = 0.0    # wall time (since t0) the current animation began
    nxt = None          # the incoming animation during a crossfade

    count = args.count if args.count is not None else args.width * args.height

    # Parse --balance START:END:R,G,B entries into (start, end, (r,g,b)).
    balance_spec = []
    for item in args.balance:
        try:
            start_s, end_s, gains_s = item.split(":")
            gains = tuple(float(v) for v in gains_s.split(","))
            if len(gains) != 3:
                raise ValueError
            balance_spec.append((int(start_s), int(end_s), gains))
        except ValueError:
            print(f"ignoring malformed --balance {item!r} "
                  f"(need START:END:R,G,B)", file=sys.stderr)
    if balance_spec:
        print(f"white-balance calibration: {len(balance_spec)} range(s)")

    if args.device == "hub75":
        from core.drivers.hub75 import HUB75Device, HAS_RGBMATRIX
        if not HAS_RGBMATRIX:
            print("rgbmatrix module not found - install rpi-rgb-led-matrix's "
                  "Python bindings (see ledctl/hub75/setup_pi_hub75.sh)",
                  file=sys.stderr)
            return 1
        dev = HUB75Device({"hub75": {
            "rows": args.height // args.parallel,
            "cols": args.width // args.chain,
            "chain_length": args.chain,
            "parallel": args.parallel,
            "hardware_mapping": args.hardware_mapping,
            "gpio_slowdown": args.gpio_slowdown,
            "brightness": args.matrix_brightness,
            "pwm_bits": args.pwm_bits,
            "pwm_lsb_nanoseconds": args.pwm_lsb_ns,
            "limit_refresh_rate_hz": args.limit_refresh,
        }})
    else:
        dev = ArduinoSerialDevice({
            "arduino": {
                "port": args.port,
                "baud": args.baud,
                "width": args.width,
                "height": args.height,
                "count": count,
                "pixel_order": args.order,
                "layout": args.layout,
                "balance": balance_spec,
            }
        })

    print(f"playing {args.name!r} on {args.device} {args.width}x{args.height} "
          f"({count} px) at {args.fps:g} fps. Ctrl-C to stop.")

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
    if args.device == "arduino" and args.fps > max_clean_fps:
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

            elapsed = now - t0
            anim_t = (elapsed - anim_start) * args.speed
            np_frame = anim.generate_frame(anim_t)

            # Several names: hold each for --each seconds, then crossfade
            # into the next one over --fade seconds. Both are rendered during
            # the fade and blended in float, so it goes through the same
            # quantizer as the float ambient animations.
            if len(args.names) > 1:
                hold = max(args.each, args.fade)
                into = elapsed - anim_start - hold
                if into >= 0 and nxt is None:
                    nxt = make_anim(args.names[(anim_idx + 1) % len(args.names)])
                wraps = (anim_idx + 1) % len(args.names) == 0
                if nxt is not None:
                    a = min(1.0, into / args.fade) if args.fade > 0 else 1.0
                    if wraps:
                        cycles = np.floor(cycles) + a
                    incoming = nxt.generate_frame(into * args.speed)
                    np_frame = (np_frame.astype(np.float32) * (1.0 - a)
                                + incoming.astype(np.float32) * a)
                    if a >= 1.0:
                        anim, nxt = nxt, None
                        anim_idx = (anim_idx + 1) % len(args.names)
                        anim_start = elapsed - into
                        print(f"  now playing {args.names[anim_idx]!r}")
                        if anim_idx == 0 and args.hue_shift:
                            cycles = float(round(cycles))
                            print(f"  colours shifted to "
                                  f"{(cycles * args.hue_shift) % 360:.0f} deg")

            hue = (cycles * args.hue_shift) % 360.0
            if hue:
                src = np_frame.astype(np.float32)
                out = src @ hue_matrix(hue)
                # A turned colour can land outside what the LEDs can show
                # (a channel < 0 or > 255). Instead of clipping, which would
                # change brightness, pull just that pixel's colour toward its
                # own grey until it fits: luma stays exact.
                y = (src @ rgb2yiq[0])[..., None]
                d = out - y
                with np.errstate(divide="ignore", invalid="ignore"):
                    k = np.where(d > 0, (255.0 - y) / d,
                                 np.where(d < 0, -y / d, np.inf))
                k = np.clip(k.min(axis=-1, keepdims=True), 0.0, 1.0)
                np_frame = np.clip(y + d * k, 0.0, 255.0)

            if not quarter:
                # Float result, so it goes through the quantizer below.
                np_frame = rotate_frame(np_frame)

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

            if args.rotate and quarter:
                # numpy rot90 is counter-clockwise; negate k for clockwise.
                k_cw = {90: -1, 180: -2, 270: -3}[int(args.rotate)]
                np_frame = np.rot90(np_frame, k=k_cw).copy()

            if args.device == "hub75":
                if np_frame.dtype != np.uint8:
                    np_frame = np.clip(np_frame, 0, 255).astype(np.uint8)
                if applied_brightness < 1.0:
                    np_frame = (np_frame.astype(np.float32)
                                * applied_brightness).astype(np.uint8)
                if args.no_e:
                    band = np.concatenate([np_frame, np_frame[::-1]])
                    np_frame = np.concatenate([band, band])
                dev.draw_numpy(np.ascontiguousarray(np_frame))
            else:
                rgb_data = frame_to_rgb_list(np_frame, applied_brightness)
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
        if args.device != "hub75":   # hub75 close() clears the panel itself
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
