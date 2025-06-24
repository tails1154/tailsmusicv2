import subprocess
import threading
from evdev import InputDevice, categorize, ecodes, list_devices
tts_lock = threading.Lock()




class API:
 def __init__(self, device):
  self.device = device
 def speak(self, text):
  print(f"TTS: {text}")
  def run_tts():
   with tts_lock:
    try:
     subprocess.run(["espeak", text], check=True)
    except Exception as e:
     print("Exception: " + str(e))
  threading.Thread(target=run_tts, daemon=True).start()
 def isRightPressed(self):
  event = self.device.read_one()
  if event and event.type == ecodes.EV_KEY:
   key_event = categorize(event)
   if key_event.keystate == 1:
    key = key_event.keycode
    if key == "KEY_NEXTSONG":
      return True
   # else:
  return False
