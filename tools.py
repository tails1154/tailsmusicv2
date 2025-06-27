import subprocess
import threading
from evdev import InputDevice, categorize, ecodes, list_devices
import json
tts_lock = threading.Lock()
print("[tools.py] Reading config.json")
with open('config.json', 'r') as file:
 config = json.load(file)

print("[tools.py] Loaded config.json!")

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
 def checkRight(self, configentry):
  """Checks if right button is pressed from a config file entry. if so, return True. if not, return False"""
  if configentry == config['skipbutton']:
   return True
  else:
   return False
 def checkLeft(self, configentry):
  """Checks if the left button is pressed from a config file entry. if so, return True. if not, return False"""
  if configentry == config['backbutton']:
   return True
  else:
   return False
 def checkPlayPause(self, configentry):
  """Checks if the play/pause button is pressed from a config file entry. if so, return True. if not, return False"""
  if configentry == config['playbutton'] or configentry == config['playbutton2']:
   return True
  else:
   return False
 def getButtonEvent(self):
  """Gets a event from evtest module. If there is none, returns False. otherwise, return the key value which you can then use with checkPlayPause, checkLeft, checkRight, etc (note to self: wdym etc)"""
  event = self.device.read_one()
  if event and event.type == ecodes.EV_KEY:
   key_event = categorize(event)
   if key_event.keystate == 1:
    key = key_event.keycode
    return key
  return False
 def isRightPressed(self):
 # print("isRightPressed() called")
  """Checks if right is pressed. if so, return true. if not, return false."""
  event = self.device.read_one()
  if event and event.type == ecodes.EV_KEY:
   key_event = categorize(event)
   if key_event.keystate == 1:
    key = key_event.keycode
    if key == config['skipbutton']:
#      print("isRightPressed True")
      return True
   # else:
  return False
 def isLeftPressed(self):
     """Checks if left is pressed. If so, return True. if not, return False"""
  #   print("isLeftPressed() called")
     event = self.device.read_one()
     if event and event.type == ecodes.EV_KEY:
         key_event = categorize(event)
         if key_event.keystate == 1:
             key = key_event.keycode
             if key == config['backbutton']:
   #              print("isLeftPressed true")
                 return True
     return False
 def isPlayPausePressed(self):
    """Checks if the play/pause button is pressed. if so, return True. if not, return False."""
   # print("isPlayPausePressed() called")
    event = self.device.read_one()
    if event and event.type == ecodes.EV_KEY:
     key_event = categorize(event)
     if key_event.keystate == 1:
      key = key_event.keycode
      if key == config['okbutton'] or key == config['okbutton2']:
    #   print("isPlayPausedPressed True")
       return True
    return False
