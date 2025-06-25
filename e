# ================== NEW COMMAND QUEUE SYSTEM ==================
class CommandQueue:
    def __init__(self):
        self.queue = queue.Queue()
        self.running = True
        
    def start_command_listener(self):
        """Start a background thread that listens for console commands"""
        def listener():
            while self.running:
                try:
                    cmd = input(">>> " if sys.stdin.isatty() else "")
                    if cmd.strip():
                        self.queue.put(cmd)
                except (EOFError, KeyboardInterrupt):
                    break
                    
        threading.Thread(target=listener, daemon=True).start()
        
    def process_commands(self):
        """Process any pending commands in the queue (call this in main loop)"""
        while not self.queue.empty():
            cmd = self.queue.get_nowait()
            try:
                print(f"Executing: {cmd}")
                result = subprocess.run(cmd, shell=True, 
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     text=True)
                if result.stdout: print(result.stdout)
                if result.stderr: print(result.stderr, file=sys.stderr)
            except Exception as e:
                print(f"Command error: {e}")

# Initialize command queue system
command_queue = CommandQueue()
command_queue.start_command_listener()
# ================== END COMMAND QUEUE SYSTEM ==================
