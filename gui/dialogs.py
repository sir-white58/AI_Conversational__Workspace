"""Pop-up windows: create/edit workspace and search results."""
import tkinter as tk
from tkinter import messagebox, ttk

from models.workspace import DEFAULT_MODE, MODES


class WorkspaceDialog(tk.Toplevel):
    """Asks for a workspace name and AI mode. result = (name, mode) or None."""

    def __init__(self, parent, title, name="", mode=DEFAULT_MODE):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.result = None

        frame = ttk.Frame(self, padding=15)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Workspace name:").grid(row=0, column=0, sticky="w")
        self.name_var = tk.StringVar(value=name)
        name_entry = ttk.Entry(frame, textvariable=self.name_var, width=32)
        name_entry.grid(row=1, column=0, pady=(2, 10))

        ttk.Label(frame, text="AI mode:").grid(row=2, column=0, sticky="w")
        self.mode_var = tk.StringVar(value=mode if mode in MODES else DEFAULT_MODE)
        ttk.Combobox(frame, textvariable=self.mode_var, values=list(MODES),
                     state="readonly", width=30).grid(row=3, column=0, pady=(2, 15))

        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, sticky="e")
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(buttons, text="OK", command=self._ok).pack(side="right", padx=5)

        self.bind("<Return>", lambda event: self._ok())
        self.bind("<Escape>", lambda event: self.destroy())
        name_entry.focus_set()
        self.grab_set()
        self.wait_window(self)

    def _ok(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Missing name",
                                   "Please enter a workspace name.", parent=self)
            return
        self.result = (name, self.mode_var.get())
        self.destroy()


class SearchResultsDialog(tk.Toplevel):
    """Lists search matches. Double-click a result to open its conversation."""

    def __init__(self, parent, word, results, on_open):
        super().__init__(parent)
        self.title(f"Search results for '{word}'")
        self.geometry("620x320")
        self.transient(parent)
        self.results = results
        self.on_open = on_open

        ttk.Label(self, padding=10,
                  text=f"{len(results)} match(es). Double-click to open."
                  ).pack(anchor="w")
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.listbox = tk.Listbox(frame, activestyle="none")
        scroll = ttk.Scrollbar(frame, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.listbox.pack(side="left", fill="both", expand=True)

        for conversation, message in results:
            snippet = message.text.replace("\n", " ")
            if len(snippet) > 70:
                snippet = snippet[:67] + "..."
            who = "You" if message.sender == "user" else "AI"
            self.listbox.insert("end", f"{conversation.title}  |  {who}: {snippet}")
        self.listbox.bind("<Double-Button-1>", self._open)

    def _open(self, event=None):
        selection = self.listbox.curselection()
        if selection:
            conversation, _ = self.results[selection[0]]
            self.on_open(conversation)
            self.destroy()
