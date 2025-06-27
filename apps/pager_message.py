import subprocess
import tools
subprocess.run(["cp", "apps/pager.py", "./pager.py"], check=True)
import pager


class APP:
	def __init__(self, dev, q=None):
		self.dev = dev
	def checkDaemon(self):
	        return False
	def start(self):
		api = tools.API(self.dev)
		api.speak("Loading...")
		self.device = self.dev # Why am I doing this to myself :(
		api = tools.API(self.device)
		# Configure your client
		client = pager.PagerClient(
		 server_url="http://192.168.0.107:3000",  # Replace with your Node.js server UR
		 client_id="RPi-1",                       # Unique ID for this device
		 recipient_id="webui",                    # Who to listen for
		 poll_interval=0                          # Check every 5 seconds
		)
		client.sync_offline_messages()
		options = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "space", "Send"]
		index = 0
		toSend = ""
		api.speak(options[index])
		while True:
		    if tools.isLeftPressed():
		        index = (index + 1) % len(options)
		    if tools.isPlayPausePressed():
		        index = (index - 1) % len(options)
		    if tools.isRightPressed():
		        selection = options[index]
		        if selection == "space":
		            toSend += " "
		        elif selection == "Send":
		            api.speak("Sending Message...")
		            client.send_message(toSend, "all")
		            api.speak("Sent Message! (May be cached for sending on next startup.)")
		            break
		        else:
		            toSend += selection
		subprocess.run(["rm", "-rf", "./pager.py"], check=True)
