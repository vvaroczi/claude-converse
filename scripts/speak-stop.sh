#!/usr/bin/env bash
# Stop any speech at once. Runs on UserPromptSubmit, so whatever the person sends cuts the voice.
# Usage: speak-stop.sh  |  speak-stop.sh --quit (also shut the voice daemon down)
SELF="$(python3 -c 'import os,sys;print(os.path.realpath(sys.argv[1]))' "$0")"; . "$(dirname "$SELF")/common.sh"
export CONVERSE_HOME
if [ "${1:-}" = "--quit" ]; then python3 "$SCRIPTS_DIR/voice-client.py" quit 2>/dev/null
else python3 "$SCRIPTS_DIR/voice-client.py" stop 2>/dev/null; fi
pkill -x say 2>/dev/null
# Old one-shot player (fallback path): kill it first, then the afplay it may have started.
if pkill -f "speak-kokoro.py" 2>/dev/null; then sleep 0.2; pkill -x afplay 2>/dev/null; fi
exit 0
