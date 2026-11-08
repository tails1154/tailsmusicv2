"""Shared, optional read-only display state for the headless TailsMusic player.

The headset-controlled process owns playback. The touchscreen process only reads
an atomic JSON snapshot; it must never initialize pygame's audio mixer.
"""
import json
import os
import tempfile
import threading
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent / ".touchscreen_status.json"
_lock = threading.Lock()
_state = {
    "song": "",
    "spoken_text": "",
    "playback": "stopped",
    "menu": None,  # Reserved for synchronized navigation later.
}


def publish(*, song=None, spoken_text=None, playback=None):
    """Update selected fields and atomically replace the status snapshot."""
    with _lock:
        if song is not None:
            _state["song"] = str(song)
        if spoken_text is not None:
            _state["spoken_text"] = str(spoken_text)
        if playback is not None:
            _state["playback"] = str(playback)
        fd = None
        tmp = None
        try:
            fd, tmp = tempfile.mkstemp(prefix=".touchscreen-", dir=STATE_PATH.parent)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                fd = None
                json.dump(_state, stream, ensure_ascii=False)
                stream.write("\n")
            os.replace(tmp, STATE_PATH)
        finally:
            if fd is not None:
                os.close(fd)
            if tmp is not None and os.path.exists(tmp):
                os.unlink(tmp)


def read():
    """Read the latest complete snapshot, or safe defaults if unavailable."""
    try:
        with STATE_PATH.open(encoding="utf-8") as stream:
            value = json.load(stream)
        if isinstance(value, dict):
            return {key: value.get(key, fallback) for key, fallback in _state.items()}
    except (OSError, ValueError, TypeError):
        pass
    return dict(_state)
