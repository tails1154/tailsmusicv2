import os
import json
import subprocess
import zipfile
import io
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

MUSIC_DIR = '/home/pi/mp3player/songs'
os.makedirs(MUSIC_DIR, exist_ok=True)

HTML = {}

def load_templates():
    base = os.path.dirname(__file__)
    for name in ["index.html", "upload.html", "wifi.html", "bluetooth.html", "ai.html"]:
        path = os.path.join(base, "templates", name)
        if os.path.exists(path):
            with open(path) as f:
                HTML[name] = f.read()

def serve_static(path):
    base = os.path.dirname(__file__)
    full = os.path.join(base, "static", path)
    if os.path.exists(full):
        with open(full, 'rb') as f:
            return f.read()
    return None

MIME = {
    ".css": "text/css",
    ".js": "application/javascript",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}

def _scan_wifi():
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "SSID,SIGNAL", "--escape", "no", "device", "wifi", "list"],
            capture_output=True, text=True, check=True, timeout=15
        )
        networks = []
        seen = set()
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split(":")
                ssid = ":".join(parts[:-1])
                signal = parts[-1] if parts[-1].isdigit() else "0"
                if ssid and ssid not in seen:
                    seen.add(ssid)
                    networks.append({"ssid": ssid, "signal": int(signal)})
        networks.sort(key=lambda x: -x["signal"])
        return networks
    except Exception as e:
        return [{"ssid": f"Error: {e}", "signal": 0}]

def _connect_wifi(ssid, password):
    try:
        subprocess.run(
            ["nmcli", "dev", "wifi", "connect", ssid, "password", password],
            capture_output=True, text=True, check=True, timeout=30
        )
        return True, "Connected successfully"
    except subprocess.CalledProcessError as e:
        return False, e.stderr or "Failed to connect"

def _bt_scan(timeout=8):
    try:
        p = subprocess.Popen(["sudo", "bluetoothctl"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        p.stdin.write("scan on\n")
        p.stdin.flush()
        import time as _t
        _t.sleep(timeout)
        p.stdin.write("scan off\n")
        p.stdin.write("devices\n")
        p.stdin.write("exit\n")
        out, _ = p.communicate(timeout=timeout + 5)
        devices = []
        for line in out.splitlines():
            if "Device" in line:
                parts = line.split()
                try:
                    i = parts.index("Device")
                    mac = parts[i + 1]
                    name = " ".join(parts[i + 2:]) if len(parts) > i + 2 else ""
                    if mac not in [d[0] for d in devices]:
                        devices.append({"mac": mac, "name": name or "Unknown"})
                except Exception:
                    pass
        return devices
    except Exception as e:
        return [{"mac": "", "name": f"Scan error: {e}"}]

def _bt_list():
    try:
        out = subprocess.check_output(["sudo", "bluetoothctl", "devices"], text=True)
        devices = []
        for line in out.splitlines():
            parts = line.split(" ", 2)
            if len(parts) >= 3 and parts[0] == "Device":
                devices.append({"mac": parts[1], "name": parts[2]})
        return devices
    except Exception as e:
        return [{"mac": "", "name": f"Error: {e}"}]

def _bt_pair_connect(mac):
    try:
        subprocess.run(["sudo", "bluetoothctl", "pair", mac], capture_output=True, text=True, timeout=15)
        subprocess.run(["sudo", "bluetoothctl", "trust", mac], capture_output=True, text=True, timeout=10)
        r = subprocess.run(["sudo", "bluetoothctl", "connect", mac], capture_output=True, text=True, timeout=20)
        if r.returncode == 0:
            return True, "Connected"
        return False, r.stderr or "Failed to connect"
    except Exception as e:
        return False, str(e)

def _bt_sinks():
    try:
        r = subprocess.run(["pactl", "list", "short", "sinks"], capture_output=True, text=True, timeout=5)
        sinks = []
        for line in r.stdout.strip().split("\n"):
            if line:
                parts = line.split("\t")
                if len(parts) >= 2:
                    sinks.append({"index": parts[0], "name": parts[1]})
        return sinks
    except Exception:
        return []

def _bt_set_sink(name):
    try:
        subprocess.run(["pactl", "set-default-sink", name], capture_output=True, text=True, timeout=5)
        return True, "Sink set"
    except Exception as e:
        return False, str(e)

def _get_ip():
    try:
        result = subprocess.run(
            ["ip", "route", "get", "8.8.8.8"],
            capture_output=True, text=True, check=True
        )
        for part in result.stdout.split():
            if part.count('.') == 3:
                return part
        return "Not connected"
    except Exception:
        return "Not connected"

AI_CONTEXT = []

def _ai_chat(user_msg):
    import requests as _req
    import random as _rnd
    global AI_CONTEXT
    if not AI_CONTEXT:
        AI_CONTEXT.append({"role": "system", "content": "You are TailsMusic AI, a voice assistant controlling a Raspberry Pi music player called TailsMusic. "
         "You can control the player with these commands (one per line, include them when appropriate):\n"
         "!next - skip to next song\n"
         "!prev - go to previous song\n"
         "!pause - toggle pause/play\n"
         "!volume N - set volume 0-100\n"
         "!shuffle - toggle shuffle mode\n"
         "!play SONG_NAME - find and play a song (use partial name)\n"
         "!current - says the currently playing song name\n"
         "!search QUERY - search for songs matching QUERY\n"
         "!stop - stop playback\n"
         "!help - list available voice commands\n\n"
         "When the user asks you to control playback, respond naturally AND include the appropriate command on its own line. "
         "Keep responses brief and conversational since they will be spoken aloud."})
    AI_CONTEXT.append({"role": "user", "content": user_msg})
    try:
        r = _req.post("https://ai.tails1154.com/api/chat",
            json={"messages": AI_CONTEXT},
            headers={"Content-Type": "application/json"}, timeout=30)
        r.raise_for_status()
        resp_text = ""
        for line in r.iter_lines():
            if line:
                try:
                    d = json.loads(line)
                    if "response" in d:
                        resp_text += d["response"]
                except:
                    pass
        if not resp_text:
            resp_text = r.text
        AI_CONTEXT.append({"role": "assistant", "content": resp_text})
        commands = []
        speech = []
        for line in resp_text.split("\n"):
            line = line.strip()
            if line.startswith("!"):
                commands.append(line[1:].strip())
            elif line:
                speech.append(line)
        return {"response": " ".join(speech), "commands": commands}
    except Exception as e:
        return {"response": f"AI error: {e}", "commands": []}

class PortalHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/') or '/'

        if path == '/':
            self._serve_html("index.html")
        elif path == '/ai':
            self._serve_html("ai.html")
        elif path == '/upload':
            self._serve_html("upload.html")
        elif path == '/wifi':
            self._serve_html("wifi.html")
        elif path == '/api/wifi/scan':
            self._json_response(_scan_wifi())
        elif path == '/bluetooth':
            self._serve_html("bluetooth.html")
        elif path == '/api/bluetooth/scan':
            self._json_response({"devices": _bt_scan()})
        elif path == '/api/bluetooth/list':
            self._json_response({"devices": _bt_list()})
        elif path == '/api/bluetooth/sinks':
            self._json_response({"sinks": _bt_sinks()})
        elif path == '/api/status':
            self._json_response({
                "ip": _get_ip(),
                "song_count": len([f for f in os.listdir(MUSIC_DIR) if f.endswith('.mp3')])
            })
        elif path.startswith('/static/'):
            rel = path[len('/static/'):]
            data = serve_static(rel)
            if data:
                ext = os.path.splitext(rel)[1]
                self.send_response(200)
                self.send_header("Content-Type", MIME.get(ext, "application/octet-stream"))
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self._serve_html("index.html")
        else:
            self._serve_html("index.html")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')

        if path == '/api/wifi/connect':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode()
            data = parse_qs(body)
            ssid = data.get('ssid', [''])[0]
            password = data.get('password', [''])[0]
            ok, msg = _connect_wifi(ssid, password)
            self._json_response({"success": ok, "message": msg})

        elif path == '/api/bluetooth/pair':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode()
            data = parse_qs(body)
            mac = data.get('mac', [''])[0]
            ok, msg = _bt_pair_connect(mac)
            self._json_response({"success": ok, "message": msg})

        elif path == '/api/bluetooth/sink/set':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode()
            data = parse_qs(body)
            name = data.get('name', [''])[0]
            ok, msg = _bt_set_sink(name)
            self._json_response({"success": ok, "message": msg})

        elif path == '/api/upload/song':
            length = int(self.headers.get('Content-Length', 0))
            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' in content_type:
                boundary = content_type.split('boundary=')[1].encode()
                raw = self.rfile.read(length)
                files = self._parse_multipart(raw, boundary)
                uploaded = []
                for name, data in files:
                    if name.lower().endswith('.mp3'):
                        dest = os.path.join(MUSIC_DIR, name)
                        with open(dest, 'wb') as f:
                            f.write(data)
                        uploaded.append(name)
                self._json_response({"success": True, "files": uploaded})
            else:
                self._json_response({"success": False, "message": "Expected multipart form data"})

        elif path == '/api/hotspot/stop':
            subprocess.Popen(["sh", "-c", "sleep 1 && sudo killall -9 python3"])
            self._json_response({"success": True, "message": "Hotspot stopping"})

        elif path == '/api/ai/chat':
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length).decode())
            msg = body.get("message", "")
            result = _ai_chat(msg)
            for cmd in result.get("commands", []):
                if cmd == "next":
                    subprocess.run(["pkill", "-f", "next_song"])
                elif cmd == "prev":
                    subprocess.run(["pkill", "-f", "prev_song"])
            self._json_response(result)

        elif path == '/api/upload/zip':
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length)
            try:
                z = zipfile.ZipFile(io.BytesIO(raw))
                extracted = []
                for name in z.namelist():
                    if name.lower().endswith('.mp3'):
                        basename = os.path.basename(name)
                        if basename:
                            z.extract(name, MUSIC_DIR)
                            if basename != name:
                                src = os.path.join(MUSIC_DIR, name)
                                dst = os.path.join(MUSIC_DIR, basename)
                                if os.path.exists(src) and not os.path.exists(dst):
                                    os.rename(src, dst)
                            extracted.append(basename)
                self._json_response({"success": True, "files": extracted})
            except Exception as e:
                self._json_response({"success": False, "message": str(e)})

        else:
            self._json_response({"success": False, "message": "Unknown endpoint"}, 404)

    def _serve_html(self, name):
        content = HTML.get(name, "<h1>404</h1>")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content.encode())))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(content.encode())

    def _json_response(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _parse_multipart(self, raw, boundary):
        parts = raw.split(b"--" + boundary)
        files = []
        for part in parts:
            if b"Content-Disposition" not in part:
                continue
            header_end = part.find(b"\r\n\r\n")
            if header_end == -1:
                continue
            headers_raw = part[:header_end].decode(errors='replace')
            body = part[header_end + 4:]
            body = body.rstrip(b"\r\n--")
            for line in headers_raw.split("\r\n"):
                if 'filename="' in line:
                    fname = line.split('filename="')[1].split('"')[0]
                    files.append((fname, body))
        return files

    def log_message(self, format, *args):
        pass

def start_server():
    load_templates()
    port = 80
    server = HTTPServer(("0.0.0.0", port), PortalHandler)
    server.serve_forever()

if __name__ == "__main__":
    start_server()
