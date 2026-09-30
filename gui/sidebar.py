"""Left panel: workspace list and conversation list."""
import tkinter as tk
from tkinter import ttk


class Sidebar(ttk.Frame):
    """Shows workspaces and the conversations of the selected workspace.
    It only displays data; MainWindow decides what each action does."""

    def __init__(self, parent, actions):
        super().__init__(parent, padding=8)
        self.actions = actions

        self.workspace_list = self._section(
            "Workspaces",
            [("New", "new_workspace"), ("Rename", "rename_workspace"),
             ("Delete", "delete_workspace")],
            "select_workspace")
        self.conversation_list = self._section(
            "Conversations",
            [("New", "new_conversation"), ("Rename", "rename_conversation"),
             ("Delete", "delete_conversation")],
            "select_conversation")

    def _section(self, title, buttons, select_action):
        ttk.Label(self, text=title, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        row = ttk.Frame(self)
        row.pack(fill="x", pady=(4, 4))
        for text, action in buttons:
            ttk.Button(row, text=text, width=8,
                       command=self.actions[action]).pack(side="left", padx=(0, 4))

        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, pady=(0, 10))
        listbox = tk.Listbox(frame, exportselection=False, activestyle="none",
                             height=8)
        scroll = ttk.Scrollbar(frame, command=listbox.yview)
        listbox.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        listbox.pack(side="left", fill="both", expand=True)
        listbox.bind("<<ListboxSelect>>",
                     lambda event: self._selected(listbox, select_action))
        return listbox

    def _selected(self, listbox, action):
        selection = listbox.curselection()
        if selection:
            self.actions[action](selection[0])

    @staticmethod
    def _fill(listbox, names, selected):
        listbox.delete(0, "end")
        for name in names:
            listbox.insert("end", name)
        if selected is not None and 0 <= selected < len(names):
            listbox.selection_set(selected)
            listbox.see(selected)

    def show_workspaces(self, names, selected):
        self._fill(self.workspace_list, names, selected)

    def show_conversations(self, names, selected):
        self._fill(self.conversation_list, names, selected)
