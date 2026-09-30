"""Right panel: chat display, message box, search and export."""
import tkinter as tk
from tkinter import ttk

from models.message import USER

FONT = ("Segoe UI", 10)


class ChatPanel(ttk.Frame):
    def __init__(self, parent, on_send, on_export, on_search):
        super().__init__(parent)
        self.on_send = on_send
        self.on_search = on_search
        self._enabled = False
        self._busy = False

        # --- top bar: title, search, export ---
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=(10, 5))
        self.title_var = tk.StringVar(value="No conversation selected")
        ttk.Label(top, textvariable=self.title_var,
                  font=("Segoe UI", 12, "bold")).pack(side="left")
        ttk.Button(top, text="Export", command=on_export).pack(side="right")
        ttk.Button(top, text="Search", command=self._search).pack(
            side="right", padx=(0, 5))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(top, textvariable=self.search_var, width=18)
        search_entry.pack(side="right", padx=(0, 5))
        search_entry.bind("<Return>", lambda event: self._search())

        # --- message display ---
        middle = ttk.Frame(self)
        middle.pack(fill="both", expand=True, padx=10)
        self.display = tk.Text(middle, wrap="word", state="disabled", padx=12,
                               pady=10, font=FONT, relief="flat", bg="#ffffff")
        scroll = ttk.Scrollbar(middle, command=self.display.yview)
        self.display.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.display.pack(side="left", fill="both", expand=True)
        self.display.tag_configure("you", foreground="#1a5fb4",
                                   font=("Segoe UI", 10, "bold"))
        self.display.tag_configure("ai", foreground="#2e7d32",
                                   font=("Segoe UI", 10, "bold"))
        self.display.tag_configure("time", foreground="#888888",
                                   font=("Segoe UI", 8))
        self.display.tag_configure("body", spacing3=10, lmargin1=8, lmargin2=8)
        self.display.tag_configure("hint", foreground="#888888",
                                   justify="center", spacing1=120)

        # --- message box ---
        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=10, pady=(10, 4))
        self.input = tk.Text(bottom, height=3, wrap="word", font=FONT)
        self.input.pack(side="left", fill="x", expand=True)
        self.send_button = ttk.Button(bottom, text="Send", command=self._send)
        self.send_button.pack(side="right", padx=(8, 0), fill="y")
        self.input.bind("<Return>", self._on_enter)

        self.status_var = tk.StringVar(value="Enter = send, Shift+Enter = new line")
        ttk.Label(self, textvariable=self.status_var, foreground="#666666"
                  ).pack(anchor="w", padx=10, pady=(0, 8))
        self._update_state()

    # ---------- events ----------
    def _on_enter(self, event):
        if event.state & 0x0001:      # Shift held: allow a new line
            return None
        self._send()
        return "break"

    def _send(self):
        self.on_send(self.input.get("1.0", "end-1c"))

    def _search(self):
        self.on_search(self.search_var.get())

    # ---------- called by MainWindow ----------
    def show_conversation(self, header, conversation):
        self.title_var.set(header)
        self._enabled = True
        self._write(lambda: self._draw_messages(conversation))
        self._update_state()

    def show_empty(self, header, hint):
        self.title_var.set(header)
        self._enabled = False
        self._write(lambda: self.display.insert("end", hint, "hint"))
        self._update_state()

    def set_busy(self, busy):
        self._busy = busy
        self.status_var.set("AI is thinking..." if busy
                            else "Enter = send, Shift+Enter = new line")
        self._update_state()

    def clear_input(self):
        self.input.delete("1.0", "end")

    def set_input(self, text):
        self.clear_input()
        self.input.insert("1.0", text)

    def focus_input(self):
        self.input.focus_set()

    # ---------- helpers ----------
    def _write(self, draw):
        self.display.configure(state="normal")
        self.display.delete("1.0", "end")
        draw()
        self.display.configure(state="disabled")
        self.display.see("end")

    def _draw_messages(self, conversation):
        if not conversation.messages:
            self.display.insert("end", "Say hello to start the conversation.",
                                "hint")
            return
        for message in conversation.messages:
            is_user = message.sender == USER
            self.display.insert("end", "You" if is_user else "AI",
                                "you" if is_user else "ai")
            self.display.insert("end", f"   {message.timestamp}\n", "time")
            self.display.insert("end", message.text + "\n", "body")

    def _update_state(self):
        state = "normal" if self._enabled and not self._busy else "disabled"
        self.input.configure(state=state)
        self.send_button.configure(state=state)
