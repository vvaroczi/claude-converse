#!/usr/bin/env bash
# Speak a text right now. Usage: speak-now.sh "text"  |  -f file  |  --warm  |  --voice [name]
# Kokoro speech goes through the voice daemon (model kept loaded), so it starts within a fraction of a second.
# Records a hash of what was spoken so the Stop hook does not repeat it at the end of the turn.
set -u
SELF="$(python3 -c 'import os,sys;print(os.path.realpath(sys.argv[1]))' "$0")"; . "$(dirname "$SELF")/common.sh"
if [ "${1:-}" = "--warm" ]; then
  # Start the daemon in the background and return at once; it is warm a second or two later.
  [ "$ENGINE" = "kokoro" ] && { nohup python3 "$SCRIPTS_DIR/voice-client.py" start >/dev/null 2>&1 & disown; }
  exit 0
fi
if [ "${1:-}" = "--voice" ]; then
  # converse-say --voice          -> print this chat's voice, e.g. "bf_emma Emma"
  # converse-say --voice Emma     -> this chat speaks as Emma from now on
  exec python3 "$SCRIPTS_DIR/voice-client.py" voice ${2:+"$2"}
fi
[ -f "$ON_FILE" ] || exit 0
if [ "${1:-}" = "-f" ]; then TXT="$(cat "$2")"; else TXT="${1:-}"; fi
TXT="$(printf '%s' "$TXT" | sed -e 's/^[[:space:]]*🔊[[:space:]]*//' | tr -s '[:space:]' ' ')"
[ -n "$TXT" ] || exit 0
mkdir -p "$CONVERSE_HOME/last-spoken.d"
find "$CONVERSE_HOME/last-spoken.d" -type f -mtime +2 -delete 2>/dev/null
printf '%s' "$TXT" | shasum -a 256 | cut -c1-16 > "$LAST_FILE"
cp "$LAST_FILE" "$CONVERSE_HOME/last-spoken" 2>/dev/null  # for hooks from 0.1.5 and older until a restart
# Silence anything not owned by the daemon (old one-shot players, the macOS voice).
pkill -f "speak-kokoro.py" 2>/dev/null; pkill -x say 2>/dev/null
case "$ENGINE" in
  kokoro)
    if printf '%s' "$TXT" | python3 "$SCRIPTS_DIR/voice-client.py" say; then exit 0; fi
    # Daemon unavailable: one-shot fallback (slower to start).
    TMP="$(mktemp -t converse).txt"; printf '%s\n' "$TXT" > "$TMP"
    ( nohup "$VENV_PY" "$SCRIPTS_DIR/speak-kokoro.py" "$TMP" "$KVOICE" "$SPEED" "$SPEAK_LANG" >/dev/null 2>&1; rm -f "$TMP" ) & disown ;;
  say)
    TMP="$(mktemp -t converse).txt"; printf '%s\n' "$TXT" > "$TMP"
    ( nohup say -v "$VOICE" -r "$RATE" -f "$TMP" >/dev/null 2>&1; rm -f "$TMP" ) & disown ;;
  *) exit 0 ;;
esac
exit 0
