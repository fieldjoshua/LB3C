#!/usr/bin/env bash
# Lean setup for driving a HUB75 RGB matrix from a Raspberry Pi with the
# Adafruit RGB Matrix Bonnet/HAT, using ledctl/play_animation.py.
#
# Installs only what the animation player needs (numpy, Pillow, pyserial and
# the rpi-rgb-led-matrix Python bindings) into ~/LB3C/venv. It deliberately
# skips OpenCV, Flask and Redis, which the player does not use and which are
# slow or painful to install on a Pi 3.
#
# Usage (on the Pi):
#   bash ~/LB3C/ledctl/hub75/setup_pi_hub75.sh            # standard
#   bash ~/LB3C/ledctl/hub75/setup_pi_hub75.sh --isolcpu  # also reserve CPU 3
#
# Safe to re-run.

set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/LB3C}"
MATRIX_DIR="${MATRIX_DIR:-$HOME/rpi-rgb-led-matrix}"
VENV="$REPO_DIR/venv"
ISOLCPU=0
[[ "${1:-}" == "--isolcpu" ]] && ISOLCPU=1

say() { printf '\n==> %s\n' "$*"; }

# Bookworm moved the boot files under /boot/firmware.
if [[ -f /boot/firmware/config.txt ]]; then
  BOOT=/boot/firmware
else
  BOOT=/boot
fi

say "System packages"
sudo apt-get update
sudo apt-get install -y git python3-venv python3-dev cython3 build-essential

say "Disable onboard audio (it shares the PWM hardware the matrix needs)"
# rpi-rgb-led-matrix refuses to run, or flickers badly, while the
# snd_bcm2835 driver is loaded.
if grep -qE '^\s*dtparam=audio=on' "$BOOT/config.txt"; then
  sudo sed -i 's/^\s*dtparam=audio=on/dtparam=audio=off/' "$BOOT/config.txt"
elif ! grep -qE '^\s*dtparam=audio=off' "$BOOT/config.txt"; then
  echo 'dtparam=audio=off' | sudo tee -a "$BOOT/config.txt" >/dev/null
fi
echo 'blacklist snd_bcm2835' | sudo tee /etc/modprobe.d/blacklist-rgb-matrix.conf >/dev/null
NEEDS_REBOOT=1

if [[ $ISOLCPU == 1 ]]; then
  say "Reserve CPU 3 for the matrix refresh thread (reduces flicker)"
  if ! grep -q 'isolcpus=' "$BOOT/cmdline.txt"; then
    sudo sed -i 's/$/ isolcpus=3/' "$BOOT/cmdline.txt"
  fi
fi

say "LB3C repository"
if [[ -d "$REPO_DIR/.git" ]]; then
  git -C "$REPO_DIR" pull --ff-only origin main
else
  git clone https://github.com/fieldjoshua/LB3C.git "$REPO_DIR"
fi

say "Python virtual environment"
[[ -d "$VENV" ]] || python3 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install numpy pillow pyserial cython

say "rpi-rgb-led-matrix Python bindings"
if [[ -d "$MATRIX_DIR/.git" ]]; then
  git -C "$MATRIX_DIR" pull --ff-only
else
  git clone https://github.com/hzeller/rpi-rgb-led-matrix.git "$MATRIX_DIR"
fi
# Upstream builds and installs the bindings with `pip install .` from the
# repo root, so this lands directly in our venv.
(cd "$MATRIX_DIR" && "$VENV/bin/pip" install .)

"$VENV/bin/python" -c "import rgbmatrix; print('rgbmatrix import OK')"

cat <<EOF

Setup complete.

$( [[ ${NEEDS_REBOOT:-0} == 1 ]] && echo "REBOOT REQUIRED so the audio change takes effect:  sudo reboot" )

Then test (the matrix library needs root):
  sudo $VENV/bin/python $REPO_DIR/ledctl/play_animation.py tunnel --device hub75

Panel not 64x64? Add e.g.  --panel 32x64
Flicker or garbage?        Add --gpio-slowdown 3
EOF
