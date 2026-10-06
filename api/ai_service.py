"""Connects the application to AI models (Gemini and Groq)."""
import json
import os
import socket
import time
import urllib.error
import urllib.request

from models.message import USER

API_URL = ("https://generativelanguage.googleapis.com/v1beta/models/"
           "{model}:generateContent")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "gemini-flash-latest"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
RETRY_CODES = (429, 500, 502, 503, 504)  # temporary problems worth retrying
PROVIDERS = ("auto", "gemini", "groq")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class AIServiceError(Exception):
    """Base class for every AI-related problem."""


class MissingAPIKeyError(AIServiceError):
    """No API key was found."""


class NetworkError(AIServiceError):
    """The internet connection failed or timed out."""


class APIResponseError(AIServiceError):
    """The AI returned an error or an unusable reply."""


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
    """Builds requests and calls Gemini (with retries and fallback models)
    or Groq. After each reply, `last_provider` tells who answered."""

    def __init__(self, api_key=None, model=None, timeout=15, retries=2):
        load_env_file()
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        main_model = model or os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
        extra = os.environ.get("GEMINI_FALLBACK_MODELS", "")
        self.models = [main_model] + [m.strip() for m in extra.split(",")
                                      if m.strip()]
        self.model = main_model
        self.groq_key = os.environ.get("GROQ_API_KEY", "")
        self.groq_model = os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)
        self.timeout = timeout
        self.retries = retries
        self.last_provider = ""      # e.g. "Gemini (gemini-flash-latest)"
        self.last_gemini_model = ""

    # ------------------------------------------------------------ Gemini
    def build_request(self, instruction, history, new_message):
        """Mode instruction + earlier messages + the new message."""
        contents = []
        for message in history:
            role = "user" if message.sender == USER else "model"
            contents.append({"role": role, "parts": [{"text": message.text}]})
        contents.append({"role": "user", "parts": [{"text": new_message}]})
        return {"system_instruction": {"parts": [{"text": instruction}]},
                "contents": contents}

    def _call_gemini(self, model, body):
        request = urllib.request.Request(
            API_URL.format(model=model), data=body, method="POST",
            headers={"Content-Type": "application/json",
                     "x-goog-api-key": self.api_key})
        with urllib.request.urlopen(request, timeout=self.timeout) as reply:
            return json.loads(reply.read().decode("utf-8"))

    def _gemini_reply(self, instruction, history, new_message):
        """Try each Gemini model, retrying temporary errors with backoff."""
        if not self.api_key:
            raise MissingAPIKeyError(
                "No API key found. Add GEMINI_API_KEY=your_key to the .env "
                "file and restart the app.")

        body = json.dumps(self.build_request(instruction, history,
                                             new_message)).encode("utf-8")
        last_error = None
        for model in self.models:
            for attempt in range(self.retries):
                try:
                    text = self._extract_text(self._call_gemini(model, body))
                    self.last_gemini_model = model
                    return text
                except urllib.error.HTTPError as error:
                    last_error = APIResponseError(
                        self._describe_http_error(error))
                    if error.code not in RETRY_CODES:
                        raise last_error  # e.g. bad key: retrying won't help
                except (urllib.error.URLError, socket.timeout, TimeoutError):
                    last_error = NetworkError(
                        "Could not reach Gemini. Check your internet "
                        "connection and try again.")
                except json.JSONDecodeError:
                    raise APIResponseError(
                        "Gemini sent a reply that could not be read.")
                if attempt < self.retries - 1:
                    time.sleep(2 ** attempt)  # wait 1s, then 2s, ...
        raise last_error

    # -------------------------------------------------------------- Groq
    def _groq_reply(self, instruction, history, new_message):
        """Groq model: fast, also used as the backup in 'auto' mode."""
        if not self.groq_key:
            raise MissingAPIKeyError(
                "No GROQ_API_KEY found. Add GROQ_API_KEY=your_key to the "
                ".env file and restart the app.")

        messages = [{"role": "system", "content": instruction}]
        for message in history:
            role = "user" if message.sender == USER else "assistant"
            messages.append({"role": role, "content": message.text})
        messages.append({"role": "user", "content": new_message})

        body = json.dumps({"model": self.groq_model,
                           "messages": messages}).encode("utf-8")
        request = urllib.request.Request(
            GROQ_URL, data=body, method="POST",
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.groq_key}",
                     "User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as reply:
                data = json.loads(reply.read().decode("utf-8"))
            text = data["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as error:
            raise APIResponseError(f"Groq error {error.code}.")
        except (urllib.error.URLError, socket.timeout, TimeoutError):
            raise NetworkError("Could not reach Groq. Check your internet "
                               "connection and try again.")
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            raise APIResponseError("Groq returned an unreadable reply.")
        if not text:
            raise APIResponseError("Groq returned an empty answer.")
        return text

    # ------------------------------------------------------------ public
    def get_reply(self, instruction, history, new_message, provider="auto"):
        """Send the request and return the AI's reply text.

        provider: 'auto' (Gemini, then Groq as backup), 'gemini' or 'groq'.
        """
        if not new_message or not new_message.strip():
            raise AIServiceError("Cannot send an empty message.")
        if provider not in PROVIDERS:
            provider = "auto"

        if provider == "groq":
            reply = self._groq_reply(instruction, history, new_message)
            self.last_provider = f"Groq ({self.groq_model})"
            return reply

        if provider == "gemini":
            reply = self._gemini_reply(instruction, history, new_message)
            self.last_provider = f"Gemini ({self.last_gemini_model})"
            return reply

        # auto: Gemini first, Groq as backup
        try:
            reply = self._gemini_reply(instruction, history, new_message)
            self.last_provider = f"Gemini ({self.last_gemini_model})"
            return reply
        except AIServiceError as gemini_error:
            if not self.groq_key:
                raise gemini_error  # no backup configured
            try:
                reply = self._groq_reply(instruction, history, new_message)
                self.last_provider = f"Groq ({self.groq_model})"
                return reply
            except AIServiceError:
                raise gemini_error  # show the main (Gemini) problem

    # ----------------------------------------------------------- helpers
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