"""This is a example app that you can use as a template without needing to credit me."""


class APP: # Always make a app class
    def __init__(self, dev, queue): # If the app is a daemon, then also add a queue paramater so you can run commands on the main thread.
        """The __init__ function should have a dev paramater that gets autofilled. Here you should import your modules"""
        import tools # The tools library (should work) has some useful tools for making some basic ui elements for TailsMusic.
        self.dev = dev # This ensures you always have access to the headphone device.
        # Now, we need to make the tools api class.
        self.api = tools.API(self.dev) # Here is where we make the api. Note the self.dev is our device
    def checkDaemon(self):
     """TailsMusic Now requires that you have a checkDaemon() function that either returns True or False. If it is True, then the app will run in the background. if it is False, then run interactively"""
     return False # False because we are not a daemon
    def start(self):
        """ The start function is where you put your app code after creating your apis"""
        self.api.speak("Heya!") # The api.speak function speaks text to the user.
        self.api.speak("Press skip to exit.")
        while True:
            if self.api.isRightPressed(): # api.isRightPressed returns true when the Skip button is pressed
                self.api.speak("Exiting")
                return # Return should exit the app
