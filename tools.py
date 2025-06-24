import subprocess
import threading



def speak(text):
 print(f"TTS: {text}")
 def run_tts():
  with tts_lock:
   try:
    subprocess.run(["espeak", text], check=True)
   except Exception as e:
    print("Exception: " + str(e))
 threading.Thread(target=run_tts, daemon=True).start()
