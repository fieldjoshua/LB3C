#!/usr/bin/env bash
# Phone-friendly Wi-Fi setup for the light box, using comitup.
#
# When the Pi boots somewhere it doesn't know any Wi-Fi, it starts its own
# hotspot. Join that hotspot from a phone or laptop and a setup page opens
# (or browse to http://10.41.0.1). Pick the local network, type its
# password, and the Pi joins it and remembers it. Known networks are tried
# first, so this changes nothing where the Pi already connects.
#
# Works with read-only (appliance) mode: a network added while the overlay
# is on is copied onto the protected SD card, so it survives power-off.
#
# Usage (on the Pi, with read-only mode OFF):
#   bash ~/LB3C/ledctl/hub75/install_wifi_setup.sh
#   bash ~/LB3C/ledctl/hub75/install_wifi_setup.sh MyHotspotPassword
# The optional argument sets the hotspot password (8-63 characters,
# default "lightbox"). Remove with: sudo apt-get remove comitup

set -euo pipefail

AP_NAME=lightbox-setup
AP_PASS="${1:-lightbox}"
CALLBACK=/usr/local/bin/lightbox-wifi-persist

if (( ${#AP_PASS} < 8 || ${#AP_PASS} > 63 )) || [[ "$AP_PASS" == *%* ]]; then
  echo "Hotspot password must be 8-63 characters, without %" >&2
  exit 2
fi
if grep -q "overlayroot=tmpfs" /proc/cmdline; then
  echo "Read-only mode is on; turn it off first:" >&2
  echo "  bash ~/LB3C/ledctl/hub75/appliance.sh off   then reboot" >&2
  exit 1
fi

echo "==> Installing comitup"
sudo apt-get update
sudo apt-get install -y comitup

# In read-only mode NetworkManager saves a new network only to RAM. comitup
# runs this on every state change; on CONNECTED it copies the saved Wi-Fi
# networks onto the real (lower) filesystem that overlayroot keeps
# read-only at /media/root-ro.
echo "==> Installing the read-only-mode Wi-Fi saver"
sudo tee "$CALLBACK" >/dev/null <<'EOF'
#!/bin/sh
[ "$1" = "CONNECTED" ] || exit 0
grep -q "overlayroot=tmpfs" /proc/cmdline || exit 0
LOWER=/media/root-ro
DIR=etc/NetworkManager/system-connections
[ -d "$LOWER/$DIR" ] || exit 0
mount -o remount,rw "$LOWER" || exit 0
cp -a "/$DIR/." "$LOWER/$DIR/"
sync
mount -o remount,ro "$LOWER"
EOF
sudo chown root:root "$CALLBACK"
sudo chmod 755 "$CALLBACK"

echo "==> Configuring comitup"
if [[ -f /etc/comitup.conf && ! -f /etc/comitup.conf.orig ]]; then
  sudo cp /etc/comitup.conf /etc/comitup.conf.orig
fi
sudo tee /etc/comitup.conf >/dev/null <<EOF
ap_name: $AP_NAME
ap_password: $AP_PASS
external_callback: $CALLBACK
EOF

sudo systemctl enable comitup
sudo systemctl restart comitup

cat <<EOF

Wi-Fi setup installed.

At a new place: power the light box on and wait about 2 minutes. If it
can't find a known Wi-Fi, it makes a hotspot:
  network:  $AP_NAME
  password: $AP_PASS
Join it from your phone. The setup page should open by itself; if not,
browse to http://10.41.0.1 . Pick the local Wi-Fi, enter its password,
and the Pi joins it (your phone drops off the hotspot - that's expected).
Then put your Mac on that Wi-Fi and:  ssh joshuafield@lightbox.local

Check status any time:  comitup-cli
EOF
