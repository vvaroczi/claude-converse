#!/usr/bin/env python3
"""Talk to the converse voice daemon. Uses the system python3 (no venv needed).
  voice-client.py say      (text on stdin; voice/speed/lang from env KVOICE, SPEED, SPEAK_LANG)
  voice-client.py stop | ping | quit
  voice-client.py start    (start the daemon if needed and wait until it is warm)
`say` and `start` launch the daemon when it is not running. Exit 0 when the daemon took the request, 1 otherwise."""
import json, os, socket, subprocess, sys, time

HOME = os.environ.get("CONVERSE_HOME") or os.path.expanduser("~/.claude/converse")
SOCK = os.path.join(HOME, "voice.sock")
HERE = os.path.dirname(os.path.realpath(__file__))
VENV_PY = os.path.join(HOME, "venv", "bin", "python")


def send(req, timeout=1.0):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect(SOCK)
        s.sendall((json.dumps(req) + "\n").encode())
        return s.recv(64).decode().strip().startswith("ok")
    except OSError:
        return False
    finally:
        s.close()


def launch(wait=12.0):
    if not os.path.exists(VENV_PY):
        return False
    subprocess.Popen([VENV_PY, os.path.join(HERE, "voice-daemon.py")], stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    end = time.time() + wait
    while time.time() < end:
        time.sleep(0.05)
        if send({"cmd": "ping"}, 0.3):
            return True
    return False


cmd = sys.argv[1] if len(sys.argv) > 1 else "ping"
if cmd == "say":
    req = {"cmd": "say", "text": sys.stdin.read(), "voice": os.environ.get("KVOICE", "af_sky"),
           "speed": float(os.environ.get("SPEED", "1.0") or 1.0), "lang": os.environ.get("SPEAK_LANG", "en-us")}
    ok = send(req) or (launch() and send(req))
elif cmd == "start":
    ok = send({"cmd": "ping"}, 0.3) or launch()
else:
    ok = send({"cmd": cmd}, 0.5)
sys.exit(0 if ok else 1)
