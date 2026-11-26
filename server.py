"""Synced playback of the ablation (make_ablation.py) on the Mac and a phone.

    python3 server.py

Open http://localhost:8766/ on the Mac and the printed /phone address on the
phone (same Wi-Fi). The Mac page plays ablation/system.wav and has the level
meter; the phone page plays ablation/mic.wav. The server sends both pages the
same start time (clocks synced by /time) and sets the Mac's output volume per
slot (ablation/schedule.tsv), putting it back at the end.
"""

import json
import os
import queue
import socket
import subprocess
import threading
import time
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).parent
AUDIO = HERE / "ablation"
PORT = int(os.environ.get("PORT", 8766))
START_LEAD_MS = 2500
CALIBRATE_LEAD_MS = 1200

lock = threading.Lock()
clients = {}  # event queue -> role
armed = {"mac": False, "phone": False}
run = {"id": 0, "old_volume": None}


def now_ms():
    return time.time() * 1000


def broadcast(event):
    data = json.dumps(event)
    with lock:
        for q in clients:
            q.put(data)


def presence():
    with lock:
        connected = {"mac": 0, "phone": 0}
        for role in clients.values():
            connected[role] += 1
        for role, n in connected.items():
            if not n:
                armed[role] = False
        event = {"type": "presence", "connected": connected, "armed": dict(armed)}
    broadcast(event)


def volume(value=None):
    if value is None:
        out = subprocess.run(["osascript", "-e", "output volume of (get volume settings)"], capture_output=True, text=True)
        return int(out.stdout.strip())
    subprocess.run(["osascript", "-e", f"set volume output volume {value}"])


def restore_volume():
    if run["old_volume"] is not None:
        volume(run["old_volume"])
        run["old_volume"] = None


def info():
    schedule = [{"at": float(a), "volume": int(v)} for a, v in
                (line.split("\t") for line in (AUDIO / "schedule.tsv").read_text().splitlines() if line)]
    timeline = [{"slot": int(k), "track": w, "start": float(a), "end": float(b), "text": t} for k, w, a, b, t in
                (line.split("\t") for line in (AUDIO / "timeline.tsv").read_text().splitlines() if line)]
    with wave.open(str(AUDIO / "system.wav")) as w:
        duration = w.getnframes() / w.getframerate()
    return {"schedule": schedule, "timeline": timeline, "duration": duration,
            "phoneUrl": f"http://{lan_ip()}:{PORT}/phone"}


def start_test(at):
    run["id"] += 1
    rid = run["id"]
    if run["old_volume"] is None:
        run["old_volume"] = volume()
    data = info()

    def wait_until(ms):
        delay = (ms - now_ms()) / 1000
        if delay > 0:
            time.sleep(delay)
        return run["id"] == rid

    def worker():
        for step in data["schedule"]:
            if not wait_until(at + step["at"] * 1000):
                return
            volume(step["volume"])
            broadcast({"type": "volume", "value": step["volume"]})
        if wait_until(at + (data["duration"] + 1) * 1000):
            restore_volume()
            broadcast({"type": "done"})

    threading.Thread(target=worker, daemon=True).start()


def lan_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


STATIC = {
    "/": ("mac.html", "text/html; charset=utf-8"),
    "/phone": ("phone.html", "text/html; charset=utf-8"),
    "/common.js": ("common.js", "text/javascript; charset=utf-8"),
    "/nosleep.mp4": ("nosleep.mp4", "video/mp4"),
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send(self, body, ctype, code=200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, obj):
        self.send(json.dumps(obj, ensure_ascii=False).encode(), "application/json")

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in STATIC:
            name, ctype = STATIC[url.path]
            return self.send((HERE / "web" / name).read_bytes(), ctype)
        if url.path in ("/audio/system.wav", "/audio/mic.wav"):
            return self.send((AUDIO / url.path.rsplit("/", 1)[1]).read_bytes(), "audio/wav")
        if url.path == "/time":
            return self.send_json({"t": now_ms()})
        if url.path == "/info":
            return self.send_json(info())
        if url.path == "/events":
            return self.events(parse_qs(url.query).get("role", ["mac"])[0])
        self.send(b"not found", "text/plain", 404)

    def events(self, role):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        q = queue.Queue()
        with lock:
            clients[q] = role if role in armed else "mac"
        presence()
        try:
            while True:
                try:
                    self.wfile.write(f"data: {q.get(timeout=10)}\n\n".encode())
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                self.wfile.flush()
        except OSError:
            pass
        finally:
            with lock:
                clients.pop(q, None)
            presence()

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        action = body.get("action")
        if action == "armed":
            with lock:
                armed[body["role"]] = bool(body.get("armed"))
            presence()
        elif action == "calibrate":
            clip = next(t for t in info()["timeline"] if t["track"] == "mic")
            broadcast({"type": "calibrate", "at": now_ms() + CALIBRATE_LEAD_MS,
                       "from": clip["start"] - 0.2, "to": clip["end"] + 0.2})
        elif action == "start":
            at = now_ms() + START_LEAD_MS
            start_test(at)
            broadcast({"type": "start", "at": at})
        elif action == "stop":
            run["id"] += 1
            restore_volume()
            broadcast({"type": "stop"})
        self.send_json({"ok": True})


def main():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    server.daemon_threads = True
    print(f"Mac:   http://localhost:{PORT}/")
    print(f"Phone: http://{lan_ip()}:{PORT}/phone   (or http://{socket.gethostname()}:{PORT}/phone)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        restore_volume()


if __name__ == "__main__":
    main()
