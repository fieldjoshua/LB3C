#!/usr/bin/env bash
# Switch the light box between read-only "appliance" mode and normal mode.
#
# In appliance mode the SD card is never written: every change goes to RAM
# and vanishes at power-off, so pulling the plug at any moment can't corrupt
# the card. The flip side is that edits (git pull, /etc/default/lightbox)
# don't stick, so switch it off, make changes, then switch it back on.
#
# Usage (on the Pi):
#   bash ~/LB3C/ledctl/hub75/appliance.sh on      then reboot
#   bash ~/LB3C/ledctl/hub75/appliance.sh off     then reboot
#   bash ~/LB3C/ledctl/hub75/appliance.sh status
#
# Uses raspi-config's own overlay switch (do_overlayfs: 0 = enable,
# 1 = disable), which also write-protects / unprotects the boot partition.

set -euo pipefail

overlay_now() { grep -q "overlayroot=tmpfs" /proc/cmdline; }

case "${1:-status}" in
  on)
    if overlay_now; then
      echo "Appliance mode is already on."
      exit 0
    fi
    if ! systemctl is-enabled --quiet lightbox 2>/dev/null; then
      echo "The lightbox autostart isn't installed, so nothing would play." >&2
      echo "Run install_autostart.sh (or refresh_pi.sh) first." >&2
      exit 1
    fi
    sudo raspi-config nonint do_overlayfs 0
    echo
    echo "Appliance mode will be on after a reboot:  sudo reboot"
    echo "From then on you can unplug the power whenever you like."
    ;;
  off)
    if overlay_now; then
      sudo raspi-config nonint do_overlayfs 1
      echo
      echo "Appliance mode will be off after a reboot:  sudo reboot"
      echo "After the reboot, run this once more to unlock the boot partition."
    else
      # Overlay already off; this unlocks the boot partition too.
      sudo raspi-config nonint do_overlayfs 1
      sudo mount -o remount,rw /boot/firmware 2>/dev/null || true
      echo "Appliance mode is off and the card is writable. Make your"
      echo "changes, then: bash $0 on"
    fi
    ;;
  status)
    if overlay_now; then
      echo "Appliance mode: ON (read-only; changes are lost at power-off)"
    else
      echo "Appliance mode: OFF (normal; changes are saved)"
    fi
    systemctl is-active --quiet lightbox \
      && echo "Light box: playing" || echo "Light box: not running"
    ;;
  *)
    echo "usage: $0 on|off|status" >&2
    exit 2
    ;;
esac
