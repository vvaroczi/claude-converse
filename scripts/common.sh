# Shared settings for the converse scripts. State lives outside the plugin so updates keep it.
CONVERSE_HOME="${CONVERSE_HOME:-$HOME/.claude/converse}"
ON_FILE="$CONVERSE_HOME/on"
CONFIG_FILE="$CONVERSE_HOME/config"
VENV_PY="$CONVERSE_HOME/venv/bin/python"
MODEL="$CONVERSE_HOME/models/kokoro-v1.0.onnx"
VOICES="$CONVERSE_HOME/models/voices-v1.0.bin"
SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE=kokoro; KVOICE=af_sky; SPEED=1.0; SPEAK_LANG=en-us; VOICE=Samantha; RATE=185; MODE=marked; MAX=900; PACE=normal; USER_NAME=
[ -f "$CONFIG_FILE" ] && . "$CONFIG_FILE"
if [ "$ENGINE" = "kokoro" ] && { [ ! -x "$VENV_PY" ] || [ ! -f "$MODEL" ] || [ ! -f "$VOICES" ]; }; then
  if command -v say >/dev/null 2>&1; then ENGINE=say; else ENGINE=none; fi
fi
# Which chat this is: set by the hooks (CONVERSE_SOURCE), else the Claude Code session running the command.
CONVERSE_SOURCE="$(printf '%s' "${CONVERSE_SOURCE:-${CLAUDE_CODE_SESSION_ID:-default}}" | tr -cd 'A-Za-z0-9_-' | cut -c1-64)"
[ -n "$CONVERSE_SOURCE" ] || CONVERSE_SOURCE=default
# What the voice calls this chat when it takes over from another one: the project folder's name.
if [ -z "${CONVERSE_LABEL:-}" ]; then
  _dir="${CONVERSE_CWD:-$PWD}"
  _top="$(git -C "$_dir" rev-parse --show-toplevel 2>/dev/null || printf '%s' "$_dir")"
  CONVERSE_LABEL="$(basename "$_top" | tr '_-' '  ') chat"
fi
# What this chat last spoke, so its end-of-turn hook does not repeat it. One file per chat.
LAST_FILE="$CONVERSE_HOME/last-spoken.d/$CONVERSE_SOURCE"
export CONVERSE_HOME CONVERSE_SOURCE CONVERSE_LABEL KVOICE SPEED SPEAK_LANG
