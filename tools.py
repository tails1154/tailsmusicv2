import subprocess
import threading
from evdev import InputDevice, categorize, ecodes, list_devices
tts_lock = threading.Lock()


class API:
 def __init__(self, device):
  self.device = device
 def speak(self, text):
  """Speaks text to the user"""
  print(f"TTS: {text}")
  subprocess.run(["espeak-ng", text], check=True)
#  def run_tts():
 #  with tts_lock:
  #  try:
     #subprocess.run(["espeak", text], check=True)
   # except Exception as e:
    # print("Exception: " + str(e))
#  threading.Thread(target=run_tts, daemon=True).start()
 def isRightPressed(self):
  """Checks if right is pressed. if so, return true. if not, return false."""
  event = self.device.read_one()
  if event and event.type == ecodes.EV_KEY:
   key_event = categorize(event)
   if key_event.keystate == 1:
    key = key_event.keycode
    if key == "KEY_NEXTSONG":
      return True
   # else:
  return False
 def isLeftPressed(self):
     """Checks if left is pressed. If so, return True. if not, return False"""
     event = self.device.read_one()
     if event and event.tpye == ecodes.EV_KEY:
         key_event = categorize(event)
         if key_event.keystate == 1:
             key = key_event.keycode
             if key == "KEY_PREVIOUSSONG":
                 return True
     return False
