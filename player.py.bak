import os
import pygame
from evdev import InputDevice, categorize, ecodes, list_devices
from time import sleep
import threading
import subprocess
import json

print("TailsMusic Loading...")
print("Modules: (7/7)")
print("All Modules Loaded!")

print("Finding SIMOLIO")
def find_simolio():
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

print("Starting Voice")
tts_lock = threading.Lock()
def speak(text):
    print(f"TTS: {text}")
    def run_tts():
        with tts_lock:
            try:
                subprocess.run(["espeak", text], check=True)
            except Exception as e:
                print(f"TTS subprocess error: {e}")
    threading.Thread(target=run_tts, daemon=True).start()

print("Loading Music Files")
playlist = [os.path.join(MUSIC_DIR, f) for f in os.listdir(MUSIC_DIR) if f.endswith('.mp3')]
if not playlist:
    speak("No songs found.")
    exit()

index = 0
paused = False
print("Loading Audio Driver")
pygame.mixer.init()
pygame.mixer.music.load(playlist[index])
pygame.mixer.music.play()

def next_song():
    global index
    index += 1
    if index >= len(playlist):
        speak("Playlist finished. Exiting.")
        exit(0)
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
        pygame.mixer.music.unpause()
    else:
        pygame.mixer.music.pause()
    paused = not paused

def shutdown_menu():
    options = ["Playlists", "Shut Down", "Back"]
    selected = 0
    speak(options[selected])
    while True:
        event = dev.read_one()
        if event and event.type == ecodes.EV_KEY:
            try:
                key_event = categorize(event)
                if key_event.keystate == 1:
                    key = key_event.keycode
                    if key == 'KEY_PREVIOUSSONG':
                        selected = (selected + 1) % len(options)
                        speak(options[selected])
                        sleep(1)
                    elif key == 'KEY_NEXTSONG':
                        choice = options[selected]
                        if choice == "Shut Down":
                            speak("Shutting down")
                            subprocess.run(["sudo", "shutdown", "now"])
                        elif choice == "Back":
                            return
                        elif choice == "Playlists":
                            playlist_menu()
                        break
            except Exception as e:
                print(f"Shutdown menu error: {e}")

def playlist_menu():
    def list_playlists():
        return [f for f in os.listdir(PLAYLIST_DIR) if f.endswith('.json')]

    while True:
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
                            sleep(1)
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

playlist_counter = 0
def create_playlist():
    global playlist_counter
    songs = []
    song_files = [f for f in os.listdir(MUSIC_DIR) if f.endswith('.mp3')]
    speak(f"Creating playlist {playlist_counter}")
    selected = 0
    while True:
        options = ["Add song", "Finish"]
        speak(options[selected])
        event = dev.read_one()
        if event and event.type == ecodes.EV_KEY:
            try:
                key_event = categorize(event)
                if key_event.keystate == 1:
                    key = key_event.keycode
                    if key == 'KEY_PREVIOUSSONG':
                        selected = (selected + 1) % len(options)
                        speak(options[selected])
                        sleep(1)
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
                                evt = dev.read_one()
                                if evt and evt.type == ecodes.EV_KEY:
                                    try:
                                        k_event = categorize(evt)
                                        if k_event.keystate == 1:
                                            k = k_event.keycode
                                            if k == 'KEY_PREVIOUSSONG':
                                                song_selected = (song_selected + 1) % len(song_files)
                                                speak(song_files[song_selected])
                                                sleep(1)
                                            elif k == 'KEY_NEXTSONG':
                                                songs.append(os.path.join(MUSIC_DIR, song_files[song_selected]))
                                                speak("Song added")
                                                break
                                    except Exception as e:
                                        print(f"Song selection error: {e}")
            except Exception as e:
                print(f"Create playlist error: {e}")

def manage_playlist(name):
    with open(f"{PLAYLIST_DIR}/{name}") as f:
        songs = json.load(f)
    options = ["Play", "Delete", "Back"]
    selected = 0
    speak(options[selected])
    while True:
        event = dev.read_one()
        if event and event.type == ecodes.EV_KEY:
            try:
                key_event = categorize(event)
                if key_event.keystate == 1:
                    key = key_event.keycode
                    if key == 'KEY_PREVIOUSSONG':
                        selected = (selected + 1) % len(options)
                        speak(options[selected])
                        sleep(1)
                    elif key == 'KEY_NEXTSONG':
                        choice = options[selected]
                        if choice == "Back":
                            return
                        elif choice == "Delete":
                            speak("Confirm delete")
                            while True:
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
                            for song in songs:
                                pygame.mixer.music.load(song)
                                pygame.mixer.music.play()
                                while pygame.mixer.music.get_busy():
                                    sleep(1)
                            speak("Playlist done")
                            return
            except Exception as e:
                print(f"Manage playlist error: {e}")

dev = InputDevice(INPUT_DEVICE)
print(f"Listening on {INPUT_DEVICE}...")
while True:
    event = dev.read_one()
    if event and event.type == ecodes.EV_KEY:
        try:
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
                    prev_song()
        except Exception as e:
            print(f"Main loop error: {e}")
    if not pygame.mixer.music.get_busy() and not paused:
        sleep(0.5)
        next_song()
