"""File handling: saving, loading and exporting workspaces."""
import json
import os

from models.workspace import Workspace


class DataError(Exception):
    """Raised when a file cannot be read, written or understood."""


class DataManager:
    """Reads and writes all files used by the application."""

    def __init__(self, folder=None):
        if folder is None:
            folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "saved")
        self.folder = folder
        self.file_path = os.path.join(folder, "workspaces.json")

    def load_workspaces(self):
        """Load saved workspaces. Returns [] when nothing is saved yet."""
        if not os.path.exists(self.file_path):
            return []
        try:
            with open(self.file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
            return [Workspace.from_dict(item) for item in data["workspaces"]]
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            self._backup_corrupted_file()
            raise DataError("The saved data file was damaged. A backup copy "
                            "was kept and the app will start empty.")
        except OSError as error:
            raise DataError(f"Could not read the saved data: {error}")

    def save_workspaces(self, workspaces):
        """Save all workspaces. Writes to a temp file first so a crash
        cannot leave a half-written file."""
        payload = {"workspaces": [w.to_dict() for w in workspaces]}
        temp_path = self.file_path + ".tmp"
        try:
            os.makedirs(self.folder, exist_ok=True)
            with open(temp_path, "w", encoding="utf-8") as file:
                json.dump(payload, file, indent=2, ensure_ascii=False)
            os.replace(temp_path, self.file_path)
        except OSError as error:
            raise DataError(f"Could not save your data: {error}")

    def export_conversation(self, conversation, path, workspace_name=""):
        """Export one conversation to a plain text file."""
        lines = [f"Conversation: {conversation.title}"]
        if workspace_name:
            lines.append(f"Workspace: {workspace_name}")
        lines.append("=" * 40)
        lines.extend(str(message) for message in conversation.messages)
        try:
            with open(path, "w", encoding="utf-8") as file:
                file.write("\n\n".join(lines) + "\n")
        except OSError as error:
            raise DataError(f"Could not export the conversation: {error}")

    def _backup_corrupted_file(self):
        backup = os.path.join(self.folder, "workspaces.corrupted.json")
        try:
            os.replace(self.file_path, backup)
        except OSError:
            pass
