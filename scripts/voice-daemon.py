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
PLAYER = (os.environ["CONVERSE_PLAYER"].split() if os.environ.get("CONVERSE_PLAYER") else
          ["afplay"] if shutil.which("afplay") else
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


# ---- Queue across chats ------------------------------------------------------------------------
# Every request names its source (the Claude Code session). Replies from different chats wait their
# turn instead of cutting each other off; a chat's newer reply replaces its own older one (playing or
# waiting); a stop from a chat clears only that chat. When the voice switches to a different chat
# within LABEL_WINDOW seconds of the last one, the reply opens with that chat's label.
LABEL_WINDOW = 900

# ---- A voice per chat --------------------------------------------------------------------------
# The first chat speaks in the configured voice. A new chat that starts while others have spoken in
# the last ACTIVE_WINDOW gets the next English voice in POOL that no active chat is using, so you can
# tell chats apart by ear. "use Emma" in a chat pins that chat's voice. Kept in voices.json.
VOICE_FILE = os.path.join(HOME, "voices.json")
ACTIVE_WINDOW = 12 * 3600
POOL = ["af_sky", "bm_george", "bf_emma", "am_michael", "af_heart", "bm_lewis", "af_bella", "am_adam", "bf_isabella", "af_nicole"]
NAMES = {"af_sky": "Sky", "af_heart": "Heart", "af_bella": "Bella", "af_nicole": "Nicole", "bf_emma": "Emma",
         "bf_isabella": "Isabella", "am_adam": "Adam", "am_michael": "Michael", "bm_george": "George", "bm_lewis": "Lewis"}
try:
    assigned = {s: v for s, v in json.load(open(VOICE_FILE)).items() if time.time() - v.get("seen", 0) < 7 * 86400}
except Exception:
    assigned = {}


def save_voices():
    try:
        tmp = VOICE_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(assigned, f)
        os.replace(tmp, VOICE_FILE)
    except OSError:
        pass


def voice_id(name):
    """Accept a voice id (bf_emma) or its name (Emma)."""
    name = str(name or "").strip()
    for vid, n in NAMES.items():
        if name.lower() in (vid, n.lower()):
            return vid
    return name if re.fullmatch(r"[a-z]{2}_[a-z]+", name) else None


def voice_for(source, default, lang):
    """The voice this chat speaks in; assigns one on first use (caller holds state_lock)."""
    now = time.time()
    a = assigned.get(source)
    if a:
        a["seen"] = now
        save_voices()
        return a["voice"]
    if not lang.startswith("en"):
        return default  # other languages: use the voice picked for that language
    in_use = {v["voice"] for s, v in assigned.items() if s != source and now - v.get("seen", 0) < ACTIVE_WINDOW}
    pick = default if default not in in_use else next((v for v in POOL if v not in in_use), default)
    assigned[source] = {"voice": pick, "pinned": False, "seen": now}
    save_voices()
    return pick


pending = []            # jobs waiting: dicts with source, label, text, voice, speed, lang
current = None          # job playing now
last_source, last_end = None, 0.0
wake = threading.Condition(state_lock)


def cancel_current():
    """Stop what is playing now (caller holds state_lock)."""
    global generation
    generation += 1
    kill_player()


def worker():
    global current, generation, last_source, last_end
    while True:
        with wake:
            while not pending:
                wake.wait()
            job = pending.pop(0)
            generation += 1
            gen = generation
            current = job
            prefix = ""
            if (job["label"] and last_source and last_source != job["source"]
                    and time.time() - last_end < LABEL_WINDOW):
                prefix = job["label"].rstrip(".") + ". "
        if os.environ.get("CONVERSE_DEBUG"):
            with open(os.path.join(HOME, "voice-debug.log"), "a") as f:
                f.write(f"{time.time():.2f} play {job['source']} {job['voice']} | {prefix + job['text']}\n")
        try:
            speak_job(gen, prefix + job["text"], job["voice"], job["speed"], job["lang"])
        except Exception:
            pass
        with wake:
            current = None
            last_source, last_end = job["source"], time.time()


def handle(req):
    global last_used
    cmd = req.get("cmd")
    last_used = time.time()
    source = str(req.get("source") or "default")
    if cmd == "ping":
        return "ok"
    if cmd == "say":
        text = str(req.get("text") or "").strip()
        if not text:
            return "ok"
        lang = str(req.get("lang") or "en-us")
        job = {"source": source, "label": str(req.get("label") or "")[:40], "text": text,
               "speed": float(req.get("speed") or 1.0), "lang": lang}
        with wake:
            job["voice"] = voice_for(source, str(req.get("voice") or "af_sky"), lang)
            pending[:] = [j for j in pending if j["source"] != source]
            if current and current["source"] == source:
                cancel_current()
                pending.insert(0, job)     # same chat: the new reply plays straight away
            else:
                pending.append(job)        # another chat is talking: wait for it
            wake.notify()
        return "ok"
    if cmd == "voice":
        # Which voice this chat speaks in (assigned now if it has none): "ok <id> <Name>".
        # With "set": pin this chat to that voice.
        with wake:
            if req.get("set"):
                vid = voice_id(req["set"])
                if not vid:
                    return "err unknown voice"
                assigned[source] = {"voice": vid, "pinned": True, "seen": time.time()}
                save_voices()
            vid = voice_for(source, str(req.get("voice") or "af_sky"), str(req.get("lang") or "en-us"))
        return f"ok {vid} {NAMES.get(vid, vid)}"
    if cmd in ("stop", "quit"):
        # A stop that names no chat (older hooks, plain `converse-stop`) stops everything.
        everyone = cmd == "quit" or req.get("all") or not req.get("source")
        with wake:
            if everyone:
                pending.clear()
            else:
                pending[:] = [j for j in pending if j["source"] != source]
            if current and (everyone or current["source"] == source):
                cancel_current()
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
        if time.time() - last_used > IDLE and current is None and not pending:
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
threading.Thread(target=worker, daemon=True).start()
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
