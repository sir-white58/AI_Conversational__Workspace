"""Modal dialogs: ask for text, create/edit a workspace."""
import tkinter as tk
from gui.theme import T, font, FlatButton, style
from models.workspace import MODES, DEFAULT_MODE

class BaseDialog(tk.Toplevel):
    def __init__(self, parent, title, w=440, h=210):
        super().__init__(parent)
        c = T.c
        self.configure(bg=c["panel"]); self.title(title); self.result = None
        self.transient(parent); self.resizable(False, False)
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 3
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.bind("<Escape>", lambda e: self.destroy())
        tk.Label(self, text=title, font=font(14, "bold"), bg=c["panel"], fg=c["text"]).pack(anchor="w", padx=24, pady=(20, 6))
        self.body = tk.Frame(self, bg=c["panel"]); self.body.pack(fill="both", expand=True, padx=24)
        bar = tk.Frame(self, bg=c["panel"]); bar.pack(fill="x", padx=24, pady=16)
        FlatButton(bar, "Save", self.ok, kind="primary").pack(side="right")
        FlatButton(bar, "Cancel", self.destroy).pack(side="right", padx=6)

    def add_entry(self, value="", show=None):
        c = T.c
        e = tk.Entry(self.body, bg=c["card"], fg=c["text"], insertbackground=c["text"], relief="flat", font=font(11), show=show)
        e.insert(0, value); e.pack(fill="x", ipady=9); e.focus_set()
        e.bind("<Return>", lambda _: self.ok())
        return e

    def ok(self):
        self.destroy()

    def show(self):
        """Open the dialog, wait until it closes, return its result (or None)."""
        self.wait_visibility(); self.grab_set(); self.wait_window()
        return self.result

class AskText(BaseDialog):
    def __init__(self, parent, title, label, value="", show=None):
        super().__init__(parent, title)
        tk.Label(self.body, text=label, font=font(10), bg=T.c["panel"], fg=T.c["muted"], wraplength=390, justify="left").pack(anchor="w", pady=(0, 8))
        self.e = self.add_entry(value, show)
    def ok(self):
        v = self.e.get().strip()
        if v:
            self.result = v; self.destroy()

class WorkspaceDialog(BaseDialog):
    """Returns (name, mode) or None."""
    def __init__(self, parent, title="New workspace", name="", mode=DEFAULT_MODE):
        super().__init__(parent, title, 470, 410)
        c = T.c
        tk.Label(self.body, text="Name", font=font(10), bg=c["panel"], fg=c["muted"]).pack(anchor="w", pady=(0, 6))
        self.e = self.add_entry(name)
        tk.Label(self.body, text="AI mode", font=font(10), bg=c["panel"], fg=c["muted"]).pack(anchor="w", pady=(14, 6))
        grid = tk.Frame(self.body, bg=c["panel"]); grid.pack(fill="x")
        self.chips = {}
        for i, k in enumerate(MODES):
            l = tk.Label(grid, text=f"{style(k)[0]}  {k}", font=font(10), padx=12, pady=8, cursor="hand2")
            l.grid(row=i // 2, column=i % 2, sticky="ew", padx=3, pady=3)
            l.bind("<Button-1>", lambda ev, k=k: self.pick(k))
            grid.columnconfigure(i % 2, weight=1); self.chips[k] = l
        self.desc = tk.Label(self.body, wraplength=410, justify="left", font=font(9), bg=c["panel"], fg=c["muted"])
        self.desc.pack(anchor="w", pady=(10, 0))
        self.pick(mode if mode in MODES else DEFAULT_MODE)

    def pick(self, mode):
        c = T.c; self.mode = mode
        for k, l in self.chips.items():
            on = k == mode
            l.config(bg=c["accent"] if on else c["card"], fg="#ffffff" if on else c["text"])
        self.desc.config(text=MODES[mode])

    def ok(self):
        n = self.e.get().strip()
        if n:
            self.result = (n, self.mode); self.destroy()
