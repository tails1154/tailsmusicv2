"""Optional companion display for the headset-controlled TailsMusic player.

Launch alongside player.py, not instead of it. No audio engine or buttons are
created here; navigation can be wired to shared menu state in a later version.
"""
import os

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from touchscreen_state import read


class TailsMusicDisplay(App):
    title = "TailsMusic v2 — Companion Display"

    def build(self):
        if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            Window.fullscreen = "auto"
        Window.clearcolor = (0.035, 0.045, 0.075, 1)
        root = BoxLayout(orientation="vertical", padding=22, spacing=12)
        root.add_widget(Label(
            text="TAILSMUSIC V2", font_size="24sp", bold=True,
            color=(0.65, 0.82, 1, 1), size_hint_y=0.18,
        ))
        self.song = Label(
            text="Waiting for playback...", font_size="29sp", bold=True,
            halign="center", valign="middle", shorten=False,
            color=(1, 1, 1, 1),
        )
        self.song.bind(size=lambda label, size: setattr(label, "text_size", size))
        root.add_widget(self.song)
        self.playback = Label(
            text="Connecting to player", font_size="18sp",
            color=(0.65, 0.82, 1, 1), size_hint_y=0.13,
        )
        root.add_widget(self.playback)
        root.add_widget(Label(
            text="LAST SPOKEN", font_size="17sp", bold=True,
            color=(0.65, 0.82, 1, 1), size_hint_y=0.12,
        ))
        self.spoken = Label(
            text="Nothing spoken yet", font_size="21sp",
            halign="center", valign="middle",
            color=(0.93, 0.93, 0.96, 1),
        )
        self.spoken.bind(size=lambda label, size: setattr(label, "text_size", size))
        root.add_widget(self.spoken)
        Clock.schedule_interval(self.refresh, 0.25)
        self.refresh(0)
        return root

    def refresh(self, _dt):
        state = read()
        song = state.get("song") or "No song selected"
        speech = state.get("spoken_text") or "Nothing spoken yet"
        playback = state.get("playback") or "stopped"
        if self.song.text != song:
            self.song.text = song
        if self.spoken.text != speech:
            self.spoken.text = speech
        label = playback.capitalize()
        if self.playback.text != label:
            self.playback.text = label


if __name__ == "__main__":
    TailsMusicDisplay().run()
