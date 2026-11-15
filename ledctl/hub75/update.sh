#!/usr/bin/env bash
# One-command light box update, safe in read-only (appliance) mode.
#
# Pulls the latest LB3C code and, optionally, changes the playlist, then
# applies it. In read-only mode it writes straight to the protected SD card
# (overlayroot's lower filesystem) and reboots once, so you never have to
# turn read-only mode off and on again. In normal mode it just restarts the
# light box.
#
# Usage (on the Pi), always as one line:
#   git -C ~/LB3C pull origin main && bash ~/LB3C/ledctl/hub75/update.sh
#   ... update.sh --add rain_ripples starfield     add patterns to the playlist
#   ... update.sh --remove ambient_spiral           take patterns out
#   ... update.sh --set "a b --device hub75 ..."    replace the whole line
#
# The leading git pull (into RAM when read-only) makes sure this script is
# itself the latest version before it runs.

set -euo pipefail

REPO_REL="${HOME#/}/LB3C"
CONF_REL=etc/default/lightbox
LOWER=/media/root-ro
MODE=""
NAMES=()
SET_LINE=""

while (( $# )); do
  case "$1" in
    --add|--remove) MODE="${1#--}"; shift
                    while (( $# )) && [[ "$1" != --* ]]; do NAMES+=("$1"); shift; done ;;
    --set) MODE=set; SET_LINE="${2:?--set needs the full argument line}"; shift 2 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

# Check names against the player's list before touching anything.
if [[ "$MODE" == add ]]; then
  KNOWN="$("$HOME/LB3C/venv/bin/python" "$HOME/LB3C/ledctl/play_animation.py" --list 2>/dev/null | awk 'NR>1{print $1}')"
  for n in "${NAMES[@]}"; do
    grep -qx "$n" <<<"$KNOWN" || { echo "unknown animation: $n" >&2; exit 2; }
  done
fi

edit_conf() {   # $1 = path of the lightbox config to edit
  [[ -z "$MODE" ]] && return 0
  sudo python3 - "$1" "$MODE" "$SET_LINE" "${NAMES[@]}" <<'PY'
import re, shlex, sys
path, mode, set_line, names = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
text = open(path).read()
m = re.search(r'^LIGHTBOX_ARGS="(.*)"$', text, re.M)
if not m:
    sys.exit("no LIGHTBOX_ARGS line in " + path)
args = shlex.split(m.group(1))
if mode == "set":
    args = shlex.split(set_line)
else:
    first_flag = next((i for i, a in enumerate(args) if a.startswith("--")), len(args))
    anims, rest = args[:first_flag], args[first_flag:]
    if mode == "add":
        anims += [n for n in names if n not in anims]
    else:
        anims = [a for a in anims if a not in names]
    if not anims:
        sys.exit("that would leave the playlist empty")
    args = anims + rest
line = 'LIGHTBOX_ARGS="' + " ".join(args) + '"'
open(path, "w").write(text[:m.start()] + line + text[m.end():])
print("playlist now:", line)
PY
}

if grep -q "overlayroot=tmpfs" /proc/cmdline; then
  echo "==> Read-only mode is on: updating the protected SD card directly"
  sudo mount -o remount,rw "$LOWER"
  trap 'sync; sudo mount -o remount,ro "$LOWER" 2>/dev/null || true' EXIT
  git -C "$LOWER/$REPO_REL" pull --ff-only origin main
  edit_conf "$LOWER/$CONF_REL"
  sync
  sudo mount -o remount,ro "$LOWER"
  trap - EXIT
  echo "==> Saved. Rebooting to load it (about a minute)."
  sudo reboot
else
  echo "==> Normal mode: updating in place"
  git -C "$HOME/LB3C" pull --ff-only origin main
  edit_conf "/$CONF_REL"
  sudo systemctl restart lightbox
  echo "==> Done - the light box restarted with the update."
fi
