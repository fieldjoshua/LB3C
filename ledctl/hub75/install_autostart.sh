#!/usr/bin/env bash
# Make the light box plug-and-play: start playing animations on the HUB75
# panel as soon as the Pi boots, with no login or SSH needed.
#
# Installs a systemd service, "lightbox", that runs play_animation.py with the
# arguments in /etc/default/lightbox. Edit that file to change what plays,
# then: sudo systemctl restart lightbox
#
# Usage (on the Pi, after setup_pi_hub75.sh):
#   bash ~/LB3C/ledctl/hub75/install_autostart.sh
#
# Safe to re-run; an existing /etc/default/lightbox is kept.

set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/LB3C}"
VENV="$REPO_DIR/venv"
CONF=/etc/default/lightbox
UNIT=/etc/systemd/system/lightbox.service

if [[ ! -x "$VENV/bin/python" ]]; then
  echo "No venv at $VENV - run setup_pi_hub75.sh first" >&2
  exit 1
fi

if [[ ! -f "$CONF" ]]; then
  sudo tee "$CONF" >/dev/null <<'EOF'
# What the light box plays at boot. After editing:
#   sudo systemctl restart lightbox
#
# Several names cycle with a crossfade; --each is seconds per animation.
# Remove --no-e once the Bonnet's E jumper is soldered (64x64 panels).
LIGHTBOX_ARGS="ambient_sweep ambient_marble ambient_caustics ambient_plasma_noise aurora --device hub75 --no-e --each 300"
EOF
  echo "Wrote $CONF"
else
  echo "Keeping existing $CONF"
fi

sudo tee "$UNIT" >/dev/null <<EOF
[Unit]
Description=Light box HUB75 animations
After=local-fs.target

[Service]
Type=simple
EnvironmentFile=$CONF
Environment=PYTHONUNBUFFERED=1
ExecStart=$VENV/bin/python $REPO_DIR/ledctl/play_animation.py \$LIGHTBOX_ARGS
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable lightbox
sudo systemctl restart lightbox

cat <<EOF

Autostart installed and running. It will start by itself on every boot.

Change what plays:  sudo nano $CONF
Apply the change:   sudo systemctl restart lightbox
Stop it:            sudo systemctl stop lightbox
Turn autostart off: sudo systemctl disable --now lightbox
See its log:        journalctl -u lightbox -f
EOF
