"""A titled list of messages."""
from models.message import Message


class Conversation:
    """Stores a title and messages; can add a message and search its text."""

    def __init__(self, title):
        self.title = self._clean_title(title)
        self.messages = []

    @staticmethod
    def _clean_title(title):
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Conversation title cannot be empty.")
        return title.strip()

    def rename(self, new_title):
        self.title = self._clean_title(new_title)

    def add_message(self, sender, text):
        message = Message(sender, text)
        self.messages.append(message)
        return message

    def remove_last_message(self):
        if self.messages:
            self.messages.pop()

    def get_history(self):
        return list(self.messages)

    def search(self, word):
        word = word.strip().lower()
        if not word:
            return []
        return [m for m in self.messages if word in m.text.lower()]

    def to_dict(self):
        return {"title": self.title,
                "messages": [m.to_dict() for m in self.messages]}

    @classmethod
    def from_dict(cls, data):
        conversation = cls(data["title"])
        conversation.messages = [Message.from_dict(m) for m in data["messages"]]
        return conversation
