"""Colours, fonts and small reusable widgets shared by the whole GUI."""
import tkinter as tk

DARK = dict(bg="#0f1117", panel="#161923", card="#1d2130", hover="#272c42", border="#2a2f45",
            text="#e8eaf2", muted="#8b91a8", accent="#7c5cff", accent_h="#9479ff",
            user="#5b47e0", ai="#1d2130", danger="#ff5d73", ok="#3ddc97")
LIGHT = dict(bg="#f4f5fb", panel="#ffffff", card="#eef0f8", hover="#e0e4f4", border="#d9dcec",
             text="#1b1e2e", muted="#6b7190", accent="#6c4cf5", accent_h="#8266ff",
             user="#6c4cf5", ai="#ffffff", danger="#e5384f", ok="#1fae74")

# icon, colour and starter prompts for each AI mode (falls back for unknown modes)
MODE_STYLE = {
    "General Assistant": ("✦", "#7c5cff", ["Plan my week for me", "Explain something complex simply", "Give me 5 project ideas"]),
    "Tutor": ("❖", "#22c1a5", ["Teach me recursion", "Explain Python classes like I'm new", "Quiz me on file handling"]),
    "Coding Helper": ("⌘", "#4d9fff", ["Explain this error: KeyError", "Write a Python class for a bank account", "How do I read a JSON file safely?"]),
    "Writing Assistant": ("✎", "#ff8a5c", ["Help me write a cover letter", "Make this paragraph sound professional", "Outline an essay on AI"]),
}

def style(mode):
    return MODE_STYLE.get(mode, ("✦", "#7c5cff", ["Hello! What can you help me with?"]))

class T:
    """Holds the active palette: T.c[...]"""
    dark, c = True, DARK
    @classmethod
    def toggle(cls):
        cls.dark = not cls.dark
        cls.c = DARK if cls.dark else LIGHT

def font(size=11, weight="normal"):
    return ("Segoe UI", size, weight)

class FlatButton(tk.Label):
    """Label-based button with a hover effect. kind: 'primary' or 'ghost'."""
    def __init__(self, parent, text, command=None, kind="ghost", bg=None):
        c = T.c
        primary = kind == "primary"
        self.base = bg or (c["accent"] if primary else parent["bg"])
        self.over = c["accent_h"] if primary else c["hover"]
        super().__init__(parent, text=text, bg=self.base, fg="#ffffff" if primary else c["text"],
                         font=font(10, "bold" if primary else "normal"), padx=14, pady=7, cursor="hand2")
        self.command = command
        self.bind("<Enter>", lambda e: self.config(bg=self.over))
        self.bind("<Leave>", lambda e: self.config(bg=self.base))
        self.bind("<Button-1>", lambda e: self.command and self.command())

class ScrollFrame(tk.Frame):
    """Scrollable area without a visible scrollbar; the mouse wheel works."""
    def __init__(self, parent, bg):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.pack(fill="both", expand=True)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self._win, width=e.width))
        for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.bind_all(ev, self._wheel, add="+")

    def _wheel(self, e):
        try:                                   # old frames may already be destroyed
            if not str(e.widget).startswith(str(self)):
                return
            if self.inner.winfo_height() <= self.canvas.winfo_height():
                return
            self.canvas.yview_scroll(-3 if (e.num == 4 or e.delta > 0) else 3, "units")
        except tk.TclError:
            pass

    def to_bottom(self):
        self.update_idletasks()
        self.canvas.yview_moveto(1)
