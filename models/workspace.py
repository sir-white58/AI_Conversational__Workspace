"""A named workspace with an AI mode and its own conversations."""
from models.conversation import Conversation

MODES = {
    "General Assistant": "You are a helpful, clear and friendly assistant.",
    "Tutor": ("You are a patient tutor. Explain ideas step by step in simple "
              "language, give small examples, and check the learner's "
              "understanding with a short question at the end."),
    "Coding Helper": ("You are an expert programming assistant. Give correct, "
                      "readable code with short explanations, point out bugs "
                      "and suggest best practices."),
    "Writing Assistant": ("You are a writing assistant. Help plan, draft and "
                          "improve text. Keep the user's voice and give "
                          "clear, constructive suggestions."),
}
DEFAULT_MODE = "General Assistant"


class Workspace:
    """Stores a name, an AI mode and a list of conversations."""

    def __init__(self, name, mode=DEFAULT_MODE):
        self.name = self._clean_name(name)
        self.mode = mode
        self.conversations = []

    @staticmethod
    def _clean_name(name):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Workspace name cannot be empty.")
        return name.strip()

    def rename(self, new_name):
        self.name = self._clean_name(new_name)

    def get_instruction(self):
        """The instruction sent to the AI with every request."""
        return MODES.get(self.mode, MODES[DEFAULT_MODE])

    def add_conversation(self, title):
        conversation = Conversation(title)
        self.conversations.append(conversation)
        return conversation

    def remove_conversation(self, conversation):
        if conversation in self.conversations:
            self.conversations.remove(conversation)

    def search(self, word):
        """Return (conversation, message) pairs whose text contains word."""
        results = []
        for conversation in self.conversations:
            for message in conversation.search(word):
                results.append((conversation, message))
        return results

    def to_dict(self):
        return {"name": self.name, "mode": self.mode,
                "conversations": [c.to_dict() for c in self.conversations]}

    @classmethod
    def from_dict(cls, data):
        workspace = cls(data["name"], data["mode"])
        workspace.conversations = [Conversation.from_dict(c)
                                   for c in data["conversations"]]
        return workspace
