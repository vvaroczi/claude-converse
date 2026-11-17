#!/usr/bin/env python3
"""Speak a text file with Kokoro (kokoro-onnx), synthesizing the next chunk while the current one plays.
Usage: speak-kokoro.py <textfile> [voice] [speed] [lang]. Model and voices come from $CONVERSE_HOME/models."""
import sys, re, os, subprocess, tempfile, threading, queue, shutil
HOME = os.environ.get("CONVERSE_HOME") or os.path.expanduser("~/.claude/converse")
MODEL = os.path.join(HOME, "models", "kokoro-v1.0.onnx")
VOICES = os.path.join(HOME, "models", "voices-v1.0.bin")
text = open(sys.argv[1], encoding="utf-8").read().strip()
voice = sys.argv[2] if len(sys.argv) > 2 else "af_sky"
speed = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
lang = sys.argv[4] if len(sys.argv) > 4 else "en-us"
if not text: sys.exit(0)
from kokoro_onnx import Kokoro
import soundfile as sf
k = Kokoro(MODEL, VOICES)
parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]
chunks, cur = [], ""
for p in parts:
    cur = (cur + " " + p).strip()
    if len(cur) > (220 if chunks else 0): chunks.append(cur); cur = ""  # first chunk = first sentence, so audio starts sooner
if cur: chunks.append(cur)
player = ["afplay"] if shutil.which("afplay") else (["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"] if shutil.which("ffplay") else (["aplay", "-q"] if shutil.which("aplay") else None))
if not player: sys.exit(0)
tmp = tempfile.mkdtemp(prefix="converse-")
q = queue.Queue(maxsize=3)
def produce():
    for i, c in enumerate(chunks):
        try:
            samples, sr = k.create(c, voice=voice, speed=speed, lang=lang)
            path = os.path.join(tmp, f"{i}.wav"); sf.write(path, samples, sr); q.put(path)
        except Exception:
            pass
    q.put(None)
threading.Thread(target=produce, daemon=True).start()
while True:
    path = q.get()
    if path is None: break
    subprocess.run(player + [path])
    try: os.remove(path)
    except OSError: pass
try: os.rmdir(tmp)
except OSError: pass
