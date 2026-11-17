#!/usr/bin/env bash
# Stop any speech at once. Runs on UserPromptSubmit, so whatever the person sends cuts the voice.
SELF="$(python3 -c 'import os,sys;print(os.path.realpath(sys.argv[1]))' "$0")"; . "$(dirname "$SELF")/common.sh"
pkill -f "^$VENV_PY $SCRIPTS_DIR/speak-kokoro.py" 2>/dev/null
pkill -x say 2>/dev/null
pkill -x afplay 2>/dev/null
sleep 0.3
pkill -x afplay 2>/dev/null
exit 0
