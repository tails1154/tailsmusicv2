import subprocess
import tools


class APP:
	def __init__(self, dev, q=None):
		self.dev = dev
		subprocess.run(["cp", "apps/pager.py", "./pager.py"], check=True)
		import pager
	def start(self):
		api = tools.API(self.dev)
		api.speak("Loading...")
		
