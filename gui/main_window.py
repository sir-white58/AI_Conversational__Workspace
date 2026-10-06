"""The main window: connects the GUI, the models, the files and the AI."""
import os
import queue
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

from api.ai_service import PROJECT_ROOT, AIService, AIServiceError
from data.data_manager import DataError, DataManager
from gui import dialogs
from gui.chat_panel import ChatPanel
from gui.sidebar import Sidebar
from gui.theme import T
from models.message import AI, USER
from models.workspace import DEFAULT_MODE, Workspace

DEFAULT_TITLES = ("New chat", "First chat")


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI Conversational Workspace")
        self.geometry("1200x780")
        self.minsize(900, 600)

        self.data_manager = DataManager()
        self.ai_service = AIService()
        self.workspaces, self.ws, self.conv = [], None, None
        self.pending = None               # conversation waiting for an AI reply
        self.expanded = set()             # workspaces open in the sidebar
        self.replies = queue.Queue()      # the AI thread puts results here
        self.provider = "auto"            # which AI to use: auto / gemini / groq

        self._load_data()
        self.build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._check_replies)
        self.bind("<Control-n>", lambda e: self.ws and self.new_conversation(self.ws))
        self.bind("<Control-f>", lambda e: self.sidebar.search.focus_set())

    def report_callback_exception(self, *args):
        """Never crash because of an error inside a GUI callback."""
        messagebox.showerror("Something went wrong", str(args[1]), parent=self)

    # ---------- layout ----------
    def build(self):
        for w in self.winfo_children():
            w.destroy()
        self.configure(bg=T.c["bg"])
        self.sidebar = Sidebar(self, self)
        self.sidebar.pack(side="left", fill="y")
        tk.Frame(self, bg=T.c["border"], width=1).pack(side="left", fill="y")
        self.chat = ChatPanel(self, self)
        self.chat.pack(side="left", fill="both", expand=True)
        self.refresh()
        self.chat.set_busy(self.pending is not None)

    def refresh(self):
        self.sidebar.refresh()
        self.chat.show(self.ws, self.conv)

    def toggle_theme(self):
        T.toggle()
        self.build()

    # ---------- data ----------
    def _load_data(self):
        try:
            self.workspaces = self.data_manager.load_workspaces()
        except DataError as error:
            messagebox.showwarning("Loading problem", str(error))
            self.workspaces = []
        if not self.workspaces:
            starter = Workspace("My Workspace", DEFAULT_MODE)
            starter.add_conversation("First chat")
            self.workspaces.append(starter)
            self._save()
        self.ws = self.workspaces[0]
        self.conv = self.ws.conversations[0] if self.ws.conversations else None
        self.expanded.add(self.ws)

    def _save(self):
        try:
            self.data_manager.save_workspaces(self.workspaces)
        except DataError as error:
            messagebox.showerror("Save problem", str(error))

    def _on_close(self):
        self._save()
        self.destroy()

    def _first(self, ws):
        return ws.conversations[0] if ws and ws.conversations else None

    def select(self, ws, conv):
        self.ws, self.conv = ws, conv
        self.expanded.add(ws)
        self.refresh()

    # ---------- workspaces ----------
    def new_workspace(self):
        result = dialogs.WorkspaceDialog(self, "New workspace").show()
        if not result:
            return
        try:
            workspace = Workspace(*result)
        except ValueError as error:
            messagebox.showwarning("Invalid name", str(error))
            return
        self.workspaces.append(workspace)
        conv = self._new_conv(workspace)
        self._save()
        self.select(workspace, conv)

    def edit_workspace(self, ws):
        result = dialogs.WorkspaceDialog(self, "Edit workspace", ws.name, ws.mode).show()
        if not result:
            return
        try:
            ws.rename(result[0])
        except ValueError as error:
            messagebox.showwarning("Invalid name", str(error))
            return
        ws.mode = result[1]
        self._save()
        self.refresh()

    def delete_workspace(self, ws):
        if not messagebox.askyesno("Delete workspace",
                                   f"Delete '{ws.name}' and all its conversations?", parent=self):
            return
        self.workspaces.remove(ws)
        self.expanded.discard(ws)
        if ws is self.ws:
            self.ws = self.workspaces[0] if self.workspaces else None
            self.conv = self._first(self.ws)
        self._save()
        self.refresh()

    # ---------- conversations ----------
    def _new_conv(self, ws):
        conv = ws.add_conversation("New chat")
        ws.conversations.remove(conv)
        ws.conversations.insert(0, conv)          # newest chat on top
        return conv

    def new_conversation(self, ws):
        conv = self._new_conv(ws)
        self._save()
        self.select(ws, conv)

    def rename_conversation(self, conv):
        title = dialogs.AskText(self, "Rename chat", "New title:", conv.title).show()
        if not title:
            return
        try:
            conv.rename(title)
        except ValueError as error:
            messagebox.showwarning("Invalid title", str(error))
            return
        self._save()
        self.refresh()

    def delete_conversation(self, ws, conv):
        if not messagebox.askyesno("Delete chat", f"Delete '{conv.title}'?", parent=self):
            return
        ws.remove_conversation(conv)
        if conv is self.conv:
            self.conv = self._first(ws)
        self._save()
        self.refresh()

    def export_conversation(self, conv=None, ws=None):
        conv, ws = conv or self.conv, ws or self.ws
        if conv is None or not conv.messages:
            self.chat.toast("Nothing to export yet")
            return
        name = re.sub(r"[^\w\- ]", "", conv.title).strip() or "conversation"
        path = filedialog.asksaveasfilename(
            title="Export conversation", defaultextension=".txt", initialfile=name + ".txt",
            filetypes=[("Text files", "*.txt")])
        if not path:
            return
        try:
            self.data_manager.export_conversation(conv, path, ws.name if ws else "")
        except DataError as error:
            messagebox.showerror("Export problem", str(error))
            return
        self.chat.toast("Exported ✓", ok=True)

    # ---------- chat ----------
    def _ask_for_key(self):
        """First-run helper: ask for the Gemini key and store it in .env."""
        key = dialogs.AskText(self, "Gemini API key",
                              "Paste your Gemini API key (kept only on this computer, in .env):",
                              show="*").show()
        if not key:
            return False
        self.ai_service.api_key = key
        path = os.path.join(PROJECT_ROOT, ".env")
        try:
            lines = []
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    lines = [l.rstrip("\n") for l in f if not l.startswith("GEMINI_API_KEY")]
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines + [f"GEMINI_API_KEY={key}"]) + "\n")
        except OSError:
            self.chat.toast("Key not saved to .env; it will work until you close the app")
        return True

    def send_message(self, text):
        """Returns True if the message was accepted."""
        text = (text or "").strip()
        if self.ws is None:
            self.chat.toast("Create a workspace first")
            return False
        if not text:
            self.chat.toast("Type a message first")
            return False
        if self.pending:
            self.chat.toast("Still waiting for the last reply…")
            return False
        placeholder = not self.ai_service.api_key or self.ai_service.api_key.startswith("paste_your")
        needs_key = placeholder and self.provider != "groq" and not self.ai_service.groq_key
        if needs_key and not self._ask_for_key():
            return False
        if self.conv is None:
            self.conv = self._new_conv(self.ws)
        conv = self.conv
        first = not conv.messages
        message = conv.add_message(USER, text)
        if first and conv.title in DEFAULT_TITLES:
            conv.title = text[:32] + ("…" if len(text) > 32 else "")
        history = conv.get_history()[:-1]          # everything before this message
        self.chat.clear_input()
        if first:
            self.chat.show(self.ws, conv)
        else:
            self.chat.add_bubble(message)
        self.sidebar.refresh()
        self.pending = conv
        self.chat.set_busy(True)
        threading.Thread(target=self._ask_ai, daemon=True,
                         args=(self.ws.get_instruction(), history, text, conv, self.provider)).start()
        return True

    def _ask_ai(self, instruction, history, text, conv, provider):
        """Runs in a background thread so the window never freezes."""
        try:
            reply = self.ai_service.get_reply(instruction, history, text, provider=provider)
            self.replies.put(("ok", reply, text, conv))
        except AIServiceError as error:
            self.replies.put(("error", str(error), text, conv))
        except Exception as error:                 # anything unexpected
            self.replies.put(("error", f"Unexpected error: {error}", text, conv))

    def _check_replies(self):
        try:
            while True:
                self._handle_reply(*self.replies.get_nowait())
        except queue.Empty:
            pass
        self.after(100, self._check_replies)

    def _handle_reply(self, status, payload, text, conv):
        self.pending = None
        self.chat.set_busy(False)
        if status == "ok":
            message = conv.add_message(AI, payload)
            self._save()                           # saved after every exchange
            self.chat.set_status(f"Answered by {self.ai_service.last_provider}")
            if conv is self.conv:
                self.chat.add_bubble(message, animate=True)
        else:
            conv.remove_last_message()             # take back the unanswered message
            self.sidebar.refresh()
            if conv is self.conv:
                self.chat.show(self.ws, conv)
                self.chat.set_input(text)
                self.chat.add_error(payload, lambda: self.send_message(text))