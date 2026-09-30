"""Left panel: workspaces, their conversations, and live search."""
import tkinter as tk
from gui.theme import T, font, FlatButton, ScrollFrame, style

def short(s, n=26):
    return s if len(s) <= n else s[:n - 1] + "…"

class Sidebar(tk.Frame):
    def __init__(self, parent, app):
        c = T.c
        super().__init__(parent, bg=c["panel"], width=300)
        self.pack_propagate(False); self.app = app
        head = tk.Frame(self, bg=c["panel"]); head.pack(fill="x", padx=16, pady=(20, 10))
        tk.Label(head, text="✦ Workspace AI", font=font(15, "bold"), bg=c["panel"], fg=c["text"]).pack(side="left")
        FlatButton(head, "☾" if T.dark else "☀", app.toggle_theme).pack(side="right")
        FlatButton(self, "＋  New workspace", app.new_workspace, kind="primary").pack(fill="x", padx=16, pady=(0, 10))
        box = tk.Frame(self, bg=c["card"]); box.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(box, text="⌕", bg=c["card"], fg=c["muted"], font=font(12)).pack(side="left", padx=(10, 0))
        self.q = tk.StringVar()
        self.search = tk.Entry(box, textvariable=self.q, bg=c["card"], fg=c["text"], insertbackground=c["text"], relief="flat", font=font(10))
        self.search.pack(fill="x", ipady=8, padx=6)
        self.q.trace_add("write", lambda *_: self.refresh())
        self.list = ScrollFrame(self, c["panel"]); self.list.pack(fill="both", expand=True, pady=(4, 0))
        tk.Label(self, text="Right-click a workspace or chat for options", font=font(8), bg=c["panel"], fg=c["muted"]).pack(pady=8)

    def _row(self, text, fg, bg, weight, click, menu=None):
        c = T.c
        r = tk.Label(self.list.inner, text=text, anchor="w", bg=bg, fg=fg, font=font(10, weight), padx=16, pady=8, cursor="hand2")
        r.pack(fill="x", padx=8, pady=1)
        r.bind("<Enter>", lambda e: r.config(bg=c["hover"])); r.bind("<Leave>", lambda e: r.config(bg=bg))
        r.bind("<Button-1>", lambda e: click())
        if menu:
            for b in ("<Button-2>", "<Button-3>"):
                r.bind(b, lambda e: self._menu(e, menu))

    def _menu(self, e, items):
        c = T.c
        m = tk.Menu(self, tearoff=0, bg=c["card"], fg=c["text"], activebackground=c["accent"], activeforeground="#fff", bd=0, font=font(10))
        for label, cmd in items:
            m.add_command(label=label, command=cmd)
        m.tk_popup(e.x_root, e.y_root)

    def refresh(self):
        for w in self.list.inner.winfo_children():
            w.destroy()
        app, c, term = self.app, T.c, self.q.get().strip()
        for ws in app.workspaces:
            convs = ws.conversations
            if term:                                   # uses Workspace.search()
                hits = {cv for cv, _ in ws.search(term)}
                convs = [cv for cv in convs if cv in hits or term.lower() in cv.title.lower()]
                if not convs:
                    continue
            opened = bool(term) or ws in app.expanded
            def toggle(ws=ws):
                app.expanded ^= {ws}; self.refresh()
            self._row(f"{'▾' if opened else '▸'}  {style(ws.mode)[0]}  {short(ws.name, 22)}", c["text"], c["panel"], "bold", toggle,
                      [("New chat", lambda ws=ws: app.new_conversation(ws)),
                       ("Edit workspace…", lambda ws=ws: app.edit_workspace(ws)),
                       ("Delete workspace", lambda ws=ws: app.delete_workspace(ws))])
            if not opened:
                continue
            for cv in convs:
                on = cv is app.conv
                self._row(f"      {short(cv.title)}", c["accent"] if on else c["muted"], c["card"] if on else c["panel"], "bold" if on else "normal",
                          lambda ws=ws, cv=cv: app.select(ws, cv),
                          [("Rename…", lambda cv=cv: app.rename_conversation(cv)),
                           ("Export to .txt", lambda ws=ws, cv=cv: app.export_conversation(cv, ws)),
                           ("Delete chat", lambda ws=ws, cv=cv: app.delete_conversation(ws, cv))])
            if not term:
                self._row("      ＋  New chat", c["muted"], c["panel"], "normal", lambda ws=ws: app.new_conversation(ws))
