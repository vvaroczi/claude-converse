#!/usr/bin/env bash
# Speak a text right now. Usage: speak-now.sh "text"  |  speak-now.sh -f file
# Records a hash of what was spoken so the Stop hook does not repeat it at the end of the turn.
set -u
SELF="$(python3 -c 'import os,sys;print(os.path.realpath(sys.argv[1]))' "$0")"; . "$(dirname "$SELF")/common.sh"
[ -f "$ON_FILE" ] || exit 0
if [ "${1:-}" = "-f" ]; then TXT="$(cat "$2")"; else TXT="${1:-}"; fi
TXT="$(printf '%s' "$TXT" | sed -e 's/^[[:space:]]*🔊[[:space:]]*//' | tr -s '[:space:]' ' ')"
[ -n "$TXT" ] || exit 0
mkdir -p "$CONVERSE_HOME"
printf '%s' "$TXT" | shasum -a 256 | cut -c1-16 > "$LAST_FILE"
bash "$SCRIPTS_DIR/speak-stop.sh"
case "$ENGINE" in
  kokoro)
    TMP="$(mktemp -t converse).txt"; printf '%s\n' "$TXT" > "$TMP"
    ( nohup "$VENV_PY" "$SCRIPTS_DIR/speak-kokoro.py" "$TMP" "$KVOICE" "$SPEED" "$SPEAK_LANG" >/dev/null 2>&1; rm -f "$TMP" ) & disown ;;
  say)
    TMP="$(mktemp -t converse).txt"; printf '%s\n' "$TXT" > "$TMP"
    ( nohup say -v "$VOICE" -r "$RATE" -f "$TMP" >/dev/null 2>&1; rm -f "$TMP" ) & disown ;;
  *) exit 0 ;;
esac
exit 0
