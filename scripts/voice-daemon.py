#!/usr/bin/env python3
"""Converse voice daemon: keeps Kokoro loaded and warm so speech starts in a fraction of a second.

Run with the converse venv python. Listens on $CONVERSE_HOME/voice.sock, one JSON request per connection:
  {"cmd": "say", "text": "...", "voice": "af_sky", "speed": 1.0, "lang": "en-us"}
  {"cmd": "stop"}   {"cmd": "ping"}   {"cmd": "quit"}
Replies with one line ("ok" or "err ...") at once; speaking happens in the background.
The first chunk is kept to the first sentence (or clause) so the voice starts while the text is still printing.
Exits after CONVERSE_IDLE seconds (default 3600) with nothing said."""
import json, os, queue, re, shutil, socket, subprocess, sys, tempfile, threading, time

HOME = os.environ.get("CONVERSE_HOME") or os.path.expanduser("~/.claude/converse")
SOCK = os.path.join(HOME, "voice.sock")
MODEL = os.path.join(HOME, "models", "kokoro-v1.0.onnx")
VOICES = os.path.join(HOME, "models", "voices-v1.0.bin")
IDLE = int(os.environ.get("CONVERSE_IDLE", "3600"))


def already_running():
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.connect(SOCK)
        s.sendall(b'{"cmd":"ping"}\n')
        return s.recv(16).startswith(b"ok")
    except OSError:
        return False
    finally:
        s.close()


if already_running():
    sys.exit(0)

from kokoro_onnx import Kokoro  # noqa: E402
import soundfile as sf  # noqa: E402

kokoro = Kokoro(MODEL, VOICES)
PLAYER = (["afplay"] if shutil.which("afplay") else
          ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"] if shutil.which("ffplay") else
          ["aplay", "-q"] if shutil.which("aplay") else None)
TMP = tempfile.mkdtemp(prefix="converse-")
synth_lock = threading.Lock()   # one Kokoro call at a time
state_lock = threading.Lock()
generation = 0                  # bumped by every say/stop; older jobs see the change and end
player_proc = None
last_used = time.time()


def synth(text, voice, speed, lang):
    with synth_lock:
        return kokoro.create(text, voice=voice, speed=speed, lang=lang)


# Warm the session (the first create after load is several times slower than the rest).
try:
    synth("Ready.", "af_sky", 1.0, "en-us")
except Exception:
    pass


# Chunk sizes, in characters. Kokoro makes speech about 4-5x faster than real time on a Mac, and each
# chunk is made while the one before it plays, so a chunk must take less time to make than the one
# before it takes to say. A first chunk of a single word ("Done.") lasts under a second, too short to
# cover the next one, so it is padded to MIN_FIRST; the second chunk stays small; later ones grow.
MIN_FIRST = 35
LIMITS = [110, 90, 160]   # max chars for chunk 1, 2, 3; 220 after that


def chunks(text):
    """Split text into chunks that play back to back with no silence between them."""
    pieces = []
    for s in re.split(r"(?<=[.!?…])\s+", text):
        s = s.strip()
        if not s:
            continue
        if len(s) > 90:  # long sentence: allow breaks at clause boundaries
            pieces.extend(p for p in re.split(r"(?<=[,;:—–])\s+", s) if p)
        else:
            pieces.append(s)
    out, cur = [], ""
    for p in pieces:
        i = len(out)
        limit = LIMITS[i] if i < len(LIMITS) else 220
        floor = MIN_FIRST if i == 0 else 0
        if cur and len(cur) + 1 + len(p) > limit and len(cur) >= floor:
            out.append(cur)
            cur = p
        else:
            cur = (cur + " " + p).strip()
    if cur:
        out.append(cur)
    return out


def kill_player():
    global player_proc
    p = player_proc
    player_proc = None
    if p and p.poll() is None:
        try:
            p.kill()
        except OSError:
            pass


def generation_bump():
    global generation
    generation += 1


def speak_job(gen, text, voice, speed, lang):
    global player_proc
    q = queue.Queue(maxsize=3)

    def produce():
        for i, c in enumerate(chunks(text)):
            if gen != generation:
                break
            try:
                samples, sr = synth(c, voice, speed, lang)
            except Exception:
                continue
            if gen != generation:
                break
            path = os.path.join(TMP, f"{gen}-{i}.wav")
            sf.write(path, samples, sr)
            q.put(path)
        q.put(None)

    threading.Thread(target=produce, daemon=True).start()
    while True:
        path = q.get()
        if path is None:
            break
        if gen == generation and PLAYER:
            with state_lock:
                if gen != generation:
                    proc = None
                else:
                    proc = player_proc = subprocess.Popen(PLAYER + [path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if proc:
                proc.wait()
                if proc.returncode != 0:
                    # The player was killed from outside (an older stop hook, `pkill afplay`): treat it as stop.
                    with state_lock:
                        if gen == generation:
                            generation_bump()
                    gen = -1
        try:
            os.remove(path)
        except OSError:
            pass


def handle(req):
    global generation, last_used
    cmd = req.get("cmd")
    last_used = time.time()
    if cmd == "ping":
        return "ok"
    if cmd in ("stop", "say", "quit"):
        with state_lock:
            generation += 1
            gen = generation
            kill_player()
        if cmd == "say":
            text = str(req.get("text") or "").strip()
            if text:
                threading.Thread(target=speak_job, daemon=True, args=(
                    gen, text, str(req.get("voice") or "af_sky"),
                    float(req.get("speed") or 1.0), str(req.get("lang") or "en-us"))).start()
        if cmd == "quit":
            threading.Thread(target=shutdown, daemon=True).start()
        return "ok"
    return "err unknown command"


def shutdown():
    time.sleep(0.1)
    try:
        os.remove(SOCK)
    except OSError:
        pass
    shutil.rmtree(TMP, ignore_errors=True)
    os._exit(0)


def idle_watch():
    while True:
        time.sleep(30)
        if time.time() - last_used > IDLE and player_proc is None:
            shutdown()


try:
    os.remove(SOCK)
except OSError:
    pass
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind(SOCK)
os.chmod(SOCK, 0o600)
server.listen(8)
threading.Thread(target=idle_watch, daemon=True).start()
while True:
    conn, _ = server.accept()
    try:
        conn.settimeout(2)
        data = b""
        while not data.endswith(b"\n") and len(data) < 65536:
            part = conn.recv(8192)
            if not part:
                break
            data += part
        try:
            reply = handle(json.loads(data.decode("utf-8") or "{}"))
        except Exception as e:
            reply = "err " + type(e).__name__
        conn.sendall((reply + "\n").encode())
    except OSError:
        pass
    finally:
        conn.close()
