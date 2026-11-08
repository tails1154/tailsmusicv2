#!/usr/bin/env python3
"""Optional, standalone touchscreen frontend for TailsMusic v2.

Uses the same songs directory as the Bluetooth-button player. Run only one
frontend at a time; both use an audio output device independently.
"""
import os
import sys
from pathlib import Path
import random
import subprocess
import time

# Set the video driver *before* importing Kivy or pygame. On Raspberry Pi
# OS Lite, SDL2 can render directly to KMS/DRM without starting X11/Wayland.
# SDL2 has no "fbcon" backend; that name only works with SDL 1.2.
# Respect an existing display session or explicit user overrides.
DIRECT_KMS = (
    sys.platform.startswith("linux")
    and not os.environ.get("DISPLAY")
    and not os.environ.get("WAYLAND_DISPLAY")
    and os.environ.get("SDL_VIDEODRIVER", "kmsdrm") == "kmsdrm"
)
if DIRECT_KMS:
    os.environ.setdefault("SDL_VIDEODRIVER", "kmsdrm")
    os.environ.setdefault("KIVY_WINDOW", "sdl2")

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider

import pygame


ROOT = Path(__file__).resolve().parent
SONGS = ROOT / "songs"
EXTENSIONS = {".mp3", ".ogg", ".wav", ".flac"}

# TEMPORARY preferred headphones. Override with TAILSMUSIC_AUDIO_MAC
# or set it to an empty string to disable automatic Bluetooth routing.
PREFERRED_AUDIO_MAC = os.environ.get("TAILSMUSIC_AUDIO_MAC", "04:57:91:08:28:51")


def _bluetooth_sink(mac):
    """Return the available PulseAudio/PipeWire Bluetooth sink for this MAC."""
    normalized = mac.replace(":", "_").upper()
    try:
        result = subprocess.run(
            ["pactl", "list", "short", "sinks"],
            capture_output=True, text=True, timeout=5, check=True,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) > 1 and fields[1].upper().startswith(
            "BLUEZ_SINK." + normalized
        ):
            return fields[1]
    return None


def configure_audio():
    """Prefer our paired Bluetooth device; keep system output as fallback.

    PULSE_SINK targets only this player's SDL audio stream, without changing
    the system-wide default sink. The audio server must run as this user.
    """
    if "PULSE_SINK" in os.environ or not PREFERRED_AUDIO_MAC:
        return
    # Lite installations sometimes have PulseAudio installed but not started.
    try:
        server = subprocess.run(
            ["pactl", "info"], capture_output=True, timeout=5
        )
        if server.returncode != 0:
            subprocess.run(
                ["pulseaudio", "--start"], capture_output=True, timeout=8,
                check=False,
            )
    except (OSError, subprocess.TimeoutExpired):
        pass

    sink = _bluetooth_sink(PREFERRED_AUDIO_MAC)
    if not sink:
        # The headset is already paired/trusted; try reconnecting on launch.
        try:
            subprocess.run(
                ["bluetoothctl", "connect", PREFERRED_AUDIO_MAC],
                capture_output=True, timeout=12, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
        for _ in range(6):
            sink = _bluetooth_sink(PREFERRED_AUDIO_MAC)
            if sink:
                break
            time.sleep(0.5)

    if sink:
        os.environ["SDL_AUDIODRIVER"] = "pulse"
        os.environ["PULSE_SINK"] = sink
        print(f"TailsMusic: selected Bluetooth audio sink {sink}", flush=True)
    else:
        print(
            "TailsMusic: preferred Bluetooth headset is unavailable; "
            "using system default audio output.", flush=True
        )



def list_songs():
    """Return music files in a predictable order without scanning subdirectories."""
    SONGS.mkdir(parents=True, exist_ok=True)
    return sorted(
        (path for path in SONGS.iterdir()
         if path.is_file() and path.suffix.lower() in EXTENSIONS),
        key=lambda path: path.name.casefold(),
    )


class MusicTouchApp(App):
    title = "TailsMusic v2"

    def build(self):
        if DIRECT_KMS:
            Window.fullscreen = "auto"
        Window.minimum_width = 360
        Window.minimum_height = 300
        self.songs = []
        self.index = -1
        self.paused = False
        self.started = False
        self.shuffle = False
        self.audio_error = ""
        configure_audio()
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
            self.audio_ready = True
        except pygame.error as exc:
            self.audio_ready = False
            self.audio_error = str(exc)

        root = BoxLayout(orientation="vertical", padding=16, spacing=10)
        heading = Label(text="[b]TailsMusic v2[/b]", markup=True, size_hint_y=None, height=45, font_size="24sp")
        root.add_widget(heading)
        self.now_playing = Label(text="No song selected", size_hint_y=None, height=56, shorten=True, shorten_from="center")
        root.add_widget(self.now_playing)
        self.status = Label(text="", size_hint_y=None, height=32, shorten=True)
        root.add_widget(self.status)
        transport = BoxLayout(size_hint_y=None, height=65, spacing=8)
        for title, callback in [
            ("Previous", self.previous), ("Play / Pause", self.toggle),
            ("Next", self.next_song),
        ]:
            button = Button(text=title, font_size="17sp")
            button.bind(on_release=callback)
            transport.add_widget(button)
        root.add_widget(transport)

        settings = BoxLayout(size_hint_y=None, height=52, spacing=8)
        self.shuffle_button = Button(text="Shuffle: Off")
        self.shuffle_button.bind(on_release=self.toggle_shuffle)
        settings.add_widget(self.shuffle_button)
        refresh = Button(text="Refresh songs")
        refresh.bind(on_release=self.refresh)
        settings.add_widget(refresh)
        root.add_widget(settings)

        volume_row = BoxLayout(size_hint_y=None, height=45)
        volume_row.add_widget(Label(text="Volume", size_hint_x=0.25))
        self.volume = Slider(min=0, max=100, value=75)
        self.volume.bind(value=self.set_volume)
        volume_row.add_widget(self.volume)
        root.add_widget(volume_row)

        self.song_list = BoxLayout(orientation="vertical", size_hint_y=None, spacing=4)
        self.song_list.bind(minimum_height=self.song_list.setter("height"))
        scroll = ScrollView()
        scroll.add_widget(self.song_list)
        root.add_widget(scroll)
        if self.audio_ready:
            pygame.mixer.music.set_volume(0.75)
        self.refresh()
        Clock.schedule_interval(self.poll_playback, 0.5)
        return root

    def refresh(self, *_args):
        current = self.songs[self.index] if 0 <= self.index < len(self.songs) else None
        self.songs = list_songs()
        self.index = self.songs.index(current) if current in self.songs else -1
        self.song_list.clear_widgets()
        for idx, path in enumerate(self.songs):
            button = Button(text=path.stem, size_hint_y=None, height=48)
            button.bind(on_release=lambda _button, i=idx: self.play_at(i))
            self.song_list.add_widget(button)
        if not self.audio_ready:
            self.status.text = "Audio unavailable: " + self.audio_error
        else:
            self.status.text = f"{len(self.songs)} song(s) • {SONGS}"
        if not self.songs:
            self.now_playing.text = "No music found. Add songs to the songs directory."
        elif current not in self.songs:
            self.now_playing.text = "Select a song"

    def play_at(self, index):
        if not self.audio_ready or not (0 <= index < len(self.songs)):
            return
        try:
            pygame.mixer.music.load(str(self.songs[index]))
            pygame.mixer.music.play()
        except (pygame.error, OSError) as exc:
            self.started = False
            self.status.text = f"Cannot play: {exc}"
            return
        self.index = index
        self.started = True
        self.paused = False
        self.now_playing.text = self.songs[index].stem
        self.status.text = f"Playing {index + 1} of {len(self.songs)}"

    def next_song(self, *_args):
        if not self.songs:
            return
        if self.shuffle and len(self.songs) > 1:
            choices = [n for n in range(len(self.songs)) if n != self.index]
            next_index = random.choice(choices)
        else:
            next_index = (self.index + 1) % len(self.songs)
        self.play_at(next_index)

    def previous(self, *_args):
        if self.songs:
            self.play_at((self.index - 1) % len(self.songs))

    def toggle(self, *_args):
        if not self.audio_ready:
            return
        if not self.started:
            self.play_at(self.index if self.index >= 0 else 0)
        elif self.paused:
            pygame.mixer.music.unpause()
            self.paused = False
            self.status.text = "Playing"
        else:
            pygame.mixer.music.pause()
            self.paused = True
            self.status.text = "Paused"

    def toggle_shuffle(self, *_args):
        self.shuffle = not self.shuffle
        self.shuffle_button.text = "Shuffle: On" if self.shuffle else "Shuffle: Off"

    def set_volume(self, _slider, value):
        if self.audio_ready:
            pygame.mixer.music.set_volume(value / 100)

    def poll_playback(self, _dt):
        if self.started and not self.paused and self.audio_ready and not pygame.mixer.music.get_busy():
            self.started = False
            self.next_song()

    def on_stop(self):
        if self.audio_ready:
            pygame.mixer.music.stop()
            pygame.mixer.quit()


if __name__ == "__main__":
    MusicTouchApp().run()
