#!/usr/bin/env bash
# One-time setup: Python venv with kokoro-onnx, the Kokoro model (310 MB) and voices (27 MB), default config.
# Reuses an existing Kokoro install when it finds one (HyperFrames users). Safe to re-run.
set -eu
CONVERSE_HOME="${CONVERSE_HOME:-$HOME/.claude/converse}"
mkdir -p "$CONVERSE_HOME/models" "$CONVERSE_HOME/bin"
SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"
PY="$(command -v python3.12 || command -v python3.11 || command -v python3.10 || command -v python3 || true)"
[ -n "$PY" ] || { echo "python3 (3.10 or newer) is required"; exit 1; }
if [ ! -x "$CONVERSE_HOME/venv/bin/python" ]; then
  if [ -x "$HOME/.hyperframes-venv/bin/python" ] && "$HOME/.hyperframes-venv/bin/python" -c "import kokoro_onnx, soundfile" 2>/dev/null; then
    echo "Reusing the HyperFrames venv (kokoro-onnx already installed)."
    ln -sfn "$HOME/.hyperframes-venv" "$CONVERSE_HOME/venv"
  else
    echo "Creating venv and installing kokoro-onnx + soundfile (a minute or two)..."
    "$PY" -m venv "$CONVERSE_HOME/venv"
    "$CONVERSE_HOME/venv/bin/pip" -q install --upgrade pip
    "$CONVERSE_HOME/venv/bin/pip" -q install kokoro-onnx soundfile
  fi
fi
BASE="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  dst="$CONVERSE_HOME/models/$f"
  if [ ! -s "$dst" ]; then
    if [ -s "$HOME/.cache/hyperframes/tts/models/$f" ]; then ln -sfn "$HOME/.cache/hyperframes/tts/models/$f" "$dst"
    elif [ -s "$HOME/.cache/hyperframes/tts/voices/$f" ]; then ln -sfn "$HOME/.cache/hyperframes/tts/voices/$f" "$dst"
    else echo "Downloading $f ..."; curl -L --progress-bar -o "$dst" "$BASE/$f"; fi
  fi
done
[ -f "$CONVERSE_HOME/config" ] || cat > "$CONVERSE_HOME/config" <<CFG
ENGINE=kokoro
KVOICE=af_sky
SPEED=1.0
PACE=normal
MODE=marked
MAX=900
VOICE=Samantha
RATE=185
CFG
ln -sfn "$SCRIPTS_DIR/speak-now.sh" "$CONVERSE_HOME/bin/converse-say"
ln -sfn "$SCRIPTS_DIR/speak-stop.sh" "$CONVERSE_HOME/bin/converse-stop"
if grep -q "speak-reply.sh" "$HOME/.claude/settings.local.json" 2>/dev/null || grep -rq "hooks/speak-reply.sh" "$PWD/.claude/settings.local.json" 2>/dev/null; then
  echo "Note: an older manual speak-reply hook is wired in a settings.local.json; remove it or replies will be spoken twice."
fi
echo "Setup done. Test: $CONVERSE_HOME/bin/converse-say \"Conversation mode works.\" (after /converse on)"
