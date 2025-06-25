import requests
import sqlite3
import time
from typing import List, Dict, Optional
import threading
import tools

class PagerClient:
    def __init__(
        self,
        server_url: str,
        client_id: str,
        recipient_id: str = "default",
        offline_db: str = "offline_messages.db",
        poll_interval: int = 5
    ):
        """
        Initialize the pager client.
        
        Args:
            server_url (str): URL of your Node.js server (e.g., "http://10.0.0.1:3000").
            client_id (str): Unique ID for this device (e.g., "RPi-1").
            recipient_id (str): Who to listen for (e.g., "RPi-2").
            offline_db (str): SQLite file for offline storage.
            poll_interval (int): How often to check for new messages (seconds).
        """
        self.server_url = server_url
        self.client_id = client_id
        self.recipient_id = recipient_id
        self.offline_db = offline_db
        self.poll_interval = poll_interval
        
        # Set up offline DB
        self._init_offline_db()

    def _init_offline_db(self):
        """Initialize the local SQLite database for offline caching."""
        with sqlite3.connect(self.offline_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    sender TEXT,
                    recipient TEXT,
                    message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def send_message(self, message: str, recipient: Optional[str] = None):
        """
        Send a message to the server (or cache offline if no internet).
        
        Args:
            message (str): The message to send.
            recipient (str, optional): Override default recipient.
        """
        recipient = recipient or self.recipient_id
        try:
            response = requests.post(
                f"{self.server_url}/send",
                json={
                    "sender": self.client_id,
                    "recipient": recipient,
                    "message": message
                },
                timeout=3
            )
            if response.status_code == 200:
                print(f"Message sent to {recipient}!")
        except (requests.ConnectionError, requests.Timeout):
            self._cache_message(self.client_id, recipient, message)
            print("No internet — message cached offline.")

    def _cache_message(self, sender: str, recipient: str, message: str):
        """Store a message locally for later syncing."""
        with sqlite3.connect(self.offline_db) as conn:
            conn.execute(
                "INSERT INTO messages (sender, recipient, message) VALUES (?, ?, ?)",
                (sender, recipient, message)
            )

    def _sync_offline_messages(self):
        """Send all cached messages to the server (if internet is back)."""
        with sqlite3.connect(self.offline_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT sender, recipient, message FROM messages")
            rows = cursor.fetchall()
            
            for sender, recipient, message in rows:
                try:
                    response = requests.post(
                        f"{self.server_url}/send",
                        json={
                            "sender": sender,
                            "recipient": recipient,
                            "message": message
                        },
                        timeout=3
                    )
                    if response.status_code == 200:
                        cursor.execute(
                            "DELETE FROM messages WHERE sender=? AND recipient=? AND message=?",
                            (sender, recipient, message)
                        )
                        conn.commit()
                        print(f"Synced: {message}")
                except (requests.ConnectionError, requests.Timeout):
                    break  # Internet dropped again

    def check_messages(self) -> List[Dict]:
        """
        Fetch new messages from the server (or return empty list if offline).
        
        Returns:
            List[Dict]: [{"sender": str, "message": str, "timestamp": str}, ...]
        """
        try:
            response = requests.get(
                f"{self.server_url}/receive?recipient={self.client_id}",
                timeout=3
            )
            if response.status_code == 200:
                return response.json()
        except (requests.ConnectionError, requests.Timeout):
            print("Offline — can't fetch messages.")
        return []

    def run(self, api):
        """Main loop: Poll for messages and sync offline cache."""
        print(f"Pager client started (ID: {self.client_id}). Listening for messages...")
        while True:
            self._sync_offline_messages()
            messages = self.check_messages()
            for msg in messages:
               api.speak(f"[{msg['sender']}] {msg['message']}")
            if api.isRightPressed():
             return
            time.sleep(self.poll_interval)


# ===== Example Usage =====

class APP:
 def __init__(self, device):
  self.device = device
 def start(self):
     api = tools.API(self.device)
     # Configure your client
     client = PagerClient(
         server_url="http://192.168.0.107:3000",  # Replace with your Node.js server URL
         client_id="RPi-1",                       # Unique ID for this device
         recipient_id="RPi-2",                    # Who to listen for
         poll_interval=0                          # Check every 5 seconds
     )
     api.speak("Sending Page")
     # Send a test message
     client.send_message("Hello from the RPi!")
     api.speak("Waiting for page in background")
     # Start listening for messages
     client.run(api)
