#!/bin/python3
print("TailsMusic preinit")
print("Loading Modules")
#print("This is a different line")
totalModules = 10
global shuffleOn
print(f"(0/{totalModules}) os")
import os
import sys
import errno
from pathlib import Path
import tempfile
import importlib.util

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / 'config.json'
MUSIC_DIR = ROOT / 'songs'
PLAYLIST_DIR = ROOT / 'playlists'
SFX_DIR = ROOT / 'sfx'
APP_PATH = ROOT / 'app.py'
print(f"(1/{totalModules}) pygame")
import pygame
print(f"(2/{totalModules}) evdev")
from evdev import InputDevice, InputEvent, categorize, ecodes, list_devices
print("(3/10) time")
from time import sleep
import time
print(f"(4/{totalModules}) threading")
import threading
print(f"(5/{totalModules}) subprocess")
import subprocess
print(f"(6/{totalModules}) json")
import json
print(f"(7/{totalModules}) random")
import random
print(f"(8/{totalModules}) wifi.py")
import wifi
print("(8.5/10) hotspot.py")
import hotspot
print(f"(9/{totalModules}) traceback")
import traceback
print(f"(10/{totalModules}) queue")
import queue
import requests

# The optional touchscreen is a status consumer, not a second audio player.
from touchscreen_state import (
    publish as publish_touchscreen,
    next_command as next_touch_command,
    clear_commands as clear_touch_commands,
)

print(f"(11/{totalModules}) pulsectl")
try:
    from pulsectl import Pulse
    _HAS_PULSECTL = True
except Exception:
    _HAS_PULSECTL = False
    Pulse = None
try:
    from bleak import BleakScanner
    _HAS_BLEAK = True
except Exception:
    _HAS_BLEAK = False
    BleakScanner = None
    print("Optional Bluetooth LE scanning is unavailable; install bleak in the venv.")
def _fatal_thread_exception(args):
    """Restart the process on unhandled worker-thread exceptions."""
    if args.exc_type is SystemExit:
        return
    traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback)
    sys.stderr.flush()
    os._exit(1)


threading.excepthook = _fatal_thread_exception
print("TailsMusic Loading...")
global daemonRunning
daemonRunning = False


def _is_alsa_underrun(line: str) -> bool:
    """Return True for ALSA/PCM underrun messages emitted by native code."""
    message = line.lower()
    return "underrun" in message and ("alsa" in message or "pcm" in message)


def _monitor_alsa_stderr(read_fd: int, output_fd: int) -> None:
    """Mirror native audio errors without restarting the player."""
    try:
        with os.fdopen(read_fd, "r", encoding="utf-8", errors="replace") as stream:
            for line in stream:
                try:
                    os.write(output_fd, line.encode("utf-8", errors="replace"))
                except OSError:
                    pass
                if _is_alsa_underrun(line):
                    try:
                        os.write(
                            output_fd,
                            b"TailsMusic: ALSA underrun detected; automatic restart disabled.\n",
                        )
                    except OSError:
                        pass
    except (OSError, ValueError):
        pass


def install_alsa_underrun_monitor() -> None:
    """Capture native stderr output while keeping it visible to the console."""
    output_fd = os.dup(2)
    read_fd, write_fd = os.pipe()
    os.dup2(write_fd, 2)
    os.close(write_fd)
    threading.Thread(
        target=_monitor_alsa_stderr,
        args=(read_fd, output_fd),
        daemon=True,
        name="AlsaUnderrunMonitor",
    ).start()


install_alsa_underrun_monitor()
print("multiprocessing")
import multiprocessing
print("queue")
print("what is typing")
from typing import Optional
print("nice")
print("Loading config.json")
with CONFIG_PATH.open('r', encoding='utf-8') as file:
 config = json.load(file)
print(f"okbutton: {config['okbutton']}")
print(f"okbutton2: {config['okbutton2']}")
print(f"skipbutton: {config['skipbutton']}")
print(f"backbutton: {config['backbutton']}")
print(f"evtestname: {config['evtestname']}")

# --- Menu navigation helper ---
def menu_nav(event, selected, options, allowInterrupt: bool = False):
    """
    Handle menu navigation: back cycles BACK, skip cycles FORWARD, play/pause (okbutton/okbutton2) selects.
    Returns tuple (selected, selected_action) where selected_action is True if play/pause was pressed.
    """
    publish_touchscreen(menu={"options": list(options), "selected": selected})
    key_event = categorize(event)
    if key_event.keystate == 1:
        key = key_event.keycode
        if key == config['backbutton']:
            selected = (selected - 1) % len(options)
            if allowInterrupt:
                speak_menu_option(options, selected, allow_interrupt=True)
            else:
                speak_menu_option(options, selected)
        elif key == config['skipbutton']:
            selected = (selected + 1) % len(options)
            if allowInterrupt:
                speak_menu_option(options, selected, allow_interrupt=True)
            else:
                speak_menu_option(options, selected)
        elif key in [config['okbutton'], config['okbutton2']]:
            return selected, True
    return selected, False


class CommandQueue:
    def __init__(self, maxsize: int = 100, verbose: bool = True, 
                 enable_multiprocessing: bool = False):
        """
        Initialize the command queue system with multiprocessing support.
        
        Args:
            maxsize: Maximum number of queued commands
            verbose: Whether to print execution details
            enable_multiprocessing: Enable inter-process communication
        """
        self.enable_multiprocessing = enable_multiprocessing
        
        if enable_multiprocessing:
            # line 67
            self.manager = multiprocessing.Manager()
            self.queue = self.manager.Queue(maxsize=maxsize) #line 69, nice
            self.lock = self.manager.Lock()
        else:
            self.queue = queue.Queue(maxsize=maxsize)
            self.lock = threading.Lock()
            
        self.running = False
        self.verbose = verbose
        self.listener_thread: Optional[threading.Thread] = None
        self.process: Optional[multiprocessing.Process] = None

    def start_command_listener(self) -> None:
        """Start the background command listener thread."""
        if self.running:
            return
            
        self.running = True
        self.listener_thread = threading.Thread(
            target=self._command_listener,
            daemon=True,
            name="CommandListener"
        )
        self.listener_thread.start()
        
        if self.verbose:
            print("Command queue listener started")

    def start_remote_processor(self) -> None:
        """Start a separate process to handle command execution."""
        if not self.enable_multiprocessing:
            raise RuntimeError("Multiprocessing not enabled in constructor")
            
        self.process = multiprocessing.Process(
            target=self._remote_command_processor,
            daemon=True
        )
        self.process.start()
        
        if self.verbose:
            print("Remote command processor started")

    def _remote_command_processor(self) -> None:
        """Process commands in a separate process."""
        while True:
            try:
                cmd = self.queue.get(timeout=1)
                self._execute_command(cmd)
            except queue.Empty:
                if not self.running:
                    break
            except Exception as e:
                raise
    def stop(self) -> None:
        """Stop all components of the command queue."""
        with self.lock:
            self.running = False
            if self.listener_thread:
                self.listener_thread.join(timeout=1.0)
            if self.process:
                self.process.join(timeout=1.0)
            if self.enable_multiprocessing:
                self.manager.shutdown()

    def _command_listener(self) -> None:
        """Background thread that listens for console input."""
        # note to self: what is the point of this??
        while self.running:
            try:
                cmd = input(">>> " if sys.stdin.isatty() else "").strip()
                if cmd:
                    self.put_command(cmd)
            except (EOFError, KeyboardInterrupt):
                break
            except Exception as e:
                raise
    def process_Command(self, timeout: float = 0.01) -> None:
        """
        Process pending commands in the queue (in current process).
        
        Args:
            timeout: Maximum time to wait for a command (seconds)
        """
        while True:
            try:
                cmd = self.queue.get_nowait() if timeout == 0 else self.queue.get(timeout=timeout)
                self._execute_command(cmd)
                self.queue.task_done()
            except queue.Empty:
                break
            except Exception as e:
                raise
    def _execute_command(self, cmd: str) -> None:
        """Execute a single command with proper error handling."""
        if self.verbose:
            print(f"[CMD] Executing: {cmd}")
            
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30  # Prevent hanging commands
            )
            
            if self.verbose:
                if result.stdout:
                    print(f"[CMD] Output:\n{result.stdout}")
                if result.stderr:
                    print(f"[CMD] Errors:\n{result.stderr}", file=sys.stderr)
                    
        except subprocess.TimeoutExpired:
            raise
        except subprocess.CalledProcessError as e:
            raise
        except Exception as e:
            raise
    def put_command(self, cmd: str, block: bool = True, 
                    timeout: Optional[float] = None) -> bool:
        """
        Safely add a command to the queue from external sources.
        
        Returns:
            bool: True if command was successfully queued
        """
        try:
            with self.lock:
                self.queue.put(cmd, block=block, timeout=timeout)
            return True
        except queue.Full:
            if self.verbose:
                print(f"[CMD] Queue full, could not add command: {cmd}")
            return False

    def __enter__(self):
        """Context manager entry point."""
        self.start_command_listener()
        if self.enable_multiprocessing:
            self.start_remote_processor()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point."""
        self.stop()


def find_simolio():
    """Find only the explicitly configured input device."""
    match = config.get("evtestname", "").strip()
    if not match:
        print("Set evtestname in config.json to part of your headset's evdev name.")
        return None
    for path in list_devices():
        try:
            device = InputDevice(path)
            name = device.name or ""
            device.close()
            if match.casefold() in name.casefold():
                return path
        except (OSError, PermissionError):
            continue
    return None

def read_input_event():
    """Exit the player if its Bluetooth media-button input device disappears.

    os._exit() bypasses Python exception handlers and shutdown cleanup, so
    a stale evdev device cannot leave the process running without controls.
    Exit code 19 lets
    the console launcher or a service supervisor restart the player.
    """
    try:
        event = dev.read_one()
        if event is not None:
            if event.type == ecodes.EV_KEY:
                key_event = categorize(event)
                if key_event.keystate == 1:
                    publish_touchscreen(activity=True)
            return event
        if config.get("turn_off_kivy", False) is not True:
            action = next_touch_command()
            if action:
                publish_touchscreen(activity=True)
                setting = {"back": "backbutton", "skip": "skipbutton", "ok": "okbutton"}[action]
                code = ecodes.ecodes.get(config[setting])
                if isinstance(code, int):
                    return InputEvent(0, 0, ecodes.EV_KEY, code, 1)
        return None
    except OSError as exc:
        if exc.errno == errno.ENODEV:
            print(
                "TailsMusic: input device disappeared (ENODEV, errno 19); "
                "exiting for supervisor restart.",
                file=sys.stderr,
                flush=True,
            )
            os._exit(errno.ENODEV)  # Immediate exit; supervisor restarts us.
        raise


def bluetooth_recording_devices():
    """Discover Bluetooth audio card and input source from PulseAudio."""
    try:
        cards = subprocess.run(["pactl", "list", "short", "cards"],
                               capture_output=True, text=True, check=True).stdout
        card = next((line.split("\t")[1] for line in cards.splitlines()
                     if len(line.split("\t")) >= 2 and
                     line.split("\t")[1].startswith("bluez_card.")), None)
        sources = subprocess.run(["pactl", "list", "short", "sources"],
                                capture_output=True, text=True, check=True).stdout
        mic = next((line.split("\t")[1] for line in sources.splitlines()
                    if len(line.split("\t")) >= 2 and
                    line.split("\t")[1].startswith(("bluez_source.", "bluez_input."))), None)
        return card, mic
    except (OSError, subprocess.CalledProcessError):
        return None, None

_speech_process = None
_speech_lock = threading.RLock()


def _stop_own_speech():
    """Interrupt our current voice and always collect its exit status."""
    global _speech_process
    with _speech_lock:
        process = _speech_process
        _speech_process = None
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        else:
            process.wait()


def _reap_own_speech(process):
    """Wait for natural completion, even if no next speech is requested."""
    process.wait()
    global _speech_process
    with _speech_lock:
        if _speech_process is process:
            _speech_process = None


def speak_nointer(text):
    publish_touchscreen(spoken_text=text)
    print(f"TTS: {text}")
    _stop_own_speech()
    subprocess.run(["espeak-ng", "-s", "130", text], check=True)


def speak(text):
    global _speech_process
    publish_touchscreen(spoken_text=text)
    with _speech_lock:
        _stop_own_speech()
        process = subprocess.Popen(["espeak-ng", "-s", "130", text])
        _speech_process = process
        threading.Thread(
            target=_reap_own_speech, args=(process,),
            name="TailsMusicSpeechReaper", daemon=True,
        ).start()

def speak_allowinter(text):
    speak(text)


def speak_menu_option(options, selected, allow_interrupt=False):
    """Keep headset narration and on-screen menu selections in sync."""
    publish_touchscreen(menu={"options": [str(item) for item in options], "selected": selected})
    if allow_interrupt:
        speak_allowinter(str(options[selected]))
    else:
        speak(str(options[selected]))

def start_optional_touchscreen():
    """Launch the UI child when enabled, installed, and a display is present."""
    if config.get("turn_off_kivy", False) is True:
        print("TailsMusic: integrated touchscreen disabled by config.")
        return None
    if importlib.util.find_spec("kivy") is None:
        print("TailsMusic: Kivy not installed; continuing headless.")
        return None
    graphical_session = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    # DRM devices alone do not grant a systemd user service access to the
    # active virtual terminal. In console mode SDL2/kmsdrm needs a local VT.
    local_console = False
    if not graphical_session:
        try:
            local_console = os.isatty(0) and os.ttyname(0).startswith("/dev/tty")
        except OSError:
            local_console = False
    if not graphical_session and not local_console:
        print(
            "TailsMusic: Kivy needs a graphical session or local active TTY; "
            "service has neither, continuing headless.",
            flush=True,
        )
        return None
    if not graphical_session and not Path("/dev/dri").exists():
        print("TailsMusic: no DRM device for KMS display; continuing headless.", flush=True)
        return None
    try:
        child_env = os.environ.copy()
        child_env["TAILSMUSIC_PARENT_PID"] = str(os.getpid())
        return subprocess.Popen([
            sys.executable, str(ROOT / "touchscreen_display.py"),
        ], cwd=str(ROOT), env=child_env)
    except OSError:
        print("TailsMusic: touchscreen launch failed; restarting through supervisor.", file=sys.stderr)
        raise


def update_tailsign(status=None):
    """Publish playback status, and optionally update the external TailSign."""
    if playlist:
        publish_touchscreen(
            song=Path(playlist[index]).stem,
            playback="paused" if status == "paused" else ("stopped" if status == "stopped" else "playing"),
        )
    if not config.get("show_on_tailsign", False):
        return
    try:
        if status == "paused":
            text = "[TailsMusic] Paused"
        elif status:
            text = "[TailsMusic] " + str(status)
        else:
            song_name = os.path.basename(playlist[index])
            if song_name.endswith(".mp3"):
                song_name = song_name[:-4]
            text = "[TailsMusic] " + song_name
        requests.post("http://127.0.0.1:1998/postsign", data={"text": text}, timeout=2)
    except Exception:
        raise
def rescan_songs():
    """Refresh the MP3 list without restarting the player or interrupting playback."""
    global playlist, index
    new_playlist = sorted(
        str(path) for path in MUSIC_DIR.iterdir()
        if path.is_file() and path.suffix.lower() == ".mp3"
    )
    if not new_playlist:
        print("Rescan: no MP3 files found; keeping the current playlist.", flush=True)
        speak("No songs found")
        return

    current_song = playlist[index] if playlist and index < len(playlist) else None
    old_count = len(playlist)
    playlist = new_playlist
    if current_song in playlist:
        index = playlist.index(current_song)
        print(f"Rescan: {old_count} -> {len(playlist)} songs; current song preserved.", flush=True)
    else:
        # The playing file was removed or renamed. Load an available song.
        index = 0
        pygame.mixer.music.load(playlist[index])
        if not paused:
            pygame.mixer.music.play()
        update_tailsign()
        print(f"Rescan: {old_count} -> {len(playlist)} songs; selected first song.", flush=True)
    speak(f"Found {len(playlist)} songs")


def next_song():
    global index
    index += 1
    if index >= len(playlist):
        index = 0
    pygame.mixer.music.load(playlist[index])
    pygame.mixer.music.play()
    update_tailsign()

def prev_song():
    global index
    index = (index - 1) % len(playlist)
    pygame.mixer.music.load(playlist[index])
    pygame.mixer.music.play()
    update_tailsign()

def toggle_pause():
    global paused
    if paused:
        pausesfx.play()
        time.sleep(pausesfx.get_length())
        pygame.mixer.music.unpause()
        update_tailsign()
    else:
        pausesfx.play()
        pygame.mixer.music.pause()
        update_tailsign("paused")
    paused = not paused

def manual_tts():
    options = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "space", "Done"]
    selected = 0
    speak_menu_option(options, selected)
    toSpeak = ""
    while True:
        if daemonRunning: cmdq.process_Command()
        event = read_input_event()
        if event and event.type == ecodes.EV_KEY:
            selected, action = menu_nav(event, selected, options)
            if action:
                choice = options[selected]
                click.play()
                if choice == "space":
                    toSpeak += " "
                elif choice == "Done":
                    speak(toSpeak)
                    break
                else:
                    toSpeak += choice

def wifiSetup():
    speak("Loading wifi networks")
    pygame.mixer.music.load(str(SFX_DIR / "dialup.mp3"))
    pygame.mixer.music.play()
    networks = wifi.scan_wifi()
    if networks:
        options = [ssid for ssid, signal in networks]
        pygame.mixer.music.stop()
        selected = 0
        speak("Choose your wifi network")
        speak_menu_option(options, selected)
        while True:
            if daemonRunning: cmdq.process_Command()
            event = read_input_event()
            if event and event.type == ecodes.EV_KEY:
                selected, action = menu_nav(event, selected, options)
                if action:
                    click.play()
                    wifiName = options[selected]
                    pygame.mixer.music.load(str(SFX_DIR / "dialup.mp3"))
                    speak("Enter your wifi password.")
                    speak("For an easier setup, Connect TailsMusic to Your monitor and type")
                    speak("n... m... t... u... i... with a keyboard and press enter.")
                    speak("Enter your wifi password")
                    options = [
                        "a", "b", "c", "d", "e", "f", "g", "h", "i", "j",
                        "k", "l", "m", "n", "o", "p", "q", "r", "s", "t",
                        "u", "v", "w", "x", "y", "z",
                        "A", "B", "C", "D", "E", "F", "G", "H", "I", "J",
                        "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
                        "U", "V", "W", "X", "Y", "Z",
                        "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
                        "!", "@", "#", "$", "%", "^", "&", "*", "(", ")",
                        "-", "_", "=", "+", "[", "{", "]", "}", "\\", "|",
                        ";", ":", "'", "\"", ",", "<", ".", ">", "/", "?", "`", "~", "space", "Done"
                    ]
                    selected = 0
                    wifiPass = ""
                    speak_menu_option(options, selected)
                    while True:
                        if daemonRunning: cmdq.process_Command()
                        event = read_input_event()
                        if event and event.type == ecodes.EV_KEY:
                            selected, action = menu_nav(event, selected, options)
                            if action:
                                click.play()
                                choice = options[selected]
                                if choice == "space":
                                    wifiPass += ""
                                elif choice == "Done":
                                    speak("Connecting")
                                    pygame.mixer.music.play()
                                    try:
                                        wifi.connect_wifi(wifiName, wifiPass)
                                    except Exception as e:
                                        raise
                                    pygame.mixer.music.stop()
                                    speak("Your IP is " + str(wifi.get_ip()))
                                    break
                                else:
                                    wifiPass += options[selected]
                    break

def list_pulse_sinks():
    """Return list of PulseAudio sinks as (index, name, desc)."""
    if not _HAS_PULSECTL:
        return []
    try:
        with Pulse('tailsmusic') as p:
            return [(s.index, s.name, s.description) for s in p.sink_list()]
    except Exception as e:
        raise
def set_default_sink_by_name(sink_name: str) -> bool:
    """Set default sink and move existing sink inputs to it."""
    if not _HAS_PULSECTL:
        print("pulsectl not available")
        return False
    try:
        with Pulse('tailsmusic') as p:
            sinks = {s.name: s for s in p.sink_list()}
            if sink_name not in sinks:
                print("Sink not found:", sink_name)
                return False
            p.sink_default_set(sinks[sink_name])
            # Move any active streams to the sink
            for si in p.sink_input_list():
                try:
                    p.sink_input_move(si.index, sinks[sink_name].index)
                except Exception:
                    raise
        return True
    except Exception as e:
        raise
def bluetooth_list_devices():
    """Return list of known bluetooth devices using bluetoothctl."""
    try:
        out = subprocess.check_output(['bluetoothctl', 'devices'], text=True)
        devices = []
        for line in out.splitlines():
            # format: Device XX:XX:XX:XX:XX:XX Name
            parts = line.split(' ', 2)
            if len(parts) >= 3 and parts[0] == 'Device':
                mac = parts[1]
                name = parts[2]
                devices.append((mac, name))
        return devices
    except Exception as e:
        raise
def bluetooth_scan(timeout=5):
    """Scan for bluetooth devices for `timeout` seconds and return devices."""
    # Prefer BLE scan with bleak if available
    if _HAS_BLEAK:
        try:
            devices = []
            results = BleakScanner.discover(timeout=timeout)
            for d in results:
                name = d.name or d.metadata.get('local_name') if getattr(d, 'metadata', None) else d.name
                devices.append((d.address, name or ''))
            if devices:
                return devices
        except Exception as e:
            raise
    # Fallback to bluetoothctl interactive scan for non-BLE or if bleak is unavailable
    try:
        p = subprocess.Popen(['bluetoothctl'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            p.stdin.write('scan on\n')
            p.stdin.flush()
            sleep(timeout)
            p.stdin.write('scan off\n')
            p.stdin.write('devices\n')
            p.stdin.write('exit\n')
            out, _err = p.communicate(timeout=timeout + 5)
        except subprocess.TimeoutExpired:
            p.kill()
            out, _err = p.communicate()
        devices = []
        for line in out.splitlines():
            if 'Device' in line:
                parts = line.split()
                try:
                    i = parts.index('Device')
                    mac = parts[i+1]
                    name = ' '.join(parts[i+2:]) if len(parts) > i+2 else ''
                    devices.append((mac, name))
                except Exception:
                    raise
        if not devices:
            return bluetooth_list_devices()
        return devices
    except Exception as e:
        raise
def bluetooth_pair_connect(mac: str) -> bool:
    """Attempt to pair, trust, and connect to a device via bluetoothctl."""
    try:
        subprocess.run(['bluetoothctl', 'pair', mac], check=False)
        subprocess.run(['bluetoothctl', 'trust', mac], check=False)
        res = subprocess.run(['bluetoothctl', 'connect', mac], check=False)
        return res.returncode == 0
    except Exception as e:
        raise
def bluetooth_menu():
    """UI menu (button-driven) for scanning, pairing and selecting a Bluetooth speaker sink."""
    options = ["Scan Devices", "Known Devices", "List Audio Sinks", "Back"]
    selected = 0
    speak_menu_option(options, selected)
    while True:
        if daemonRunning: cmdq.process_Command()
        event = read_input_event()
        if event and event.type == ecodes.EV_KEY:
            selected, action = menu_nav(event, selected, options)
            if action:
                click.play()
                choice = options[selected]
                if choice == "Back":
                    pausesfx.play()
                    return
                elif choice == "Scan Devices":
                    speak("Scanning for Bluetooth devices")
                    devices = bluetooth_scan(timeout=6)
                    if not devices:
                        speak("No devices found")
                        continue
                    dev_opts = [f"{n} ({m})" for m, n in devices]
                    dev_opts.append("Back")
                    sel = 0
                    speak_allowinter(dev_opts[sel])
                    while True:
                        if daemonRunning: cmdq.process_Command()
                        e = read_input_event()
                        if e and e.type == ecodes.EV_KEY:
                            sel, act = menu_nav(e, sel, dev_opts, allowInterrupt=True)
                            if act:
                                click.play()
                                if dev_opts[sel] == "Back":
                                    break
                                chosen_mac = devices[sel][0]
                                chosen_name = devices[sel][1]
                                speak(f"Pairing with {chosen_name}")
                                ok = bluetooth_pair_connect(chosen_mac)
                                if ok:
                                    speak("Connected")
                                    # attempt to set pulse sink matching device
                                    sinks = list_pulse_sinks()
                                    # try to find sink with MAC in name
                                    target = None
                                    for idx, name, desc in sinks:
                                        if chosen_mac.replace(':', '_') in name or chosen_name in desc or chosen_name in name:
                                            target = name
                                            break
                                    if target:
                                        set_default_sink_by_name(target)
                                        speak("Audio routed to speaker")
                                    else:
                                        speak("Speaker found but could not route audio automatically")
                                else:
                                    speak("Failed to connect to device")
                                break
                elif choice == "Known Devices":
                    devices = bluetooth_list_devices()
                    if not devices:
                        speak("No known devices")
                        continue
                    dev_opts = [f"{n} ({m})" for m, n in devices]
                    dev_opts.append("Back")
                    sel = 0
                    speak_allowinter(dev_opts[sel])
                    while True:
                        if daemonRunning: cmdq.process_Command()
                        e = read_input_event()
                        if e and e.type == ecodes.EV_KEY:
                            sel, act = menu_nav(e, sel, dev_opts, allowInterrupt=True)
                            if act:
                                click.play()
                                if dev_opts[sel] == "Back":
                                    break
                                chosen_mac = devices[sel][0]
                                chosen_name = devices[sel][1]
                                speak(f"Connecting to {chosen_name}")
                                ok = bluetooth_pair_connect(chosen_mac)
                                if ok:
                                    speak("Connected")
                                else:
                                    speak("Failed to connect")
                                break
                elif choice == "List Audio Sinks":
                    sinks = list_pulse_sinks()
                    if not sinks:
                        speak("No audio sinks available")
                        continue
                    sink_opts = [f"{name} - {desc}" for idx, name, desc in sinks]
                    sink_opts.append("Back")
                    sel = 0
                    speak_allowinter(sink_opts[sel])
                    while True:
                        if daemonRunning: cmdq.process_Command()
                        e = read_input_event()
                        if e and e.type == ecodes.EV_KEY:
                            sel, act = menu_nav(e, sel, sink_opts, True)
                            if act:
                                click.play()
                                if sink_opts[sel] == "Back":
                                    break
                                chosen = sinks[sel]
                                ok = set_default_sink_by_name(chosen[1])
                                if ok:
                                    speak("Audio routed to device")
                                else:
                                    speak("Failed to set sink")
                                break

def run_script_menu():
    py_files = []
    apps_dir = str(ROOT / 'apps')
    if os.path.exists(apps_dir):
        py_files = [os.path.join(root, f) 
                   for root, _, files in os.walk(apps_dir) 
                   for f in files if f.endswith('.py')]
    if not py_files:
        speak("No scripts found in apps directory")
        return
    options = [os.path.basename(f) for f in py_files] + ["Back"]
    selected = 0
    speak_menu_option(options, selected)
    while True:
        global daemonRunning
        if daemonRunning: cmdq.process_Command()
        event = read_input_event()
        if event and event.type == ecodes.EV_KEY:
            selected, action = menu_nav(event, selected, options)
            if action:
                click.play()
                if options[selected] == "Back":
                    return
                else:
                    speak(f"Running {options[selected]}")
                    selected_script = next((p for p in py_files if os.path.basename(p) == options[selected]), None)
                    if selected_script is None:
                        speak("Script not found")
                        return
                    spec = importlib.util.spec_from_file_location("tailsmusic_selected_app", selected_script)
                    if spec is None or spec.loader is None:
                        speak("Cannot load selected script")
                        return
                    app_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(app_module)
                    app = app_module.APP(dev, cmdq)
                    if app.checkDaemon():
                        speak("App is a daemon. Running in background")
                        thread = multiprocessing.Process(target=app.start)
                        thread.start()
                        daemonRunning = True
                    else:
                        app.start()
                        speak("Script finished")
                    return

def portal_setup():
    speak("Starting setup hotspot")
    msg = hotspot.start()
    print(msg)
    if not hotspot.is_running():
        speak("Hotspot failed. Check terminal logs and NetworkManager permissions.")
        return
    speak("Hotspot started. Connect using the configured WiFi password.")
    speak(msg)
    options = ["Stop Hotspot", "Back"]
    selected = 0
    speak_menu_option(options, selected)
    while True:
        if daemonRunning: cmdq.process_Command()
        event = read_input_event()
        if event and event.type == ecodes.EV_KEY:
            selected, action = menu_nav(event, selected, options)
            if action:
                click.play()
                if options[selected] == "Stop Hotspot":
                    speak("Stopping hotspot")
                    hotspot.stop()
                    speak("Hotspot stopped")
                    pausesfx.play()
                    return
                elif options[selected] == "Back":
                    return

def shutdown_menu():
    selected = 0
    first_render = True
    while True:
        tailsign_status = "On" if config.get("show_on_tailsign", False) else "Off"
        options = ["Playlists", "Random Song", "Update TailsMusic", "Shuffle", "Re scan Songs", 
                   "Connect to WiFi", "Setup Hotspot", "Bluetooth", "Get local IP", "Open App", 
                   f"Show on TailSign: {tailsign_status}", "AI Mode", "Shut Down", "Back"]
        if first_render:
            speak_menu_option(options, selected)
            first_render = False
        if daemonRunning: cmdq.process_Command()
        event = read_input_event()
        if event and event.type == ecodes.EV_KEY:
            selected, action = menu_nav(event, selected, options)
            if action:
                click.play()
                choice = options[selected]
                if choice and choice.startswith("Show on TailSign"):
                    current = config.get("show_on_tailsign", False)
                    config["show_on_tailsign"] = not current
                    with CONFIG_PATH.open("w", encoding="utf-8") as cfg_f:
                        json.dump(config, cfg_f, indent=4)
                    speak("Show on TailSign " + ("enabled" if not current else "disabled"))
                elif choice == "Shut Down":
                    speak("Confirm shutdown?")
                    confirm_opts = ["Cancel", "Shut Down"]
                    conf_sel = 0
                    while True:
                        if daemonRunning: cmdq.process_Command()
                        event = read_input_event()
                        if event and event.type == ecodes.EV_KEY:
                            conf_sel, confirmed = menu_nav(event, conf_sel, confirm_opts)
                            if confirmed:
                                click.play()
                                if confirm_opts[conf_sel] == "Shut Down":
                                    speak("Shutting down")
                                    subprocess.run(["sudo", "shutdown", "now"])
                                break
                elif choice == "Back":
                    pausesfx.play()
                    return
                elif choice == "Playlists":
                    playlist_menu()
                elif choice == "Random Song":
                    song_files = sorted([f for f in os.listdir(MUSIC_DIR) if f.endswith('.mp3')], key=str.lower)
                    random_song = random.choice(song_files) if song_files else None
                    pygame.mixer.music.load(str(MUSIC_DIR / random_song))
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        event = read_input_event()
                        if event and event.type == ecodes.EV_KEY:
                            selected2, action2 = menu_nav(event, 0, ["Stop"])
                            print(selected2) # there ruff now i used selected2 are you happy
                            if action2 and options[0] == "Stop":
                                pygame.mixer.music.stop()
                                break
                elif choice == "Shuffle":
                    shuffleOn = True
                    while shuffleOn:
                        song_files = sorted([f for f in os.listdir(MUSIC_DIR) if f.endswith('.mp3')], key=str.lower)
                        random_song = random.choice(song_files) if song_files else None
                        pygame.mixer.music.load(os.path.join(MUSIC_DIR, random_song))
                        pygame.mixer.music.play()
                        while pygame.mixer.music.get_busy():
                            event = read_input_event()
                            if event and event.type == ecodes.EV_KEY:
                                key_event = categorize(event)
                                key = key_event.keycode
                                if key_event.keystate == 1:
                                    if key == config["backbutton"]:
                                        pygame.mixer.music.stop()
                                        speak("Exiting shuffle")
                                        shuffleOn = False
                                        break
                                    if key == config["skipbutton"]:
                                        pygame.mixer.music.stop()
                                        break
                elif choice == "Manual text to speech":
                    manual_tts()
                elif choice == "Re scan Songs":
                    rescan_songs()
                elif choice == "Connect to WiFi":
                    wifiSetup()
                elif choice == "Setup Hotspot":
                    portal_setup()
                elif choice == "Bluetooth":
                    bluetooth_menu()
                elif choice == "Get local IP":
                    speak("Your Local IP is: " + wifi.get_ip())
                elif choice == "Open App":
                    run_script_menu()
                    return
                elif choice == "AI Mode":
                    ai_mode()
                    return
                elif choice == "Update TailsMusic":
                    speak("Updating TailsMusic")
                    pygame.mixer.music.load(str(SFX_DIR / "dialup.mp3"))
                    pygame.mixer.music.play(-1)
                    try:
                        subprocess.run(["git", "-C", str(ROOT), "pull", "--ff-only"], check=True)
                        speak("Reloading TailsMusic")
                        print("TailsMusic: update completed; exiting for supervisor restart.", flush=True)
                        os._exit(1)
                    except Exception as e:
                        raise
                pausesfx.play()
                break

def playlist_menu():
    def list_playlists():
        return [f for f in os.listdir(PLAYLIST_DIR) if f.endswith('.json')]
    while True:
        if daemonRunning: cmdq.process_Command()
        options = ["Create", *list_playlists(), "Back"]
        selected = 0
        speak_menu_option(options, selected)
        waiting = True
        while waiting:
            event = read_input_event()
            if event and event.type == ecodes.EV_KEY:
                selected, action = menu_nav(event, selected, options)
                if action:
                    click.play()
                    choice = options[selected]
                    if choice == "Back":
                        return
                    elif choice == "Create":
                        create_playlist()
                    else:
                        manage_playlist(choice)
                    waiting = False

def create_playlist():
    global playlist_counter
    songs = []
    song_files = sorted([f for f in os.listdir(MUSIC_DIR) if f.endswith('.mp3')])
    speak(f"Creating playlist {playlist_counter}")
    selected = 0
    while True:
        if daemonRunning: cmdq.process_Command()
        options = ["Add song", "Finish"]
        event = read_input_event()
        if event and event.type == ecodes.EV_KEY:
            selected, action = menu_nav(event, selected, options)
            if action:
                click.play()
                if options[selected] == "Finish":
                    with (PLAYLIST_DIR / f"playlist{playlist_counter}.json").open("w") as f:
                        json.dump(songs, f)
                    speak("Playlist saved")
                    playlist_counter += 1
                    return
                elif options[selected] == "Add song":
                    song_selected = 0
                    speak_allowinter(song_files[song_selected])
                    while True:
                        if daemonRunning: cmdq.process_Command()
                        evt = read_input_event()
                        if evt and evt.type == ecodes.EV_KEY:
                            song_selected, action = menu_nav(evt, song_selected, song_files)
                            if action:
                                click.play()
                                songs.append(song_files[song_selected])
                                speak("Song added")
                                break

def manage_playlist(name):
    with (PLAYLIST_DIR / name).open() as f:
        songs = json.load(f)
    options = ["Play", "Delete", "Back"]
    selected = 0
    speak_menu_option(options, selected)
    while True:
        if daemonRunning: cmdq.process_Command()
        event = read_input_event()
        if event and event.type == ecodes.EV_KEY:
            selected, action = menu_nav(event, selected, options)
            if action:
                click.play()
                choice = options[selected]
                if choice == "Back":
                    break
                elif choice == "Delete":
                    speak("Confirm delete")
                    while True:
                        if daemonRunning: cmdq.process_Command()
                        evt = read_input_event()
                        if evt and evt.type == ecodes.EV_KEY:
                            selected2, action2 = menu_nav(evt, 0, ["Delete", "Cancel"])
                            if action2:
                                if ["Delete", "Cancel"][selected2] == "Delete":
                                    click.play()
                                    os.remove(PLAYLIST_DIR / name)
                                    speak("Deleted")
                                    return
                                else:
                                    speak("Cancel")
                                    break
                elif choice == "Play":
                    playlist_index = 0
                    while playlist_index < len(songs):
                        song = str(MUSIC_DIR / Path(songs[playlist_index]).name)
                        print(song)
                        pygame.mixer.music.load(song)
                        pygame.mixer.music.play()
                        advance = True  # Flag to control playlist_index increment

                        while pygame.mixer.music.get_busy():
                            event = read_input_event()
                            if event and event.type == ecodes.EV_KEY:
                                key_event = categorize(event)
                                if key_event.keystate == 1:
                                    key = key_event.keycode
                                    if key == config['skipbutton']:
                                        pygame.mixer.music.stop()
                                        break  # Move to next song
                                    elif key == config['backbutton']:
                                        pygame.mixer.music.stop()
                                        playlist_index = max(0, playlist_index - 2)
                                        advance = False
                                        break
                                    elif key == config['okbutton'] or key == config['okbutton2']:
                                        pygame.mixer.music.stop()
                                        playlist_index = len(songs)  # Exit playlist
                                        break

                        if advance:
                            playlist_index += 1

                    speak("Playlist done")
                    return


def song_menu():
    panel.play()
    global index
    options = ["Add to Playlist", "Show Info", "Back"]
    selected = 0
    speak_menu_option(options, selected)
    while True:
        if daemonRunning: cmdq.process_Command()
        event = read_input_event()
        if event and event.type == ecodes.EV_KEY:
            selected, action = menu_nav(event, selected, options)
            if action:
                click.play()
                choice = options[selected]
                if choice == "Add to Playlist":
                    add_song_to_playlist(playlist[index])
                elif choice == "Show Info":
                    show_song_info(playlist[index])
                elif choice == "Delete Song":
                    try:
                        os.remove(playlist[index])
                        speak("Song deleted")
                        del playlist[index]
                        index %= len(playlist)
                    except Exception as e:
                        raise
                    break
                elif choice == "Back":
                    break
      

def add_song_to_playlist(song_path):
    playlists = [f for f in os.listdir(PLAYLIST_DIR) if f.endswith('.json')]
    if not playlists:
        speak("No playlists found. Create one first.")
        return
    selected = 0
    speak("Select playlist to add")
    speak(playlists[selected])
    while True:
        event = read_input_event()
        if event and event.type == ecodes.EV_KEY:
            selected, action = menu_nav(event, selected, playlists)
            if action:
                with open(os.path.join(PLAYLIST_DIR, playlists[selected]), "r+") as f:
                    songs = json.load(f)
                    if Path(song_path).name not in songs:
                        songs.append(Path(song_path).name)
                        f.seek(0)
                        json.dump(songs, f)
                        f.truncate()
                        speak("Song added to playlist.")
                    else:
                        speak("Song already in playlist.")
                break

def show_song_info(song_path):
    try:
        fname = os.path.basename(song_path)
        speak(f"Song name: {fname}")
    except Exception as e:
        raise
def ai_mode():
    global index, paused, shuffleOn
    if 'shuffleOn' not in globals():
        shuffleOn = False
    try:
        from gtts import gTTS
    except ImportError:
        speak("Installing Google TTS")
        print("Install gTTS in the TailsMusic virtual environment using setup.sh")
        return

    STT_URL = "http://tails1154.com:25569/is_wake"
    context = [
        {"role": "system", "content": (
            "You are TailsMusic AI, a voice assistant controlling a Raspberry Pi music player called TailsMusic. "
            "You can control the player with these commands (one per line, include them when appropriate):\n"
            "!next - skip to next song\n"
            "!prev - go to previous song\n"
            "!pause - toggle pause/play\n"
            "!volume N - set volume 0-100\n"
            "!shuffle - toggle shuffle mode\n"
            "!play SONG_NAME - find and play a song (use partial name)\n"
            "!search QUERY - search for songs matching QUERY, returns matching song names\n"
            "!current - says the currently playing song name\n"
            "!stop - stop playback\n"
            "!help - list available voice commands\n\n"
            "When the user asks you to control playback, respond naturally AND include the appropriate command on its own line. "
            "If they ask about the current song, use !current. "
            "If they ask to find/play a specific song, use !play or !search. "
            "Keep responses brief and conversational since they will be spoken aloud."
        )}
    ]
    speak("AI mode")
    while True:
        if daemonRunning: cmdq.process_Command()
        event = read_input_event()
        if event and event.type == ecodes.EV_KEY:
            key_event = categorize(event)
            if key_event.keystate == 1:
                key = key_event.keycode
                if key == config['backbutton']:
                    speak_nointer("Exiting AI mode")
                    return
                elif key in [config['okbutton'], config['okbutton2']]:
                    click.play()
                    try:
                        card, mic_source = bluetooth_recording_devices()
                        if card:
                            subprocess.run(["pactl", "set-card-profile", card, "headset-head-unit"], capture_output=True)
                        sleep(0.5)
                        speak("Recording")
                        raw_data = None
                        try:
                            _, detected_source = bluetooth_recording_devices()
                            mic_source = detected_source or mic_source
                            if not mic_source:
                                speak("No Bluetooth microphone detected")
                                continue
                            rec_path = str(Path(tempfile.gettempdir()) / f"tailsmusic_ai_recording_{os.getuid()}.wav")
                            proc = subprocess.Popen(["parec", "--file-format=wav", "-d", mic_source, "--rate=16000", "--format=s16le", "--channels=1", rec_path], stderr=subprocess.DEVNULL)
                            while True:
                                if daemonRunning: cmdq.process_Command()
                                event = read_input_event()
                                if event and event.type == ecodes.EV_KEY:
                                    ke = categorize(event)
                                    if ke.keystate == 1 and ke.keycode == config['skipbutton']:
                                        proc.terminate()
                                        break
                                    elif ke.keystate == 1 and ke.keycode in [config['backbutton']]:
                                        proc.terminate()
                                        raw_data = b""
                                        break
                                sleep(0.05)
                            proc.wait()
                            if raw_data is None:
                                with open(rec_path, "rb") as f:
                                    raw_data = f.read()
                        except Exception as e:
                            raise
                    finally:
                        subprocess.run(["pactl", "set-card-profile", card, "a2dp-sink"], capture_output=True) if card else None
                    if len(raw_data) < 8000:
                        speak("Nothing heard")
                        continue
                    speak_nointer("Transcribing")
                    try:
                        r = requests.post(STT_URL, data=raw_data, timeout=15)
                        r.raise_for_status()
                        text = r.json().get("text", "")
                    except Exception as e:
                        raise
                    if not text or text.lower() in ("law", "claw", "wall"):
                        continue
                    speak_nointer("You said " + text)
                    speak_nointer("Press skip if correct, back to re record")
                    confirmed = False
                    while not confirmed:
                        if daemonRunning: cmdq.process_Command()
                        event = read_input_event()
                        if event and event.type == ecodes.EV_KEY:
                            ke = categorize(event)
                            if ke.keystate == 1:
                                if ke.keycode == config['skipbutton']:
                                    click.play()
                                    confirmed = True
                                elif ke.keycode in [config['backbutton'], config['okbutton'], config['okbutton2']]:
                                    click.play()
                                    break
                        sleep(0.05)
                    if not confirmed:
                        continue
                    speak_nointer("Thinking")
                    current_song = os.path.basename(playlist[index]) if playlist else "none"
                    state_msg = f"Current state: playing '{current_song}', paused={paused}, shuffle={'on' if shuffleOn else 'off'}, total songs={len(playlist)}"
                    context.append({"role": "system", "content": state_msg})
                    context.append({"role": "user", "content": text})
                    try:
                        resp = requests.post("https://ai.tails1154.com/api/chat",
                            json={"messages": context},
                            headers={"Content-Type": "application/json"},
                            timeout=30)
                        resp.raise_for_status()
                        data = resp.json()
                        if "choices" in data:
                            response_text = data["choices"][0]["message"]["content"]
                        elif "response" in data:
                            response_text = data["response"]
                        else:
                            response_text = str(data)
                    except Exception as e:
                        raise
                    context.pop()
                    context.pop()
                    context.append({"role": "user", "content": text})
                    context.append({"role": "assistant", "content": response_text})
                    speech_lines = []
                    for line in response_text.split("\n"):
                        line = line.strip()
                        if line.startswith("!"):
                            cmd = line[1:].strip()
                            if cmd == "next":
                                next_song()
                            elif cmd == "prev":
                                prev_song()
                            elif cmd == "pause":
                                toggle_pause()
                            elif cmd == "stop":
                                pygame.mixer.music.stop()
                                paused = False
                                update_tailsign("stopped")
                            elif cmd.startswith("volume"):
                                try:
                                    vol = int(cmd.split()[1])
                                    vol = max(0, min(100, vol))
                                    pygame.mixer.music.set_volume(vol / 100.0)
                                except Exception:
                                    raise
                            elif cmd == "shuffle":
                                shuffleOn = not shuffleOn
                            elif cmd.startswith("play"):
                                song_name = cmd[5:].strip().lower()
                                found = None
                                for i, s in enumerate(playlist):
                                    if song_name in os.path.basename(s).lower():
                                        found = i
                                        break
                                if found is not None:
                                    index = found
                                    pygame.mixer.music.load(playlist[index])
                                    pygame.mixer.music.play()
                                    update_tailsign()
                            elif cmd == "current":
                                song_name = os.path.basename(playlist[index]) if playlist else "nothing"
                                speech_lines.append(f"Currently playing {song_name}")
                            elif cmd.startswith("search"):
                                query = cmd[7:].strip().lower()
                                matches = [os.path.basename(s) for s in playlist if query in os.path.basename(s).lower()]
                                if matches:
                                    names = ", ".join(m[:30] for m in matches[:5])
                                    speech_lines.append(f"Found {len(matches)} songs: {names}")
                                else:
                                    speech_lines.append("No songs found")
                            elif cmd == "help":
                                speech_lines.append("Commands: next, prev, pause, volume, shuffle, play, stop, current, search")
                        else:
                            if line:
                                speech_lines.append(line)
                    speech_text = " ".join(speech_lines) if speech_lines else "Say something"
                    try:
                        if speech_text:
                            speak_nointer("Generating Text To Speech")
                            publish_touchscreen(spoken_text=speech_text)
                            tts = gTTS(text=speech_text, lang="en")
                            response_path = str(Path(tempfile.gettempdir()) / f"tailsmusic_ai_response_{os.getuid()}.mp3")
                            tts.save(response_path)
                            sfx = pygame.mixer.Sound(response_path)
                            chan = sfx.play()
                            if chan:
                                tts_len = sfx.get_length()
                                for _ in range(int(tts_len / 0.05)):
                                    if daemonRunning: cmdq.process_Command()
                                    event = read_input_event()
                                    if event and event.type == ecodes.EV_KEY:
                                        ke = categorize(event)
                                        if ke.keystate == 1 and ke.keycode in [config['skipbutton'], config['backbutton']]:
                                            sfx.stop()
                                            break
                                    sleep(0.05)
                    except Exception:
                        raise
if __name__ == "__main__":
    cmdq = CommandQueue(20, True, True)
    cmdq.start_command_listener()
    cmdq.start_remote_processor()
    print("Modules Loaded!")
    print("TailsMusic Loading...")
    print("Finding Headphones")
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    PLAYLIST_DIR.mkdir(parents=True, exist_ok=True)
    device_path = find_simolio()
    if device_path:
        print("Using Headphone device:", device_path)
        dev = InputDevice(device_path)
    else:
        print("Bluetooth media button device not found; exiting for restart.", flush=True)
        os._exit(errno.ENODEV)  # Immediately terminate only this process.

    INPUT_DEVICE = device_path
    os.makedirs(PLAYLIST_DIR, exist_ok=True)
    daemonRunning = False
    try:
        print("Remvoing stale app.py")
        os.remove(APP_PATH)
        print("Starting Voice")
    except FileNotFoundError:
        pass  # No stale app.py is normal.
    tts_lock = threading.Lock()
    print("Loading Music Files")
    playlist = sorted(
        [str(MUSIC_DIR / f) for f in os.listdir(MUSIC_DIR) if f.lower().endswith('.mp3')]
    )
    # Python manages bytecode caches; do not delete them at every startup.
    if not playlist:
        print("No music found. Add MP3 files to", MUSIC_DIR)
        sys.exit(1)
    index = 0
    paused = False
    print("Loading Audio Driver")
    # Route through PulseAudio for Bluetooth devices. Direct ALSA output is
    # prone to underruns when the Bluetooth sink changes or wakes up.
    os.environ['SDL_AUDIO_ALSA_BUFFER_SIZE'] = '4096'
    os.environ['SDL_AUDIODRIVER'] = 'pulse'
    pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=4096)
    try:
        pygame.mixer.init()
    except pygame.error as pulse_error:
        print(f"PulseAudio init failed ({pulse_error}); falling back to ALSA")
        os.environ['SDL_AUDIODRIVER'] = 'alsa'
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=4096)
        pygame.mixer.init()
    print("Loading sfx...")
    pausesfx = pygame.mixer.Sound(str(SFX_DIR / "pause.mp3"))
    dialup = pygame.mixer.Sound(str(SFX_DIR / "dialup.mp3"))
    panel = pygame.mixer.Sound(str(SFX_DIR / "panel.mp3"))
    click = pygame.mixer.Sound(str(SFX_DIR / "click.mp3"))
    print("Welcome to TailsMusic!")
    clear_touch_commands()
    publish_touchscreen(song=Path(playlist[index]).stem, spoken_text="", playback="stopped")
    pygame.mixer.music.load(playlist[index])
    pygame.mixer.music.play()
    update_tailsign()
    touchscreen_process = start_optional_touchscreen()

    playlist_counter = max((int(f.removeprefix("playlist").removesuffix(".json")) for f in os.listdir(PLAYLIST_DIR) if f.startswith("playlist") and f.endswith(".json") and f.removeprefix("playlist").removesuffix(".json").isdigit()), default=-1) + 1
    dev = InputDevice(INPUT_DEVICE)
    print(f"Listening on {INPUT_DEVICE}...")
    while True:
        if touchscreen_process is not None and touchscreen_process.poll() is not None:
            code = touchscreen_process.returncode
            raise RuntimeError(
                f"TailsMusic: companion display exited (status {code}); "
                "crashing player so service supervisor can restart it."
            )
        if daemonRunning: cmdq.process_Command()
        event = read_input_event()
        if event and event.type == ecodes.EV_KEY:
            key_event = categorize(event)
            if key_event.keystate == 1:
                key = key_event.keycode
                if key in [config['okbutton'], config['okbutton2']]:
                    toggle_pause()
                elif key == config['skipbutton']:
                    if paused:
                        panel.play()
                        shutdown_menu()
                    else:
                        next_song()
                elif key == config['backbutton']:
                    if not paused:
                        prev_song()
                    else:
                        song_menu()
        time.sleep(0.05)
        if not pygame.mixer.music.get_busy() and not paused:
            sleep(0.5)
            next_song()
