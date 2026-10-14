#!/usr/bin/env bash
# Refresh the light box Pi in place (no wipe) and tune it for smooth,
# flicker-free playback:
#
#   - updates Raspberry Pi OS packages and cleans old ones
#   - pulls the latest LB3C code
#   - re-runs setup_pi_hub75.sh with --isolcpu (rebuilds the matrix
#     library, keeps onboard audio off, reserves CPU 3 for the panel)
#   - installs or refreshes the boot autostart, and adds steady-frame-rate
#     settings to /etc/default/lightbox
#
# Usage (on the Pi):
#   bash ~/LB3C/ledctl/hub75/refresh_pi.sh
#   bash ~/LB3C/ledctl/hub75/refresh_pi.sh --no-os   skip the OS update
#   bash ~/LB3C/ledctl/hub75/refresh_pi.sh --rebuild force a matrix rebuild
#     (normally skipped when the library hasn't changed; it adds nothing
#     to performance)
# then reboot. Turn on read-only mode afterwards with appliance.sh on.

set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/LB3C}"
HUB="$REPO_DIR/ledctl/hub75"
CONF=/etc/default/lightbox

UPDATE_OS=1
SETUP_ARGS=(--isolcpu)
for arg in "$@"; do
  case "$arg" in
    --no-os) UPDATE_OS=0 ;;
    --rebuild) SETUP_ARGS+=(--rebuild) ;;
  esac
done

say() { printf '\n==> %s\n' "$*"; }

if grep -q "overlayroot=tmpfs" /proc/cmdline; then
  echo "Read-only mode is on, so nothing done here would survive a reboot." >&2
  echo "Run: bash $HUB/appliance.sh off   then reboot and run this again." >&2
  exit 1
fi

if [[ $UPDATE_OS == 1 ]]; then
  say "Raspberry Pi OS updates"
  sudo apt-get update
  sudo apt-get full-upgrade -y
  sudo apt-get autoremove -y
  sudo apt-get clean
else
  say "Skipping Raspberry Pi OS updates (--no-os)"
fi

say "Latest LB3C code"
git -C "$REPO_DIR" pull --ff-only origin main

say "Matrix library and Pi settings"
bash "$HUB/setup_pi_hub75.sh" "${SETUP_ARGS[@]}"

say "Boot autostart"
bash "$HUB/install_autostart.sh"

# Smoothness: a Pi 3 can't render every animation at 60 fps, and a frame
# rate that wobbles between 30 and 60 reads as judder. A steady 30 fps
# looks smoother for slow ambient motion. Leave any --fps already chosen.
if ! grep -q -- "--fps" "$CONF"; then
  sudo sed -i 's/^\(LIGHTBOX_ARGS=".*\)"$/\1 --fps 30"/' "$CONF"
  echo "Added --fps 30 to $CONF"
fi
# Recolour after every full pass through the list, keeping each pixel's
# brightness (so contrast is unchanged): five palettes before it repeats.
if ! grep -q -- "--hue-shift" "$CONF"; then
  sudo sed -i 's/^\(LIGHTBOX_ARGS=".*\)"$/\1 --hue-shift 72"/' "$CONF"
  echo "Added --hue-shift 72 to $CONF"
fi
grep '^LIGHTBOX_ARGS=' "$CONF"

cat <<EOF

Refresh complete. Reboot so the kernel, CPU and audio changes take effect:
  sudo reboot

Once it plays correctly after the reboot, make it plug-and-play safe:
  bash $HUB/appliance.sh on
EOF
