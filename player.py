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
print(f"(3/10) time")
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
#global daemonRunning
# ================== MULTIPROCESSING-ENABLED COMMAND QUEUE SYSTEM ==================
import subprocess
import threading
import multiprocessing
import queue
import sys
from typing import Optional, Dict, Any
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
            # Create a multiprocessing manager for cross-process communication
            self.manager = multiprocessing.Manager()
            self.queue = self.manager.Queue(maxsize=maxsize)
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
#print("All Modules Loaded!")
print("TailsMusic Loading...")
print("Finding SIMOLIO")
def find_simolio():
    """This finds the bluetooth input device for button presses."""
    for path in list_devices():
        dev = InputDevice(path)
        if "SIMOLIO" in dev.name:
            return path
    return None

device_path = find_simolio()
if device_path:
    print("Using SIMOLIO device:", device_path)
    dev = InputDevice(device_path)
else:
    print("SIMOLIO Bluetooth media button device not found.")
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
    """This function speaks text to the user"""
    print(f"TTS: {text}")
    subprocess.run(["espeak-ng", "-s", "130", text], check=True)
  #  def run_tts():
  #      with tts_lock:
   #         try:
    #            subprocess.run(["espeak-ng", "-s", "130", text], check=True)
     #       except Exception as e:
 #               print(f"TTS subprocess error: {e}")
#    threading.Thread(target=run_tts, daemon=True).start()


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
print("Loading Sounds...")
pausesfx = pygame.mixer.Sound("/home/pi/mp3player/sfx/pause.mp3")
dialup = pygame.mixer.Sound("/home/pi/mp3player/sfx/dialup.mp3")
print("Welcome to TailsMusic!")
pygame.mixer.music.load(playlist[index])
pygame.mixer.music.play()

def next_song():
    """This function goes to the next song in the main playlist (the one that gets created when the script starts)"""
    global index
    index += 1
    if index >= len(playlist):
        index = 0
        #exit(0)
    pygame.mixer.music.load(playlist[index])
    pygame.mixer.music.play()

def prev_song():
    """This function goes the the prev song in the main playlist"""
    global index
    index = (index - 1) % len(playlist)
    pygame.mixer.music.load(playlist[index])
    pygame.mixer.music.play()

def toggle_pause():
    """This function pauses and unpauses the song in the main playlist"""
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
 """I randomly wanted to make this function to where you could input text with your headphone buttons and tts would play it"""
 options = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "space", "Done"]
 selected = 0
 speak(options[selected])
 toSpeak = ""
 while True:
  if daemonRunning: cmdq.process_Command()
  event = dev.read_one()
  if event and event.type == ecodes.EV_KEY:
   key_event = categorize(event)
   if key_event.keystate == 1:
    key = key_event.keycode
    if key == 'KEY_PREVIOUSSONG':
     selected = (selected + 1) % len(options)
     speak(options[selected])
    elif key == 'KEY_NEXTSONG':
     choice = options[selected]
     speak(choice)
     if choice == "space":
      toSpeak += " "
     elif choice == "Done":
      speak(toSpeak)
      break
     else:
      toSpeak += choice

def wifiSetup():
 """This function handles the wifi setup function."""
 speak("Loading wifi networks")
 pygame.mixer.music.load("/home/pi/mp3player/sfx/dialup.mp3")
 pygame.mixer.music.play()
 networks = wifi.scan_wifi()
 if networks:
  options = []
  for i, (ssid, signal) in enumerate(networks):
   options.append(f"{ssid}")
  pygame.mixer.music.stop()
  selected = 0
  speak("Choose your wifi network")
  speak(options[selected])
  while True:
   if daemonRunning: cmdq.process_Command()
   event = dev.read_one()
   if event and event.type == ecodes.EV_KEY:
    key_event = categorize(event)
    if key_event.keystate == 1:
     key = key_event.keycode
     if key == 'KEY_PREVIOUSSONG':
      selected = (selected + 1) % len(options)
      speak(options[selected])
     elif key == 'KEY_NEXTSONG':
      wifiName = options[selected]
      pygame.mixer.music.load("/home/pi/mp3player/sfx/dialup.mp3")
      speak("Enter your wifi password.")
      speak("For an easier setup, Connect TailsMusic to Your monitor and type")
      speak("n... m... t... u... i... with a keyboard and press enter.")
      speak("Enter your wifi password") # we "need" to say it twice because people get bored and forget what they were doing lol
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
        key_event = categorize(event)
        if key_event.keystate == 1:
         key = key_event.keycode
         if key_event.keystate == 1:
          key = key_event.keycode
          print(key)
          if key == 'KEY_PREVIOUSSONG':
           selected = (selected + 1) % len(options)
           speak(options[selected])
           #sleep(1)
          elif key == 'KEY_PLAYCD' or key == 'KEY_PAUSECD':
           selected = (selected - 1) % len(options)
           speak(options[selected])
           #sleep(1)
          elif key == 'KEY_NEXTSONG':
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
    """This function is the apps launcher"""
    # Get all .py files in apps/ directory
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
            key_event = categorize(event)
            if key_event.keystate == 1:
                key = key_event.keycode
                if key == 'KEY_PREVIOUSSONG':
                    selected = (selected + 1) % len(options)
                    speak(options[selected])
                    #sleep(1)
                elif key == 'KEY_NEXTSONG':
                    if options[selected] == "Back":
                        return
                    else:
                        script_path = py_files[selected]
                        speak(f"Running {options[selected]}")
                        if True:
                            subprocess.run(["cp", "apps/" + options[selected], "app.py"])
                            import app as appModule
                            app = appModule.APP(dev, cmdq)
                            if app.checkDaemon():
                             speak("App is a daemon. Running in background")
                             thread = threading.Thread(target=app.start, daemon=True)
                             daemonRunning = True
                            else:
                             app.start()
                             os.remove("app.py")
                             speak("Script finished")
                        #except Exception as e:
                        #    speak(f"Error running script: {str(e)}")
                        return

def shutdown_menu():
    """Despite the name, this is NOT the shutdown menu. That is in this function in a option. The reason for this function name is because early in development before I made menus that does stuff. This function used to just ask if you wanted to shutdown."""
    options = ["Playlists", "Random Song", "Update TailsMusic", "Manual text to speech", "Re scan Songs", 
               "Connect to WiFi", "Get local IP", "Shut Down", "Open App", "Back"]
    selected = 0
    speak(options[selected])
    while True:
        if daemonRunning: cmdq.process_Command()
        event = dev.read_one()
        if event and event.type == ecodes.EV_KEY:
            if True:
                key_event = categorize(event)
                if key_event.keystate == 1:
                    key = key_event.keycode
                    if key == 'KEY_PREVIOUSSONG':
                        selected = (selected + 1) % len(options)
                        speak(options[selected])
                        #sleep(1)
                    elif key == 'KEY_PLAYCD' or key == 'KEY_PAUSECD':
                                   selected = (selected - 1) % len(options)
                                   speak(options[selected])
                    elif key == 'KEY_NEXTSONG':
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
                                  key_event = categorize(event)
                                  if key_event.keystate == 1:
                                      key = key_event.keycode
                                      if key == 'KEY_NEXTSONG':
                                           pygame.mixer.music.stop()
                                           break
                        elif choice == "Manual TTS":
                              manual_tts()
                        elif choice == "Re scan Songs":
                              speak("Rescanning")
                              exit(0)
                        elif choice == "Connect to WiFi":
                              wifiSetup()
                        elif choice == "Get IP":
                              speak("Your Local IP is: " + wifi.get_ip())
                        elif choice == "Open App":
                              #global daemonRuning # nice spelling btw
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
    """This function handles the list of playlists and the Create button"""
    def list_playlists():
        return [f for f in os.listdir(PLAYLIST_DIR) if f.endswith('.json')]

    while True:
        if daemonRunning: cmdq.process_Command()
        options = ["Create"] + list_playlists() + ["Back"]
        selected = 0
        speak(options[selected])
        waiting = True
        while waiting:
            event = dev.read_one()
            if event and event.type == ecodes.EV_KEY:
                try:
                    key_event = categorize(event)
                    if key_event.keystate == 1:
                        key = key_event.keycode
                        if key == 'KEY_PREVIOUSSONG':
                            selected = (selected + 1) % len(options)
                            speak(options[selected])
                            #sleep(1)
                        elif key == 'KEY_NEXTSONG':
                            choice = options[selected]
                            if choice == "Back":
                                return
                            elif choice == "Create":
                                create_playlist()
                            else:
                                manage_playlist(choice)
                            waiting = False
                except Exception as e:
                    print(f"Playlist menu error: {e}")

playlist_counter = max((int(f.removeprefix("playlist").removesuffix(".json")) for f in os.listdir("/home/pi/mp3player/playlists/") if f.startswith("playlist") and f.endswith(".json")), default=-1) + 1
def create_playlist():
    """This function is the playlist menu that is for adding songs to a playlist and finishing the playlist."""
    global playlist_counter
    songs = []
    #song_files = [f for f in os.listdir(MUSIC_DIR) if f.endswith('.mp3')]
    song_files = sorted([f for f in os.listdir(MUSIC_DIR) if f.endswith('.mp3')])

    speak(f"Creating playlist {playlist_counter}")
    selected = 0
    while True:
        if daemonRunning: cmdq.process_Command()
        options = ["Add song", "Finish"]
        #speak(options[selected])
        event = dev.read_one()
        if event and event.type == ecodes.EV_KEY:
            try:
                key_event = categorize(event)
                if key_event.keystate == 1:
                    key = key_event.keycode
                    print(key)
                    if key == 'KEY_PREVIOUSSONG':
                        selected = (selected + 1) % len(options)
                        speak(options[selected])
                        #sleep(1)
                    elif key == 'KEY_NEXTSONG':
                        if options[selected] == "Finish":
                            with open(f"{PLAYLIST_DIR}/playlist{playlist_counter}.json", 'w') as f:
                                json.dump(songs, f)
                            speak("Playlist saved")
                            playlist_counter += 1
                            return
                        elif options[selected] == "Add song":
                            song_selected = 0
                            speak(song_files[song_selected])
                            while True:
                                if daemonRunning: cmdq.process_Command()
                                evt = dev.read_one()
                                if evt and evt.type == ecodes.EV_KEY:
                                    try:
                                        k_event = categorize(evt)
                                        if k_event.keystate == 1:
                                            k = k_event.keycode
                                            if k == 'KEY_PREVIOUSSONG':
                                                song_selected = (song_selected + 1) % len(song_files)
                                                speak(song_files[song_selected])
                                                #sleep(1)
                                            elif k == 'KEY_PLAYCD' or k == 'KEY_PAUSECD':
                                                song_selected = (song_selected - 1) % len(song_files)
                                                speak(song_files[song_selected])
                                                #sleep(1)
                                            elif k == 'KEY_NEXTSONG':
                                                songs.append(os.path.join(MUSIC_DIR, song_files[song_selected]))
                                                speak("Song added")
                                                break
                                    except Exception as e:
                                        print(f"Song selection error: {e}")
            except Exception as e:
                print(f"Create playlist error: {e}")

def manage_playlist(name):
    """This function is for playing, deleting, and going back when selecting a playlist from the playlist menu."""
    with open(f"{PLAYLIST_DIR}/{name}") as f:
        songs = json.load(f)
    options = ["Play", "Delete", "Back"]
    selected = 0
    speak(options[selected])
    while True:
        if daemonRunning: cmdq.process_Command()
        event = dev.read_one()
        if event and event.type == ecodes.EV_KEY:
            try:
                key_event = categorize(event)
                if key_event.keystate == 1:
                    key = key_event.keycode
                    if key == 'KEY_PREVIOUSSONG':
                        selected = (selected + 1) % len(options)
                        speak(options[selected])
                        #sleep(1)
                    elif key == 'KEY_NEXTSONG':
                        choice = options[selected]
                        if choice == "Back":
                          break
                        elif choice == "Delete":
                            speak("Confirm delete")
                            while True:
                                if daemonRunning: cmdq.process_Command()
                                evt = dev.read_one()
                                if evt and evt.type == ecodes.EV_KEY:
                                    k_event = categorize(evt)
                                    if k_event.keystate == 1:
                                        k = k_event.keycode
                                        if k == 'KEY_NEXTSONG':
                                            os.remove(f"{PLAYLIST_DIR}/{name}")
                                            speak("Deleted")
                                            return
                                        elif k == 'KEY_PREVIOUSSONG':
                                            speak("Cancel")
                                            break
                        elif choice == "Play":
                              #print(songs)
                              #print(songs[1])
                              for song in songs:
                               print(song)
                               #speak("Playlist done")
                               pygame.mixer.music.load(song)
                               pygame.mixer.music.play()
                               while pygame.mixer.music.get_busy():
                                event = dev.read_one()
                                if event and event.type == ecodes.EV_KEY:
                                 key_event = categorize(event)
                                 if key_event.keystate == 1:
                                  key = key_event.keycode
                                  if key == 'KEY_NEXTSONG':
                                   pygame.mixer.music.stop()
                                   #break

                              speak("Playlist done")
                              return
            except Exception as e:
                print(f"Manage playlist error: {e}")
def date_time():
    """This function speaks the date and time in a 12 hour format"""
    try:
        cmd = ["bash", "-c", 'date "+%A %B %e %r %Y"']
        fullcmd = ""
        for item in cmd:
                fullcmd += " " + item
        print(fullcmd)
        datetime = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(datetime.stderr)
        speak("The date and time is: " + datetime.stdout)
    except Exception as e:
        speak("Error getting date and time: " + str(e))

dev = InputDevice(INPUT_DEVICE) # Note to self: Why is this so late in the code lol
print(f"Listening on {INPUT_DEVICE}...")
while True:
    if daemonRunning: cmdq.process_Command()
    event = dev.read_one()
    if event and event.type == ecodes.EV_KEY:
        if True:
            key_event = categorize(event)
            if key_event.keystate == 1:
                key = key_event.keycode
                if key in ['KEY_PLAYCD', 'KEY_PAUSECD']:
                    toggle_pause()
                elif key == 'KEY_NEXTSONG':
                    if paused:
                        shutdown_menu()
                    else:
                        next_song()
                elif key == 'KEY_PREVIOUSSONG':
                   if not paused:
                    prev_song()
                   else:
                       date_time()
    if not pygame.mixer.music.get_busy() and not paused:
        sleep(0.5)
        next_song()
#Wed 25 Jun 04:21:16 2025
# Initialize command queue system
#command_queue = CommandQueue()
#c#ommand_queue.start_com# ================== END COMMAND QUEUE SYSTEM ==================
# Initialize command queue system (example usage)
#if __name__ == "__main__":
 #   # For multiprocessing demo
  #  with CommandQueue(enable_multiprocessing=True, verbose=True) as cmd_queue:
   #     # Add commands from main process
    #    cmd_queue.put_command("echo 'Hello from main process'")
     #   
        # Simulate adding commands from another proces#s
 #       def remote_worker(queue):
#            queue.put("echo 'Hello from remote process'")
      #      queue.put("python --version")
            
#        remote = multiprocessing.Process(
 #           target=remote_worker,
  #          args=(cmd_queue.queue,)
   #     )
    #    remote.start()
     #   remote.join()
        
     #   try:
    #        while True:
  #              # Main process can still add commands
   #             cmd_queue.put_command("date")
#                time.sleep(2)
#        except KeyboardInterrupt:
 #           print("\nShutting down...")
# ================== END ENHANCED COMMAND QUEUE SYSTEM ==================
