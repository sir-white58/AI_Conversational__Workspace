"""A single chat message."""
from datetime import datetime

USER = "user"
AI = "ai"


class Message:
    """Stores who sent a message, its text and the time it was sent."""

    def __init__(self, sender, text, timestamp=None):
        if sender not in (USER, AI):
            raise ValueError(f"Sender must be '{USER}' or '{AI}'.")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Message cannot be empty.")
        self.sender = sender
        self.text = text.strip()
        self.timestamp = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M")

    def to_dict(self):
        return {"sender": self.sender, "text": self.text,
                "timestamp": self.timestamp}

    @classmethod
    def from_dict(cls, data):
        return cls(data["sender"], data["text"], data["timestamp"])

    def __str__(self):
        name = "You" if self.sender == USER else "AI"
        return f"[{self.timestamp}] {name}: {self.text}"
