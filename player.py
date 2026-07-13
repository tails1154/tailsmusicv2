#!/bin/python3
print("TailsMusic preinit")
print("Loading Modules")
#print("This is a different line")
totalModules = 10
global shuffleOn
print(f"(0/{totalModules}) os")
import os
print(f"(1/{totalModules}) pygame")
import pygame
print(f"(2/{totalModules}) evdev")
from evdev import InputDevice, categorize, ecodes, list_devices
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
print(f"(9/{totalModules}) shutil")
import shutil
print(f"(10/{totalModules}) queue")
import queue
import requests
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
    os.system("espeak-ng 'pulsectl module not found. installing it' -s 130")
    os.system("pip install pulsectl bleak --break-system-packages")
    os.system("espeak-ng 'pulsectl module installed. reloading TailsMusic' -s 130")
    os.system("killall -9 python3")
print("TailsMusic Loading...")
global daemonRunning
daemonRunning = False
print("multiprocessing")
import multiprocessing
print("queue")
print("sys")
import sys
print("what is typing")
from typing import Optional
print("nice")
print("Loading config.json")
with open('config.json', 'r') as file:
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
    key_event = categorize(event)
    if key_event.keystate == 1:
        key = key_event.keycode
        if key == config['backbutton']:
            selected = (selected - 1) % len(options)
            if allowInterrupt:
                speak_allowinter(options[selected])
            else:
                speak(options[selected])
        elif key == config['skipbutton']:
            selected = (selected + 1) % len(options)
            if allowInterrupt:
                speak_allowinter(options[selected])
            else:
                speak(options[selected])
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
                print(f"Remote processor error: {e}")

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
                print(f"Command input error: {e}")

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
                print(f"Command processing error: {e}")

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
            print(f"[CMD] Timeout: Command took too long: {cmd}")
        except subprocess.CalledProcessError as e:
            print(f"[CMD] Failed (exit {e.returncode}): {cmd}\n{e.stderr}")
        except Exception as e:
            print(f"[CMD] Unexpected error: {e}")

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
    """This finds the bluetooth input device for button presses."""
    for path in list_devices():
        dev = InputDevice(path)
        if config['evtestname'] in dev.name:
            return path
    return None

def speak_nointer(text):
    print(f"TTS: {text}")
    subprocess.run(["killall", "espeak-ng"], check=False)
    subprocess.run(["espeak-ng", "-s", "130", text], check=True)
def speak(text):
    subprocess.run(["killall", "espeak-ng"], check=False)
    subprocess.Popen(["espeak-ng", "-s", "130", text])
def speak_allowinter(text):
    speak(text)

def update_tailsign(status=None):
    """Update the TailSign display with current song info.
    Only updates if 'show_on_tailsign' is enabled in config.
    """
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
        pass
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
    speak(options[selected])
    toSpeak = ""
    while True:
        if daemonRunning: cmdq.process_Command()
        event = dev.read_one()
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
    pygame.mixer.music.load("/home/pi/mp3player/sfx/dialup.mp3")
    pygame.mixer.music.play()
    networks = wifi.scan_wifi()
    if networks:
        options = [ssid for ssid, signal in networks]
        pygame.mixer.music.stop()
        selected = 0
        speak("Choose your wifi network")
        speak(options[selected])
        while True:
            if daemonRunning: cmdq.process_Command()
            event = dev.read_one()
            if event and event.type == ecodes.EV_KEY:
                selected, action = menu_nav(event, selected, options)
                if action:
                    click.play()
                    wifiName = options[selected]
                    pygame.mixer.music.load("/home/pi/mp3player/sfx/dialup.mp3")
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
                    speak(options[selected])
                    while True:
                        if daemonRunning: cmdq.process_Command()
                        event = dev.read_one()
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
                                        pygame.mixer.music.stop()
                                        speak("Error connecting: " + str(e))
                                        break
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
        print("pulsectl list error:", e)
        return []


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
                    pass
        return True
    except Exception as e:
        print("Error setting default sink:", e)
        return False


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
        print('bluetoothctl devices error:', e)
        return []


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
            print('bleak scan error:', e)

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
            out, err = p.communicate(timeout=timeout + 5)
        except subprocess.TimeoutExpired:
            p.kill()
            out, err = p.communicate()
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
                    continue
        if not devices:
            return bluetooth_list_devices()
        return devices
    except Exception as e:
        print('bluetooth scan error:', e)
        return []


def bluetooth_pair_connect(mac: str) -> bool:
    """Attempt to pair, trust, and connect to a device via bluetoothctl."""
    try:
        subprocess.run(['bluetoothctl', 'pair', mac], check=False)
        subprocess.run(['bluetoothctl', 'trust', mac], check=False)
        res = subprocess.run(['bluetoothctl', 'connect', mac], check=False)
        return res.returncode == 0
    except Exception as e:
        print('bluetooth connect error:', e)
        return False


def bluetooth_menu():
    """UI menu (button-driven) for scanning, pairing and selecting a Bluetooth speaker sink."""
    options = ["Scan Devices", "Known Devices", "List Audio Sinks", "Back"]
    selected = 0
    speak(options[selected])
    while True:
        if daemonRunning: cmdq.process_Command()
        event = dev.read_one()
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
                        e = dev.read_one()
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
                        e = dev.read_one()
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
                        e = dev.read_one()
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
    apps_dir = os.path.join(os.path.dirname(__file__), 'apps')
    if os.path.exists(apps_dir):
        py_files = [os.path.join(root, f) 
                   for root, _, files in os.walk(apps_dir) 
                   for f in files if f.endswith('.py')]
    if not py_files:
        speak("No scripts found in apps directory")
        return
    options = [os.path.basename(f) for f in py_files] + ["Back"]
    selected = 0
    speak(options[selected])
    while True:
        global daemonRunning
        if daemonRunning: cmdq.process_Command()
        event = dev.read_one()
        if event and event.type == ecodes.EV_KEY:
            selected, action = menu_nav(event, selected, options)
            if action:
                click.play()
                if options[selected] == "Back":
                    return
                else:
                    speak(f"Running {options[selected]}")
                    subprocess.run(["cp", "apps/" + options[selected], "app.py"])
                    import app as appModule
                    app = appModule.APP(dev, cmdq)
                    if app.checkDaemon():
                        speak("App is a daemon. Running in background")
                        thread = multiprocessing.Process(target=app.start)
                        thread.start()
                        daemonRunning = True
                    else:
                        app.start()
                        os.remove("app.py")
                        speak("Script finished")
                    return

def portal_setup():
    speak("Starting setup hotspot")
    msg = hotspot.start()
    speak("Hotspot started")
    print(msg)
    speak("Connect to TailsMusic Setup WiFi. It is an open network")
    options = ["Stop Hotspot", "Back"]
    selected = 0
    speak(options[selected])
    while True:
        if daemonRunning: cmdq.process_Command()
        event = dev.read_one()
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
            speak(options[selected])
            first_render = False
        if daemonRunning: cmdq.process_Command()
        event = dev.read_one()
        if event and event.type == ecodes.EV_KEY:
            selected, action = menu_nav(event, selected, options)
            if action:
                click.play()
                choice = options[selected]
                if choice and choice.startswith("Show on TailSign"):
                    current = config.get("show_on_tailsign", False)
                    config["show_on_tailsign"] = not current
                    with open("config.json", "w") as cfg_f:
                        json.dump(config, cfg_f, indent=4)
                    speak("Show on TailSign " + ("enabled" if not current else "disabled"))
                elif choice == "Shut Down":
                    speak("Shutting down")
                    subprocess.run(["sudo", "shutdown", "now"])
                elif choice == "Back":
                    pausesfx.play()
                    return
                elif choice == "Playlists":
                    playlist_menu()
                elif choice == "Random Song":
                    song_files = sorted([f for f in os.listdir(MUSIC_DIR) if f.endswith('.mp3')], key=str.lower)
                    random_song = random.choice(song_files) if song_files else None
                    pygame.mixer.music.load("songs/" + random_song)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        event = dev.read_one()
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
                            event = dev.read_one()
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
                    speak("Rescanning")
                    os.system("killall -9 python3")
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
                    pygame.mixer.music.load("sfx/dialup.mp3")
                    pygame.mixer.music.play(-1)
                    try:
                        subprocess.run(["git", "pull"], check=True)
                        speak("Reloading TailsMusic")
                        os.system("killall -9 python3")
                    except Exception as e:
                        speak("Error updating: " + str(e))
                pausesfx.play()
                break

def playlist_menu():
    def list_playlists():
        return [f for f in os.listdir(PLAYLIST_DIR) if f.endswith('.json')]
    while True:
        if daemonRunning: cmdq.process_Command()
        options = ["Create", *list_playlists(), "Back"]
        selected = 0
        speak(options[selected])
        waiting = True
        while waiting:
            event = dev.read_one()
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
        event = dev.read_one()
        if event and event.type == ecodes.EV_KEY:
            selected, action = menu_nav(event, selected, options)
            if action:
                click.play()
                if options[selected] == "Finish":
                    with open(f"{PLAYLIST_DIR}/playlist{playlist_counter}.json", 'w') as f:
                        json.dump(songs, f)
                    speak("Playlist saved")
                    playlist_counter += 1
                    return
                elif options[selected] == "Add song":
                    song_selected = 0
                    speak_allowinter(song_files[song_selected])
                    while True:
                        if daemonRunning: cmdq.process_Command()
                        evt = dev.read_one()
                        if evt and evt.type == ecodes.EV_KEY:
                            song_selected, action = menu_nav(evt, song_selected, song_files)
                            if action:
                                click.play()
                                songs.append(os.path.join(MUSIC_DIR, song_files[song_selected]))
                                speak("Song added")
                                break

def manage_playlist(name):
    with open(f"{PLAYLIST_DIR}/{name}") as f:
        songs = json.load(f)
    options = ["Play", "Delete", "Back"]
    selected = 0
    speak(options[selected])
    while True:
        if daemonRunning: cmdq.process_Command()
        event = dev.read_one()
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
                        evt = dev.read_one()
                        if evt and evt.type == ecodes.EV_KEY:
                            selected2, action2 = menu_nav(evt, 0, ["Delete", "Cancel"])
                            if action2:
                                if ["Delete", "Cancel"][selected2] == "Delete":
                                    click.play()
                                    os.remove(f"{PLAYLIST_DIR}/{name}")
                                    speak("Deleted")
                                    return
                                else:
                                    speak("Cancel")
                                    break
                elif choice == "Play":
                    playlist_index = 0
                    while playlist_index < len(songs):
                        song = songs[playlist_index]
                        print(song)
                        pygame.mixer.music.load(song)
                        pygame.mixer.music.play()
                        advance = True  # Flag to control playlist_index increment

                        while pygame.mixer.music.get_busy():
                            event = dev.read_one()
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
    speak(options[selected])
    while True:
        if daemonRunning: cmdq.process_Command()
        event = dev.read_one()
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
                        speak("Error deleting song: " + str(e))
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
        event = dev.read_one()
        if event and event.type == ecodes.EV_KEY:
            selected, action = menu_nav(event, selected, playlists)
            if action:
                with open(os.path.join(PLAYLIST_DIR, playlists[selected]), "r+") as f:
                    songs = json.load(f)
                    if song_path not in songs:
                        songs.append(song_path)
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
        speak("Error showing song info: " + str(e))


def ai_mode():
    global index, paused, shuffleOn
    try:
        from gtts import gTTS
    except ImportError:
        speak("Installing Google TTS")
        os.system("pip install gtts --break-system-packages")
        os.system("killall -9 python3")
        return

    STT_URL = "http://tails1154.com:25569/is_wake"
    system_prompt = (
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
    )
    context = [
        {"role": "system", "content": system_prompt}
    ]
    speak("AI mode")
    while True:
        if daemonRunning: cmdq.process_Command()
        event = dev.read_one()
        if event and event.type == ecodes.EV_KEY:
            key_event = categorize(event)
            if key_event.keystate == 1:
                key = key_event.keycode
                if key == config['backbutton']:
                    speak("Exiting AI mode")
                    os.system("killall -9 python3")
                    return
                elif key in [config['okbutton'], config['okbutton2']]:
                    click.play()
                    speak("Listening")
                    proc = subprocess.Popen(["arecord", "-d", "7", "-f", "S16_LE", "-r", "16000", "-t", "wav", "/tmp/ai_input.wav"], stderr=subprocess.DEVNULL)
                    while proc.poll() is None:
                        if daemonRunning: cmdq.process_Command()
                        event = dev.read_one()
                        if event and event.type == ecodes.EV_KEY:
                            key_event = categorize(event)
                            if key_event.keystate == 1:
                                key = key_event.keycode
                                if key in [config['okbutton'], config['okbutton2'], config['skipbutton']]:
                                    proc.kill()
                                    proc.wait()
                                    break
                        sleep(0.05)
                    if proc.returncode == -9:
                        continue
                    try:
                        with open("/tmp/ai_input.wav", "rb") as f:
                            wav_data = f.read()
                        resp = requests.post(STT_URL, data=wav_data, timeout=15)
                        resp.raise_for_status()
                        result = resp.json()
                        text = result.get("text", "")
                    except Exception:
                        continue
                    if not text or text.lower() in ("law", "claw", "wall"):
                        continue
                    speak_nointer("You said " + text)
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
                        response_text = ""
                        reader = resp.iter_lines()
                        for line in reader:
                            if line:
                                try:
                                    data = json.loads(line)
                                    if "response" in data:
                                        response_text += data["response"]
                                except Exception:
                                    pass
                        if not response_text:
                            response_text = resp.text
                    except Exception:
                        continue
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
                            elif cmd.startswith("volume"):
                                try:
                                    vol = int(cmd.split()[1])
                                    vol = max(0, min(100, vol))
                                    pygame.mixer.music.set_volume(vol / 100.0)
                                except Exception:
                                    pass
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
                            tts = gTTS(text=speech_text, lang="en")
                            tts.save("/tmp/ai_response.mp3")
                            sfx = pygame.mixer.Sound("/tmp/ai_response.mp3")
                            chan = sfx.play()
                            if chan:
                                tts_len = sfx.get_length()
                                for _ in range(int(tts_len / 0.05)):
                                    if daemonRunning: cmdq.process_Command()
                                    event = dev.read_one()
                                    if event and event.type == ecodes.EV_KEY:
                                        ke = categorize(event)
                                        if ke.keystate == 1 and ke.keycode in [config['skipbutton'], config['backbutton']]:
                                            sfx.stop()
                                            break
                                    sleep(0.05)
                    except Exception:
                        speak_nointer(speech_text)


if __name__ == "__main__":
    cmdq = CommandQueue(20, True, True)
    cmdq.start_command_listener()
    cmdq.start_remote_processor()
    print("Modules Loaded!")
    print("TailsMusic Loading...")
    print("Finding Headphones")
    device_path = find_simolio()
    if device_path:
        print("Using Headphone device:", device_path)
        dev = InputDevice(device_path)
    else:
        print("Bluetooth media button device not found.")
        os.system("killall -9 python3")

    MUSIC_DIR = '/home/pi/mp3player/songs'
    PLAYLIST_DIR = '/home/pi/mp3player/playlists'
    INPUT_DEVICE = device_path
    os.makedirs(PLAYLIST_DIR, exist_ok=True)
    daemonRunning = False
    try:
        print("Remvoing stale app.py")
        os.remove("app.py")
        print("Starting Voice")
    except Exception as e:
        print("Error removing app.py: " + str(e))
    tts_lock = threading.Lock()
    print("Loading Music Files")
    playlist = sorted(
        [os.path.join(MUSIC_DIR, f) for f in os.listdir(MUSIC_DIR) if f.endswith('.mp3')]
    )
    print("Removing __pycache__")
    try:
        shutil.rmtree("__pycache__")
    except Exception as e:
        print("Exception Deleteing __pycache__:" + str(e))
    if not playlist:
        speak("No songs found.")
        os.system("killall -9 python3")
    index = 0
    paused = False
    print("Switching to HFP mode for mic")
    subprocess.run(["pactl", "set-card-profile", "bluez_card.00_1E_7C_C8_C3_D8", "handsfree_head_unit"], capture_output=True)
    sleep(0.5)
    print("Loading Audio Driver")
    os.environ['SDL_AUDIODRIVER'] = 'alsa'
    pygame.mixer.pre_init(frequency=16000, size=-16, channels=1, buffer=2048)
    pygame.mixer.init()
    print("Loading sfx...")
    pausesfx = pygame.mixer.Sound("/home/pi/mp3player/sfx/pause.mp3")
    dialup = pygame.mixer.Sound("/home/pi/mp3player/sfx/dialup.mp3")
    panel = pygame.mixer.Sound("/home/pi/mp3player/sfx/panel.mp3")
    click = pygame.mixer.Sound("/home/pi/mp3player/sfx/click.mp3")
    print("Welcome to TailsMusic!")
    pygame.mixer.music.load(playlist[index])
    pygame.mixer.music.play()
    update_tailsign()

    playlist_counter = max((int(f.removeprefix("playlist").removesuffix(".json")) for f in os.listdir("/home/pi/mp3player/playlists/") if f.startswith("playlist") and f.endswith(".json")), default=-1) + 1
    dev = InputDevice(INPUT_DEVICE)
    print(f"Listening on {INPUT_DEVICE}...")
    while True:
        if daemonRunning: cmdq.process_Command()
        event = dev.read_one()
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
