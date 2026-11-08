"""Local IPC for the optional TailsMusic companion touchscreen.

The player owns all playback and menus. The Kivy child reads its status and
submits button presses to the player's normal evdev navigation path.
"""
import json
import os
import tempfile
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE_PATH = ROOT / ".touchscreen_status.json"
COMMAND_DIR = ROOT / ".touchscreen_commands"
_lock = threading.Lock()
_state = {
    "song": "",
    "spoken_text": "",
    "playback": "stopped",
    "menu": None,
}


def publish(*, song=None, spoken_text=None, playback=None, menu=Ellipsis):
    """Atomically update the display snapshot without erasing unrelated fields."""
    with _lock:
        if song is not None:
            _state["song"] = str(song)
        if spoken_text is not None:
            _state["spoken_text"] = str(spoken_text)
        if playback is not None:
            _state["playback"] = str(playback)
        if menu is not Ellipsis:
            _state["menu"] = menu
        fd, tmp = tempfile.mkstemp(prefix=".touchscreen-", dir=ROOT)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(_state, stream, ensure_ascii=False)
                stream.write("\n")
            os.replace(tmp, STATE_PATH)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)


def read():
    """Return the latest complete snapshot or offline defaults."""
    try:
        with STATE_PATH.open(encoding="utf-8") as stream:
            value = json.load(stream)
        if isinstance(value, dict):
            return {key: value.get(key, fallback) for key, fallback in _state.items()}
    except (OSError, ValueError, TypeError):
        pass
    return dict(_state)


def send(action):
    """Submit a synthetic headphone button action from the touchscreen process."""
    if action not in ("back", "skip", "ok", "playlists"):
        raise ValueError("Unknown touchscreen action")
    COMMAND_DIR.mkdir(mode=0o700, exist_ok=True)
    name = f"{time.time_ns():020d}-{uuid.uuid4().hex}.cmd"
    fd, tmp = tempfile.mkstemp(prefix=".pending-", dir=COMMAND_DIR)
    try:
        with os.fdopen(fd, "w", encoding="ascii") as stream:
            stream.write(action)
        os.replace(tmp, COMMAND_DIR / name)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def next_command():
    """Read one pending input; called only from the owner's player loop."""
    if not COMMAND_DIR.exists():
        return None
    for path in sorted(COMMAND_DIR.glob("*.cmd"))[:1]:
        try:
            action = path.read_text(encoding="ascii").strip()
            path.unlink(missing_ok=True)
            if action in ("back", "skip", "ok"):
                return action
        except OSError:
            return None
    return None


def clear_commands():
    """Prevent old taps from affecting a newly started player."""
    COMMAND_DIR.mkdir(mode=0o700, exist_ok=True)
    for path in COMMAND_DIR.glob("*.cmd"):
        path.unlink(missing_ok=True)
