# -*- coding: utf-8 -*-
"""ui/widgets.py — عناصر واجهة صغيرة مشتركة بين أكثر من نافذة."""
import tkinter as tk

class ToolTip:
    def __init__(self, widget, text_provider):
        self.widget = widget
        self.text_provider = text_provider
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        text = self.text_provider() if callable(self.text_provider) else self.text_provider
        if self.tip_window or not text:
            return
        x = self.widget.winfo_rootx() + 15
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(tw, text=text, justify="right", background="#FFFFE1", relief="solid", borderwidth=1, font=("Segoe UI", 9), padx=6, pady=3, wraplength=350)
        lbl.pack()

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None
