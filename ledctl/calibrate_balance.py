#!/usr/bin/env python3
"""Interactive white-balance calibration for panels built from mismatched
LED strip batches.

Displays a flat grey field (so nothing but the calibration changes) and
cycles through candidate per-LED gain settings, announcing each one. You
watch the panel, note which numbered option looks most uniform, and feed
that number into the next, finer stage.

Three modes, meant to be run in order:

  split   locate the batch boundary - dims successive index ranges so you
          can see exactly where the mismatch starts
  coarse  sweep the main correction directions (warm/cool/green/dim)
  fine    refine around a chosen triple, one small step per channel

Example session:
    python3 ledctl/calibrate_balance.py --mode split
    python3 ledctl/calibrate_balance.py --mode coarse --split 50
    python3 ledctl/calibrate_balance.py --mode fine --around 1.0,0.94,0.82

Ctrl-C clears the strip and exits.
"""

from __future__ import annotations

import argparse
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.drivers.arduino_serial import ArduinoSerialDevice  # noqa: E402


def coarse_candidates():
    """Main correction directions. Gains apply to the corrected section."""
    return [
        ((1.00, 1.00, 1.00), "no correction (baseline)"),
        ((1.00, 1.00, 0.92), "slightly less blue  (fixes: too cool)"),
        ((1.00, 0.99, 0.84), "less blue           (fixes: too cool)"),
        ((1.00, 0.98, 0.74), "much less blue      (fixes: very cool)"),
        ((0.94, 1.00, 1.00), "slightly less red   (fixes: too warm)"),
        ((0.86, 0.99, 1.00), "less red            (fixes: too warm)"),
        ((0.76, 0.98, 1.00), "much less red       (fixes: very warm)"),
        ((1.00, 0.88, 1.00), "less green          (fixes: too green)"),
        ((0.97, 1.00, 0.97), "less red+blue       (fixes: too pink)"),
        ((0.88, 0.88, 0.88), "dim all             (fixes: too bright)"),
    ]


def fine_candidates(base, step):
    r, g, b = base
    out = [((r, g, b), "current best (reference)")]
    for name, idx in (("red", 0), ("green", 1), ("blue", 2)):
        for sign, word in ((+1, "more"), (-1, "less")):
            v = list(base)
            v[idx] = round(max(0.0, min(2.0, v[idx] + sign * step)), 3)
            out.append((tuple(v), f"{word} {name}"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=["split", "coarse", "fine", "static"],
                    default="coarse")
    ap.add_argument("--split", type=int, default=50,
                    help="LED index where the second batch starts (default 50)")
    ap.add_argument("--target", choices=["second", "first"], default="second",
                    help="which section to apply gains to (default second)")
    ap.add_argument("--around", default="1.0,1.0,1.0",
                    help="fine mode: the triple to refine around, R,G,B")
    ap.add_argument("--step", type=float, default=0.04,
                    help="fine mode: adjustment size per channel (default 0.04)")
    ap.add_argument("--level", type=int, default=110,
                    help="grey level 0-255 to display (default 110)")
    ap.add_argument("--hold", type=float, default=5.0,
                    help="seconds to show each candidate (default 5)")

    ap.add_argument("--width", type=int, default=10)
    ap.add_argument("--height", type=int, default=10)
    ap.add_argument("--count", type=int, default=None)
    ap.add_argument("--fps", type=float, default=40.0)
    ap.add_argument("--port", default=None)
    ap.add_argument("--baud", type=int, default=500000)
    ap.add_argument("--order", default="GRB")
    ap.add_argument("--layout", default="serpentine",
                    choices=["serpentine", "linear"])
    args = ap.parse_args()

    count = args.count if args.count is not None else args.width * args.height
    split = max(0, min(count, args.split))

    # Build the candidate list for the chosen mode.
    if args.mode == "split":
        candidates = []
        n = 4
        for i in range(n):
            lo = int(count * i / n)
            hi = int(count * (i + 1) / n)
            candidates.append((("RANGE", lo, hi), f"dimming LEDs {lo}-{hi - 1}"))
    elif args.mode == "coarse":
        candidates = coarse_candidates()
    else:
        try:
            base = tuple(float(v) for v in args.around.split(","))
            if len(base) != 3:
                raise ValueError
        except ValueError:
            print(f"--around must be R,G,B (got {args.around!r})", file=sys.stderr)
            return 2
        candidates = fine_candidates(base, args.step)

    if args.mode == "split":
        section = "(dimming one quarter at a time)"
    else:
        lo, hi = (split, count) if args.target == "second" else (0, split)
        section = f"(gains applied to LEDs {lo}-{hi - 1})"

    print(f"\ncalibration: mode={args.mode} {section}")
    print(f"grey level {args.level}, {args.hold:g}s per option, "
          f"{len(candidates)} options, looping. Ctrl-C to stop.\n")
    for i, (val, label) in enumerate(candidates, 1):
        if args.mode == "split":
            print(f"  {i}. {label}")
        else:
            print(f"  {i}. R={val[0]:.2f} G={val[1]:.2f} B={val[2]:.2f}   {label}")
    print()

    dev = ArduinoSerialDevice({
        "arduino": {
            "port": args.port, "baud": args.baud,
            "width": args.width, "height": args.height, "count": count,
            "pixel_order": args.order, "layout": args.layout,
        }
    })
    dev.open()

    # STATIC mode: latch one frame, then stop transmitting entirely.
    # WS2811 chips hold their last value with no data, so anything that
    # still moves after this cannot be caused by the data path - it is
    # power or the LEDs themselves. This separates "refresh/signal
    # integrity" from "hardware" definitively.
    if args.mode == "static":
        try:
            base = tuple(float(v) for v in args.around.split(","))
            if len(base) != 3:
                raise ValueError
        except ValueError:
            base = (1.0, 1.0, 1.0)
        table = [(1.0, 1.0, 1.0)] * count
        lo, hi = (split, count) if args.target == "second" else (0, split)
        for j in range(lo, hi):
            table[j] = base
        dev.balance = table
        lvl = max(0, min(255, args.level))
        grey = [(lvl, lvl, lvl)] * (args.width * args.height)
        print(f"latching grey {lvl} with gains R={base[0]:.2f} "
              f"G={base[1]:.2f} B={base[2]:.2f} on LEDs {lo}-{hi - 1} ...")
        for _ in range(5):                 # a few frames to be certain
            dev.draw_rgb_frame(args.width, args.height, grey)
            time.sleep(0.05)
        print("\n*** TRANSMISSION STOPPED - no more data is being sent. ***")
        print("Watch the panel for 30s:")
        print("  flicker STOPS     -> the data/refresh path is the cause")
        print("  flicker CONTINUES -> power or the LEDs themselves\n")
        try:
            time.sleep(30.0)
        except KeyboardInterrupt:
            pass
        print("done - the strip keeps its last value until you Ctrl-C.")
        try:
            input("press Enter to blank the strip and exit...")
        except (EOFError, KeyboardInterrupt):
            pass
        try:
            dev.draw_rgb_frame(args.width, args.height,
                               [(0, 0, 0)] * (args.width * args.height))
        except Exception:
            pass
        dev.close()
        return 0

    stop = {"v": False}
    signal.signal(signal.SIGINT, lambda *a: stop.__setitem__("v", True))
    signal.signal(signal.SIGTERM, lambda *a: stop.__setitem__("v", True))

    lvl = max(0, min(255, args.level))
    grey = [(lvl, lvl, lvl)] * (args.width * args.height)
    period = 1.0 / max(args.fps, 1.0)

    try:
        while not stop["v"]:
            for i, (val, label) in enumerate(candidates, 1):
                if stop["v"]:
                    break
                # Install this candidate's gain table.
                table = [(1.0, 1.0, 1.0)] * count
                if args.mode == "split":
                    _, lo, hi = val
                    for j in range(lo, hi):
                        table[j] = (0.25, 0.25, 0.25)
                    print(f"  >> {i}. {label}")
                else:
                    lo, hi = (split, count) if args.target == "second" else (0, split)
                    for j in range(lo, hi):
                        table[j] = val
                    print(f"  >> {i}. R={val[0]:.2f} G={val[1]:.2f} "
                          f"B={val[2]:.2f}   {label}")
                dev.balance = table

                end = time.monotonic() + args.hold
                while time.monotonic() < end and not stop["v"]:
                    dev.draw_rgb_frame(args.width, args.height, grey)
                    time.sleep(period)
    finally:
        try:
            dev.draw_rgb_frame(args.width, args.height,
                               [(0, 0, 0)] * (args.width * args.height))
        except Exception:
            pass
        dev.close()
        print("\nstopped. Note the option number that looked best.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
