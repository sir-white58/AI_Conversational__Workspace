"""Connects the application to the Google Gemini API."""
import json
import os
import socket
import urllib.error
import urllib.request

from models.message import USER

API_URL = ("https://generativelanguage.googleapis.com/v1beta/models/"
           "{model}:generateContent")
DEFAULT_MODEL = "gemini-2.5-flash"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class AIServiceError(Exception):
    """Base class for every AI-related problem."""


class MissingAPIKeyError(AIServiceError):
    """No API key was found."""


class NetworkError(AIServiceError):
    """The internet connection failed or timed out."""


class APIResponseError(AIServiceError):
    """Gemini returned an error or an unusable reply."""


def load_env_file(path=None):
    """Read KEY=VALUE lines from a .env file into os.environ."""
    path = path or os.path.join(PROJECT_ROOT, ".env")
    try:
        with open(path, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
    except OSError:
        pass  # no .env file: the key may already be an environment variable


class AIService:
    """Builds requests, calls the Gemini API and returns the reply."""

    def __init__(self, api_key=None, model=None, timeout=60):
        load_env_file()
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model = model or os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
        self.timeout = timeout

    def build_request(self, instruction, history, new_message):
        """Mode instruction + earlier messages + the new message."""
        contents = []
        for message in history:
            role = "user" if message.sender == USER else "model"
            contents.append({"role": role, "parts": [{"text": message.text}]})
        contents.append({"role": "user", "parts": [{"text": new_message}]})
        return {"system_instruction": {"parts": [{"text": instruction}]},
                "contents": contents}

    def get_reply(self, instruction, history, new_message):
        """Send the request and return the AI's reply text."""
        if not new_message or not new_message.strip():
            raise AIServiceError("Cannot send an empty message.")
        if not self.api_key:
            raise MissingAPIKeyError(
                "No API key found. Add GEMINI_API_KEY=your_key to the .env "
                "file and restart the app.")

        body = json.dumps(self.build_request(instruction, history,
                                             new_message)).encode("utf-8")
        request = urllib.request.Request(
            API_URL.format(model=self.model), data=body, method="POST",
            headers={"Content-Type": "application/json",
                     "x-goog-api-key": self.api_key})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as reply:
                data = json.loads(reply.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            raise APIResponseError(self._describe_http_error(error))
        except (urllib.error.URLError, socket.timeout, TimeoutError):
            raise NetworkError("Could not reach Gemini. Check your internet "
                               "connection and try again.")
        except json.JSONDecodeError:
            raise APIResponseError("Gemini sent a reply that could not be read.")
        return self._extract_text(data)

    @staticmethod
    def _extract_text(data):
        try:
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(part.get("text", "") for part in parts).strip()
        except (KeyError, IndexError, TypeError, AttributeError):
            raise APIResponseError("Gemini returned no answer (the reply may "
                                   "have been blocked). Try rephrasing.")
        if not text:
            raise APIResponseError("Gemini returned an empty answer.")
        return text

    @staticmethod
    def _describe_http_error(error):
        try:
            detail = json.loads(error.read().decode("utf-8"))["error"]["message"]
        except Exception:
            detail = ""
        if error.code in (400, 401, 403):
            return ("Gemini rejected the request. Check that your API key is "
                    f"correct. {detail}").strip()
        if error.code == 429:
            return "Too many requests or quota reached. Wait a bit and retry."
        if error.code >= 500:
            return "Gemini is having problems right now. Try again shortly."
        return f"Gemini error {error.code}. {detail}".strip()
