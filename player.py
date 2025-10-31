#!/bin/python3
print("TailsMusic preinit")
print("Loading Modules")
#print("This is a different line")
totalModules = 10
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
print(f"(9/{totalModules}) shutil")
import shutil
print(f"(10/{totalModules}) queue")
import queue
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
def menu_nav(event, selected, options):
    """
    Handle menu navigation: back cycles BACK, skip cycles FORWARD, play/pause (okbutton/okbutton2) selects.
    Returns tuple (selected, selected_action) where selected_action is True if play/pause was pressed.
    """
    key_event = categorize(event)
    if key_event.keystate == 1:
        key = key_event.keycode
        if key == config['backbutton']:
            selected = (selected - 1) % len(options)
            speak(options[selected])
        elif key == config['skipbutton']:
            selected = (selected + 1) % len(options)
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


cmdq = CommandQueue(20, True, True)
cmdq.start_command_listener()
cmdq.start_remote_processor()
print("Modules Loaded!")
print("TailsMusic Loading...")
print("Finding Headphones")
def find_simolio():
    """This finds the bluetooth input device for button presses."""
    for path in list_devices():
        dev = InputDevice(path)
        if config['evtestname'] in dev.name:
            return path
    return None

device_path = find_simolio()
if device_path:
    print("Using Headphone device:", device_path)
    dev = InputDevice(device_path)
else:
    print("Bluetooth media button device not found.")
    exit(1)

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
def speak(text):
    print(f"TTS: {text}")
    subprocess.run(["killall", "espeak-ng"], check=False)
    subprocess.run(["espeak-ng", "-s", "130", text], check=True)
def speak_allowinter(text):
    subprocess.run(["killall", "espeak-ng"], check=False)
    subprocess.Popen(["espeak-ng", "-s", "130", text])

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
    exit()
index = 0
paused = False
print("Loading Audio Driver")
pygame.mixer.init()
print("Loading sfx...")
pausesfx = pygame.mixer.Sound("/home/pi/mp3player/sfx/pause.mp3")
dialup = pygame.mixer.Sound("/home/pi/mp3player/sfx/dialup.mp3")
panel = pygame.mixer.Sound("/home/pi/mp3player/sfx/panel.mp3")
click = pygame.mixer.Sound("/home/pi/mp3player/sfx/click.mp3")
print("Welcome to TailsMusic!")
pygame.mixer.music.load(playlist[index])
pygame.mixer.music.play()

def next_song():
    global index
    index += 1
    if index >= len(playlist):
        index = 0
    pygame.mixer.music.load(playlist[index])
    pygame.mixer.music.play()

def prev_song():
    global index
    index = (index - 1) % len(playlist)
    pygame.mixer.music.load(playlist[index])
    pygame.mixer.music.play()

def toggle_pause():
    global paused
    if paused:
        pausesfx.play()
        time.sleep(pausesfx.get_length())
        pygame.mixer.music.unpause()
    else:
        pausesfx.play()
        pygame.mixer.music.pause()
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

def shutdown_menu():
    options = ["Playlists", "Random Song", "Update TailsMusic", "Manual text to speech", "Re scan Songs", 
               "Connect to WiFi", "Get local IP", "Open App", "Shut Down", "Back"]
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
                if choice == "Shut Down":
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
                            if action2 and options[0] == "Stop":
                                pygame.mixer.music.stop()
                                break
                elif choice == "Manual text to speech":
                    manual_tts()
                elif choice == "Re scan Songs":
                    speak("Rescanning")
                    exit(0)
                elif choice == "Connect to WiFi":
                    wifiSetup()
                elif choice == "Get local IP":
                    speak("Your Local IP is: " + wifi.get_ip())
                elif choice == "Open App":
                    run_script_menu()
                    return
                elif choice == "Update TailsMusic":
                    speak("Updating TailsMusic")
                    pygame.mixer.music.load("sfx/dialup.mp3")
                    pygame.mixer.music.play(-1)
                    try:
                        subprocess.run(["git", "pull"], check=True)
                        speak("Reloading TailsMusic")
                        exit(0)
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

playlist_counter = max((int(f.removeprefix("playlist").removesuffix(".json")) for f in os.listdir("/home/pi/mp3player/playlists/") if f.startswith("playlist") and f.endswith(".json")), default=-1) + 1
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
                        while pygame.mixer.music.get_busy():
                            event = dev.read_one()
                            if event and event.type == ecodes.EV_KEY:
                                selected2, action2 = menu_nav(event, 0, ["Skip", "Back"])
                                if action2:
                                    if ["Skip", "Back"][selected2] == "Skip":
                                        pygame.mixer.music.stop()
                                        break
                                    elif ["Skip", "Back"][selected2] == "Back":
                                        pygame.mixer.music.stop()
                                        playlist_index = max(playlist_index - 2, -1)
                                        break
                        playlist_index += 1
                    speak("Playlist done")
                    return

def song_menu():
    global index
    options = ["Add to Playlist", "Show Info", "Delete Song", "Back"]
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
    speak("Exiting song menu")

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
    if not pygame.mixer.music.get_busy() and not paused:
        sleep(0.5)
        next_song()
