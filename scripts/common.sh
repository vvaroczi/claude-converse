# Shared settings for the converse scripts. State lives outside the plugin so updates keep it.
CONVERSE_HOME="${CONVERSE_HOME:-$HOME/.claude/converse}"
ON_FILE="$CONVERSE_HOME/on"
CONFIG_FILE="$CONVERSE_HOME/config"
LAST_FILE="$CONVERSE_HOME/last-spoken"
VENV_PY="$CONVERSE_HOME/venv/bin/python"
MODEL="$CONVERSE_HOME/models/kokoro-v1.0.onnx"
VOICES="$CONVERSE_HOME/models/voices-v1.0.bin"
SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE=kokoro; KVOICE=af_sky; SPEED=1.3; VOICE=Samantha; RATE=185; MODE=marked; MAX=900; PACE=normal
[ -f "$CONFIG_FILE" ] && . "$CONFIG_FILE"
if [ "$ENGINE" = "kokoro" ] && { [ ! -x "$VENV_PY" ] || [ ! -f "$MODEL" ] || [ ! -f "$VOICES" ]; }; then
  if command -v say >/dev/null 2>&1; then ENGINE=say; else ENGINE=none; fi
fi
