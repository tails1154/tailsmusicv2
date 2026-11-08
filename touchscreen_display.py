"""Fullscreen, headset-synchronized TailsMusic touchscreen companion.

The main player retains sole ownership of audio, speech, and menu logic.
This UI only reads shared status and submits familiar headphone actions.
"""
import os
import sys

# SDL2 must be configured before importing any Kivy module.
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
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from touchscreen_state import read, send

BG = (0.035, 0.055, 0.095, 1)
CARD = (0.075, 0.115, 0.18, 1)
CARD_ALT = (0.095, 0.15, 0.225, 1)
ACCENT = (0.36, 0.72, 1, 1)
TEXT = (0.95, 0.97, 1, 1)
MUTED = (0.66, 0.75, 0.86, 1)


class Panel(BoxLayout):
    """A layout with a subtle rounded background."""
    def __init__(self, color=CARD, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*color)
            self.bg_rect = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(18)]
            )
        self.bind(pos=self._update_bg, size=self._update_bg)

    def _update_bg(self, *_args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size


def text_label(value, size=18, color=TEXT, bold=False, **kwargs):
    label = Label(
        text=value, font_size=sp(size), color=color, bold=bold,
        halign="left", valign="middle", **kwargs
    )
    label.bind(size=lambda obj, dimensions: setattr(
        obj, "text_size", (max(0, dimensions[0] - dp(6)), dimensions[1])
    ))
    return label


class TailsMusicDisplay(App):
    title = "TailsMusic v2"

    def __init__(self, parent_pid=None, **kwargs):
        super().__init__(**kwargs)
        self.parent_pid = parent_pid

    def build(self):
        # Fill the entire display in both desktop and direct-console modes.
        Window.fullscreen = "auto"
        Window.clearcolor = BG
        Window.minimum_width = dp(320)
        Window.minimum_height = dp(240)

        self.root_layout = BoxLayout(
            orientation="vertical", spacing=dp(12), padding=dp(16)
        )
        header = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        header.add_widget(text_label(
            "TAILSMUSIC", size=24, color=TEXT, bold=True
        ))
        self.connection = text_label(
            "HEADSET + TOUCH", size=13, color=ACCENT,
            size_hint_x=0.38, halign="right"
        )
        header.add_widget(self.connection)
        self.root_layout.add_widget(header)

        self.content = BoxLayout(spacing=dp(12))
        self.now_panel = Panel(
            orientation="vertical", padding=dp(18), spacing=dp(9)
        )
        self.now_panel.add_widget(text_label(
            "NOW PLAYING", size=14, color=ACCENT, bold=True,
            size_hint_y=None, height=dp(30)
        ))
        self.song = text_label(
            "Waiting for playback...", size=29, bold=True
        )
        self.now_panel.add_widget(self.song)
        self.playback = text_label(
            "Connecting", size=19, color=MUTED,
            size_hint_y=None, height=dp(40)
        )
        self.now_panel.add_widget(self.playback)
        self.content.add_widget(self.now_panel)

        self.menu_panel = Panel(
            color=CARD_ALT, orientation="vertical",
            padding=dp(18), spacing=dp(5)
        )
        self.menu_panel.add_widget(text_label(
            "HEADPHONE MENU", size=14, color=ACCENT, bold=True,
            size_hint_y=None, height=dp(30)
        ))
        self.menu = text_label(
            "Use the headset or touchscreen to navigate.",
            size=19, color=TEXT
        )
        self.menu_panel.add_widget(self.menu)
        self.content.add_widget(self.menu_panel)
        self.root_layout.add_widget(self.content)

        speech_panel = Panel(
            orientation="vertical", padding=[dp(18), dp(9)],
            spacing=dp(2), size_hint_y=None, height=dp(105)
        )
        speech_panel.add_widget(text_label(
            "LAST SPOKEN", size=13, color=ACCENT, bold=True,
            size_hint_y=None, height=dp(25)
        ))
        self.spoken = text_label("Nothing spoken yet", size=18)
        speech_panel.add_widget(self.spoken)
        self.root_layout.add_widget(speech_panel)

        controls = BoxLayout(
            size_hint_y=None, height=dp(74), spacing=dp(10)
        )
        for title, action in (
            ("\u25c0  BACK", "back"),
            ("\u25cf  SELECT", "ok"),
            ("NEXT  \u25b6", "skip"),
        ):
            button = Button(
                text=title, font_size=sp(18), bold=True,
                background_normal="", background_down="",
                background_color=ACCENT if action == "ok" else CARD_ALT,
                color=BG if action == "ok" else TEXT,
            )
            button.bind(on_release=lambda _btn, cmd=action: send(cmd))
            controls.add_widget(button)
        self.root_layout.add_widget(controls)
        self.root_layout.add_widget(text_label(
            "Back / Next: change song or browse menu   |   Select: pause or confirm",
            size=12, color=MUTED, halign="center",
            size_hint_y=None, height=dp(24)
        ))

        Window.bind(size=self._resize)
        self._resize()
        Clock.schedule_interval(self.refresh, 0.25)
        self.refresh(0)
        return self.root_layout

    def _resize(self, *_args):
        # Landscape: split now-playing and menus. Portrait: stack them.
        portrait = Window.width < Window.height
        self.content.orientation = "vertical" if portrait else "horizontal"
        self.song.font_size = sp(24 if portrait else 31)
        self.menu.font_size = sp(17 if portrait else 19)

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
            options = [str(option) for option in menu["options"]]
            if options:
                selected = int(menu.get("selected", 0)) % len(options)
                first = max(0, min(selected - 2, len(options) - 5))
                last = min(len(options), first + 5)
                lines = [
                    (">  " if i == selected else "     ") + options[i]
                    for i in range(first, last)
                ]
                menu_text = "\n".join(lines)
            else:
                menu_text = "No menu options"
        else:
            menu_text = "Use the headset or touchscreen to navigate."
        if self.menu.text != menu_text:
            self.menu.text = menu_text


if __name__ == "__main__":
    raw_parent = os.environ.get("TAILSMUSIC_PARENT_PID")
    TailsMusicDisplay(
        parent_pid=int(raw_parent) if raw_parent else None
    ).run()
