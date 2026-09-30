"""Run with:  python -m unittest discover tests"""
import os
import tempfile
import unittest

from api.ai_service import AIService, APIResponseError, MissingAPIKeyError
from data.data_manager import DataError, DataManager
from models.message import AI, USER
from models.workspace import Workspace


class ModelTests(unittest.TestCase):
    def test_empty_message_rejected(self):
        ws = Workspace("W")
        convo = ws.add_conversation("C")
        with self.assertRaises(ValueError):
            convo.add_message(USER, "   ")

    def test_search_is_case_insensitive(self):
        convo = Workspace("W").add_conversation("C")
        convo.add_message(USER, "What is a List?")
        convo.add_message(AI, "A tuple is different.")
        self.assertEqual(len(convo.search("list")), 1)
        self.assertEqual(convo.search(""), [])

    def test_workspace_search_across_conversations(self):
        ws = Workspace("W")
        ws.add_conversation("A").add_message(USER, "python is fun")
        ws.add_conversation("B").add_message(USER, "hello")
        self.assertEqual(len(ws.search("python")), 1)


class DataTests(unittest.TestCase):
    def test_save_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            manager = DataManager(folder)
            ws = Workspace("Study", "Tutor")
            ws.add_conversation("Loops").add_message(USER, "Explain for loops")
            manager.save_workspaces([ws])
            loaded = manager.load_workspaces()
            self.assertEqual(loaded[0].name, "Study")
            self.assertEqual(loaded[0].conversations[0].messages[0].text,
                             "Explain for loops")

    def test_corrupted_file_raises_data_error(self):
        with tempfile.TemporaryDirectory() as folder:
            manager = DataManager(folder)
            with open(manager.file_path, "w") as file:
                file.write("{ not valid json")
            with self.assertRaises(DataError):
                manager.load_workspaces()

    def test_missing_file_gives_empty_list(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(DataManager(folder).load_workspaces(), [])

    def test_export_writes_text_file(self):
        with tempfile.TemporaryDirectory() as folder:
            manager = DataManager(folder)
            convo = Workspace("W").add_conversation("Chat")
            convo.add_message(USER, "hi")
            path = os.path.join(folder, "out.txt")
            manager.export_conversation(convo, path, "W")
            with open(path, encoding="utf-8") as file:
                self.assertIn("hi", file.read())


class AIServiceTests(unittest.TestCase):
    def test_request_contains_mode_history_and_new_message(self):
        convo = Workspace("W").add_conversation("C")
        convo.add_message(USER, "first")
        convo.add_message(AI, "answer")
        request = AIService(api_key="x").build_request(
            "Be a tutor", convo.get_history(), "second")
        roles = [item["role"] for item in request["contents"]]
        self.assertEqual(roles, ["user", "model", "user"])
        self.assertEqual(request["system_instruction"]["parts"][0]["text"],
                         "Be a tutor")

    def test_missing_key_raises(self):
        service = AIService(api_key="")
        service.api_key = ""
        with self.assertRaises(MissingAPIKeyError):
            service.get_reply("x", [], "hello")

    def test_bad_reply_shape_raises(self):
        with self.assertRaises(APIResponseError):
            AIService._extract_text({"candidates": []})


if __name__ == "__main__":
    unittest.main()
