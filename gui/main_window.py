"""The main window: connects the GUI, the models, the files and the AI."""
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from api.ai_service import AIService, AIServiceError
from data.data_manager import DataError, DataManager
from gui.chat_panel import ChatPanel
from gui.dialogs import SearchResultsDialog, WorkspaceDialog
from gui.sidebar import Sidebar
from models.message import AI, USER
from models.workspace import DEFAULT_MODE, Workspace


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI Conversational Workspace")
        self.geometry("1050x680")
        self.minsize(820, 520)

        self.data_manager = DataManager()
        self.ai_service = AIService()
        self.workspaces = []
        self.ws_index = None
        self.conv_index = None
        self.waiting = False
        self.replies = queue.Queue()   # the AI thread puts results here

        self._build_layout()
        self._load_data()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._check_replies)

    # ---------- layout ----------
    def _build_layout(self):
        actions = {
            "select_workspace": self.select_workspace,
            "new_workspace": self.new_workspace,
            "rename_workspace": self.rename_workspace,
            "delete_workspace": self.delete_workspace,
            "select_conversation": self.select_conversation,
            "new_conversation": self.new_conversation,
            "rename_conversation": self.rename_conversation,
            "delete_conversation": self.delete_conversation,
        }
        panes = ttk.PanedWindow(self, orient="horizontal")
        panes.pack(fill="both", expand=True)
        self.sidebar = Sidebar(panes, actions)
        self.chat = ChatPanel(panes, self.send_message, self.export_conversation,
                              self.search_workspace)
        panes.add(self.sidebar, weight=0)
        panes.add(self.chat, weight=1)
        self.sidebar.configure(width=270)

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
        self.ws_index = 0
        self.conv_index = 0 if self.workspaces[0].conversations else None
        self._refresh()

    def _save(self):
        try:
            self.data_manager.save_workspaces(self.workspaces)
        except DataError as error:
            messagebox.showerror("Save problem", str(error))

    def _on_close(self):
        self._save()
        self.destroy()

    # ---------- current selection ----------
    def _workspace(self):
        if self.ws_index is None or self.ws_index >= len(self.workspaces):
            return None
        return self.workspaces[self.ws_index]

    def _conversation(self):
        workspace = self._workspace()
        if (workspace is None or self.conv_index is None
                or self.conv_index >= len(workspace.conversations)):
            return None
        return workspace.conversations[self.conv_index]

    def _refresh(self):
        self.sidebar.show_workspaces([w.name for w in self.workspaces],
                                     self.ws_index)
        workspace = self._workspace()
        if workspace is None:
            self.sidebar.show_conversations([], None)
            self.chat.show_empty("No workspace", "Create a workspace to begin.")
            return
        self.sidebar.show_conversations(
            [c.title for c in workspace.conversations], self.conv_index)
        header = f"{workspace.name}  ·  {workspace.mode}"
        conversation = self._conversation()
        if conversation is None:
            self.chat.show_empty(header, "Create or select a conversation.")
        else:
            self.chat.show_conversation(f"{header}  ·  {conversation.title}",
                                        conversation)
            self.chat.focus_input()

    # ---------- workspaces ----------
    def select_workspace(self, index):
        self.ws_index = index
        workspace = self._workspace()
        self.conv_index = 0 if workspace and workspace.conversations else None
        self._refresh()

    def new_workspace(self):
        dialog = WorkspaceDialog(self, "New workspace")
        if dialog.result is None:
            return
        name, mode = dialog.result
        try:
            workspace = Workspace(name, mode)
        except ValueError as error:
            messagebox.showwarning("Invalid name", str(error))
            return
        workspace.add_conversation("New chat")
        self.workspaces.append(workspace)
        self.ws_index = len(self.workspaces) - 1
        self.conv_index = 0
        self._save()
        self._refresh()

    def rename_workspace(self):
        workspace = self._workspace()
        if workspace is None:
            messagebox.showinfo("No workspace", "Select a workspace first.")
            return
        dialog = WorkspaceDialog(self, "Edit workspace", workspace.name,
                                 workspace.mode)
        if dialog.result is None:
            return
        try:
            workspace.rename(dialog.result[0])
        except ValueError as error:
            messagebox.showwarning("Invalid name", str(error))
            return
        workspace.mode = dialog.result[1]
        self._save()
        self._refresh()

    def delete_workspace(self):
        workspace = self._workspace()
        if workspace is None:
            messagebox.showinfo("No workspace", "Select a workspace first.")
            return
        if not messagebox.askyesno(
                "Delete workspace",
                f"Delete '{workspace.name}' and all its conversations?"):
            return
        self.workspaces.remove(workspace)
        self.ws_index = 0 if self.workspaces else None
        first = self._workspace()
        self.conv_index = 0 if first and first.conversations else None
        self._save()
        self._refresh()

    # ---------- conversations ----------
    def select_conversation(self, index):
        self.conv_index = index
        self._refresh()

    def new_conversation(self):
        workspace = self._workspace()
        if workspace is None:
            messagebox.showinfo("No workspace", "Create a workspace first.")
            return
        title = simpledialog.askstring("New conversation",
                                       "Conversation title:",
                                       initialvalue="New chat", parent=self)
        if title is None:
            return
        try:
            workspace.add_conversation(title)
        except ValueError as error:
            messagebox.showwarning("Invalid title", str(error))
            return
        self.conv_index = len(workspace.conversations) - 1
        self._save()
        self._refresh()

    def rename_conversation(self):
        conversation = self._conversation()
        if conversation is None:
            messagebox.showinfo("No conversation", "Select a conversation first.")
            return
        title = simpledialog.askstring("Rename conversation", "New title:",
                                       initialvalue=conversation.title,
                                       parent=self)
        if title is None:
            return
        try:
            conversation.rename(title)
        except ValueError as error:
            messagebox.showwarning("Invalid title", str(error))
            return
        self._save()
        self._refresh()

    def delete_conversation(self):
        workspace, conversation = self._workspace(), self._conversation()
        if conversation is None:
            messagebox.showinfo("No conversation", "Select a conversation first.")
            return
        if not messagebox.askyesno("Delete conversation",
                                   f"Delete '{conversation.title}'?"):
            return
        workspace.remove_conversation(conversation)
        self.conv_index = 0 if workspace.conversations else None
        self._save()
        self._refresh()

    # ---------- chat ----------
    def send_message(self, text):
        conversation, workspace = self._conversation(), self._workspace()
        if conversation is None:
            messagebox.showinfo("No conversation",
                                "Select or create a conversation first.")
            return
        if self.waiting:
            return
        try:
            conversation.add_message(USER, text)    # rejects empty messages
        except ValueError:
            messagebox.showwarning("Empty message", "Please type a message first.")
            return

        history = conversation.get_history()[:-1]   # everything before this message
        instruction = workspace.get_instruction()
        self.waiting = True
        self.chat.clear_input()
        self._refresh()
        self.chat.set_busy(True)
        threading.Thread(target=self._ask_ai, daemon=True,
                         args=(instruction, history, text, conversation)).start()

    def _ask_ai(self, instruction, history, text, conversation):
        """Runs in a background thread so the window never freezes."""
        try:
            reply = self.ai_service.get_reply(instruction, history, text)
            self.replies.put(("ok", reply, text, conversation))
        except AIServiceError as error:
            self.replies.put(("error", str(error), text, conversation))
        except Exception as error:   # anything unexpected
            self.replies.put(("error", f"Unexpected error: {error}", text,
                              conversation))

    def _check_replies(self):
        try:
            while True:
                self._handle_reply(*self.replies.get_nowait())
        except queue.Empty:
            pass
        self.after(100, self._check_replies)

    def _handle_reply(self, status, payload, text, conversation):
        self.waiting = False
        self.chat.set_busy(False)
        if status == "ok":
            conversation.add_message(AI, payload)
            self._save()                      # saved after every exchange
            self._refresh()
        else:
            conversation.remove_last_message()   # take back the unanswered message
            self._refresh()
            if conversation is self._conversation():
                self.chat.set_input(text)
            messagebox.showerror("AI problem", payload)

    # ---------- search & export ----------
    def search_workspace(self, word):
        workspace = self._workspace()
        if workspace is None:
            messagebox.showinfo("No workspace", "Select a workspace first.")
            return
        if not word.strip():
            messagebox.showinfo("Search", "Type a word to search for.")
            return
        results = workspace.search(word)
        if not results:
            messagebox.showinfo("Search", f"No messages contain '{word.strip()}'.")
            return
        SearchResultsDialog(self, word.strip(), results, self._open_conversation)

    def _open_conversation(self, conversation):
        workspace = self._workspace()
        if conversation in workspace.conversations:
            self.conv_index = workspace.conversations.index(conversation)
            self._refresh()

    def export_conversation(self):
        conversation, workspace = self._conversation(), self._workspace()
        if conversation is None:
            messagebox.showinfo("Export", "Select a conversation first.")
            return
        path = filedialog.asksaveasfilename(
            title="Export conversation", defaultextension=".txt",
            initialfile=f"{conversation.title}.txt",
            filetypes=[("Text files", "*.txt")])
        if not path:
            return
        try:
            self.data_manager.export_conversation(conversation, path,
                                                  workspace.name)
        except DataError as error:
            messagebox.showerror("Export problem", str(error))
            return
        messagebox.showinfo("Export", "Conversation exported.")
