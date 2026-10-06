"""Right panel: chat bubbles, typing indicator, error card and message box."""
import re
import tkinter as tk
from gui.theme import T, font, FlatButton, ScrollFrame, style
from models.message import USER

PROVIDERS = ["auto", "gemini", "groq"]
HINT = "Enter to send  ·  Shift+Enter for a new line"

def clean_md(s):
    """Light markdown clean-up (labels can't show bold or bullets natively)."""
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"^\s*[*\-] ", "• ", s, flags=re.M)
    s = re.sub(r"^#+\s*", "", s, flags=re.M)
    return s.replace("`", "")

class ChatPanel(tk.Frame):
    def __init__(self, parent, app):
        c = T.c
        super().__init__(parent, bg=c["bg"])
        self.app, self.labels, self.busy, self.typing = app, [], False, None
        head = tk.Frame(self, bg=c["bg"]); head.pack(fill="x", padx=28, pady=(18, 10))
        self.title = tk.Label(head, font=font(15, "bold"), bg=c["bg"], fg=c["text"]); self.title.pack(side="left")
        self.chip = tk.Label(head, font=font(9, "bold"), padx=10, pady=3, bg=c["card"], fg=c["accent"]); self.chip.pack(side="left", padx=12)
        FlatButton(head, "⇩ Export", lambda: app.export_conversation()).pack(side="right")
        self.prov_btn = FlatButton(head, f"⚙ {app.provider.capitalize()}", self._cycle_provider)
        self.prov_btn.pack(side="right", padx=6)
        tk.Frame(self, bg=c["border"], height=1).pack(fill="x")
        self.scroll = ScrollFrame(self, c["bg"]); self.scroll.pack(fill="both", expand=True)
        self.scroll.canvas.bind("<Configure>", self._resize, add="+")
        box = tk.Frame(self, bg=c["bg"]); box.pack(fill="x", padx=28, pady=(6, 16))
        card = tk.Frame(box, bg=c["card"], highlightthickness=1, highlightbackground=c["border"], highlightcolor=c["accent"])
        card.pack(fill="x")
        self.input = tk.Text(card, height=1, wrap="word", bg=c["card"], fg=c["text"], insertbackground=c["text"],
                             relief="flat", font=font(11), padx=14, pady=12, undo=True)
        self.input.pack(side="left", fill="x", expand=True)
        self.send_btn = FlatButton(card, "Send  ➤", self.submit, kind="primary"); self.send_btn.pack(side="right", padx=8, pady=8)
        self.input.bind("<Return>", self._enter); self.input.bind("<KeyRelease>", self._grow)
        self.hint = tk.Label(box, text=HINT, font=font(8), bg=c["bg"], fg=c["muted"])
        self.hint.pack(anchor="w", pady=(4, 0))

    # ---- AI provider choice
    def _cycle_provider(self):
        """Click to switch: Auto -> Gemini -> Groq -> Auto."""
        i = PROVIDERS.index(self.app.provider)
        self.app.provider = PROVIDERS[(i + 1) % len(PROVIDERS)]
        self.prov_btn.config(text=f"⚙ {self.app.provider.capitalize()}")

    def set_status(self, text):
        """Small text under the message box (e.g. who answered)."""
        self.hint.config(text=text or HINT)

    # ---- input box
    def _enter(self, e):
        if e.state & 0x1:                 # Shift held -> newline
            return None
        self.submit(); return "break"

    def _grow(self, _=None):
        self.input.config(height=min(5, int(self.input.index("end-1c").split(".")[0])))

    def submit(self):
        self.app.send_message(self.input.get("1.0", "end"))

    def clear_input(self):
        self.input.delete("1.0", "end"); self._grow()

    def set_input(self, text):
        self.clear_input(); self.input.insert("1.0", text); self._grow()

    def _wl(self):
        return max(260, int(self.scroll.canvas.winfo_width() * 0.62))

    def _resize(self, _):
        for l in self.labels:
            try: l.config(wraplength=self._wl())
            except tk.TclError: pass

    # ---- rendering
    def show(self, ws, conv):
        for w in self.scroll.inner.winfo_children():
            w.destroy()
        self.labels, self.typing = [], None
        icon, color, _ = style(ws.mode) if ws else ("✦", T.c["accent"], [])
        self.title.config(text=conv.title if conv else (ws.name if ws else "Welcome"))
        self.chip.config(text=f"{icon}  {ws.mode}" if ws else "", fg=color)
        if not conv or not conv.messages:
            self._empty(ws)
        else:
            for m in conv.messages:
                self.add_bubble(m)
        if self.busy and self.app.pending is conv:
            self._typing_on()
        self.scroll.to_bottom()
        if conv: self.input.focus_set()

    def _empty(self, ws):
        c = T.c
        icon, color, starters = style(ws.mode) if ws else ("✦", c["accent"], [])
        f = tk.Frame(self.scroll.inner, bg=c["bg"]); f.pack(pady=(70, 0))
        tk.Label(f, text=icon, font=font(44), fg=color, bg=c["bg"]).pack()
        tk.Label(f, text=ws.name if ws else "Welcome", font=font(20, "bold"), fg=c["text"], bg=c["bg"]).pack(pady=(6, 2))
        tk.Label(f, text=f"{ws.mode} mode  ·  ask anything, or try one of these" if ws else "Create a workspace to get started",
                 font=font(11), fg=c["muted"], bg=c["bg"]).pack(pady=(0, 16))
        for s in starters:
            FlatButton(f, s, lambda s=s: self.app.send_message(s), bg=c["card"]).pack(pady=4)

    def add_bubble(self, m, animate=False):
        c, user = T.c, m.sender == USER
        icon, color, _ = style(self.app.ws.mode)
        row = tk.Frame(self.scroll.inner, bg=c["bg"]); row.pack(fill="x", padx=28, pady=6)
        if not user:
            tk.Label(row, text=icon, font=font(12, "bold"), fg="#fff", bg=color, width=3, pady=4).pack(side="left", anchor="n", padx=(0, 10))
        col = tk.Frame(row, bg=c["bg"]); col.pack(side="right" if user else "left")
        side = "e" if user else "w"
        segs = [m.text] if user else re.split(r"```[\w+-]*\n?(.*?)```", m.text, flags=re.S)
        parts = []
        for i, s in enumerate(segs):
            if not s.strip():
                continue
            code = i % 2 == 1
            if code:
                w = tk.Label(col, justify="left", anchor="w", font=("Consolas", 10), bg="#0b0d14", fg="#c9d1ff", padx=14, pady=10)
                txt = s.strip("\n")
            else:
                w = tk.Label(col, justify="left", anchor="w", font=font(11), padx=16, pady=10,
                             bg=c["user"] if user else c["ai"], fg="#ffffff" if user else c["text"])
                txt = s.strip() if user else clean_md(s).strip()
            w.config(wraplength=self._wl()); w.pack(anchor=side, pady=2, fill="x" if code else "none")
            self.labels.append(w); parts.append((w, txt))
        foot = tk.Frame(col, bg=c["bg"]); foot.pack(anchor=side)
        tk.Label(foot, text=m.timestamp[11:16], font=font(8), bg=c["bg"], fg=c["muted"]).pack(side="left")
        if not user:
            cp = tk.Label(foot, text="   ⧉ copy", font=font(8), bg=c["bg"], fg=c["muted"], cursor="hand2"); cp.pack(side="left")
            cp.bind("<Button-1>", lambda e: self._copy(cp, m.text))
        if animate and not user:
            self._type(parts)
        else:
            for w, t in parts: w.config(text=t)
        self.scroll.to_bottom()

    def _type(self, parts, n=0):
        """Typewriter effect: reveal the reply a few characters at a time."""
        total, left = sum(len(t) for _, t in parts), n
        try:
            for w, t in parts:
                w.config(text=t[:max(0, min(len(t), left))]); left -= len(t)
            self.scroll.to_bottom()
        except tk.TclError:
            return                        # user switched chat mid-animation
        if n < total:
            self.after(10, lambda: self._type(parts, n + 6))

    def _copy(self, lbl, text):
        self.clipboard_clear(); self.clipboard_append(text)
        lbl.config(text="   ✓ copied", fg=T.c["ok"])
        self.after(1500, lambda: lbl.winfo_exists() and lbl.config(text="   ⧉ copy", fg=T.c["muted"]))

    # ---- status widgets
    def set_busy(self, b):
        self.busy = b
        self.send_btn.config(text="···" if b else "Send  ➤")
        self._typing_off()
        if b and self.app.pending is self.app.conv:
            self._typing_on()

    def _typing_on(self):
        self.typing = tk.Label(self.scroll.inner, text="●  ○  ○", font=font(11), fg=T.c["accent"], bg=T.c["bg"])
        self.typing.pack(anchor="w", padx=70, pady=8); self._pulse(0); self.scroll.to_bottom()

    def _typing_off(self):
        if self.typing:
            try: self.typing.destroy()
            except tk.TclError: pass
            self.typing = None

    def _pulse(self, i):
        if self.typing is None: return
        try: self.typing.config(text=("●  ○  ○", "○  ●  ○", "○  ○  ●")[i % 3])
        except tk.TclError: return
        self.after(300, lambda: self._pulse(i + 1))

    def add_error(self, msg, retry):
        c = T.c
        f = tk.Frame(self.scroll.inner, bg=c["card"], highlightthickness=1, highlightbackground=c["danger"])
        f.pack(anchor="w", padx=70, pady=8)
        tk.Label(f, text="⚠  " + msg, font=font(10), bg=c["card"], fg=c["text"], wraplength=420, justify="left").pack(side="left", padx=12, pady=10)
        FlatButton(f, "Retry", lambda: (f.destroy(), retry()), kind="primary").pack(side="right", padx=8)
        self.scroll.to_bottom()

    def toast(self, text, ok=False):
        t = tk.Label(self, text=text, font=font(10, "bold"), fg="#fff", bg=T.c["ok"] if ok else T.c["danger"], padx=16, pady=8)
        t.place(relx=0.5, y=70, anchor="n")
        self.after(2200, t.destroy)