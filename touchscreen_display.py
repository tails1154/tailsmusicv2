"""Integrated optional companion UI launched by player.py.

This process NEVER initializes audio; all touch actions are fed back into the
headset-controlled player's existing evdev menu path.
"""
import os
import sys

# Configure SDL BEFORE Kivy imports its window provider.
# Raspberry Pi OS Lite needs KMS/DRM when running from a local text console.
# Preserve overrides and normal X11/Wayland sessions.
DIRECT_KMS = (
    sys.platform.startswith("linux")
    and not os.environ.get("DISPLAY")
    and not os.environ.get("WAYLAND_DISPLAY")
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

from touchscreen_state import read, send


class TailsMusicDisplay(App):
    title = "TailsMusic v2"

    def __init__(self, parent_pid=None, **kwargs):
        super().__init__(**kwargs)
        self.parent_pid = parent_pid

    def build(self):
        if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            Window.fullscreen = "auto"
        Window.clearcolor = (0.035, 0.045, 0.075, 1)
        root = BoxLayout(orientation="vertical", padding=18, spacing=10)
        root.add_widget(Label(
            text="TAILSMUSIC V2", font_size="24sp", bold=True,
            color=(0.65, 0.82, 1, 1), size_hint_y=0.12,
        ))
        self.song = Label(
            text="Waiting for playback...", font_size="27sp", bold=True,
            halign="center", valign="middle", color=(1, 1, 1, 1),
            size_hint_y=0.23,
        )
        self.song.bind(size=lambda label, size: setattr(label, "text_size", size))
        root.add_widget(self.song)
        self.playback = Label(
            text="Connecting to player", font_size="18sp",
            color=(0.65, 0.82, 1, 1), size_hint_y=0.08,
        )
        root.add_widget(self.playback)
        self.menu = Label(
            text="", font_size="18sp", halign="center", valign="middle",
            color=(0.9, 0.96, 1, 1), size_hint_y=0.22,
        )
        self.menu.bind(size=lambda label, size: setattr(label, "text_size", size))
        root.add_widget(self.menu)
        root.add_widget(Label(
            text="LAST SPOKEN", font_size="16sp", bold=True,
            color=(0.65, 0.82, 1, 1), size_hint_y=0.08,
        ))
        self.spoken = Label(
            text="Nothing spoken yet", font_size="19sp",
            halign="center", valign="middle",
            color=(0.93, 0.93, 0.96, 1), size_hint_y=0.16,
        )
        self.spoken.bind(size=lambda label, size: setattr(label, "text_size", size))
        root.add_widget(self.spoken)

        controls = BoxLayout(size_hint_y=0.11, spacing=8)
        for title, action in (("Back / Prev", "back"), ("Select / Pause", "ok"), ("Next / Skip", "skip")):
            button = Button(text=title, font_size="17sp")
            button.bind(on_release=lambda _button, command=action: send(command))
            controls.add_widget(button)
        root.add_widget(controls)
        Clock.schedule_interval(self.refresh, 0.25)
        self.refresh(0)
        return root

    def refresh(self, _dt):
        if self.parent_pid and os.getppid() != self.parent_pid:
            self.stop()
            return
        state = read()
        song = state.get("song") or "No song selected"
        speech = state.get("spoken_text") or "Nothing spoken yet"
        playback = (state.get("playback") or "stopped").capitalize()
        if self.song.text != song:
            self.song.text = song
        if self.spoken.text != speech:
            self.spoken.text = speech
        if self.playback.text != playback:
            self.playback.text = playback
        menu = state.get("menu")
        if isinstance(menu, dict) and isinstance(menu.get("options"), list):
            options = [str(item) for item in menu["options"]]
            if options:
                selected = int(menu.get("selected", 0)) % len(options)
                start = max(0, selected - 2)
                end = min(len(options), start + 5)
                lines = [
                    ("> " if i == selected else "   ") + options[i]
                    for i in range(start, end)
                ]
                menu_text = "\n".join(lines)
            else:
                menu_text = ""
        else:
            menu_text = "Headset and touchscreen controls are synchronized"
        if self.menu.text != menu_text:
            self.menu.text = menu_text


if __name__ == "__main__":
    parent_pid = os.environ.get("TAILSMUSIC_PARENT_PID")
    TailsMusicDisplay(parent_pid=int(parent_pid) if parent_pid else None).run()
