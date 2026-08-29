# -*- coding: utf-8 -*-
"""ui/batch_dialog.py — نافذة اختيار المودات المراد ترجمتها دفعة وحدة."""
import tkinter as tk
from tkinter import ttk, messagebox

from ..data.ui_texts import UI_TEXTS

class BatchSelectionDialog(tk.Toplevel):
    def __init__(self, parent, mods_list, on_confirm_callback, ui_lang="ar", t_func=None):
        super().__init__(parent)
        self.ui_lang = ui_lang
        self.t = t_func if t_func else (lambda key: UI_TEXTS.get(ui_lang, UI_TEXTS["en"]).get(key, UI_TEXTS["en"].get(key, "")))
        self.title(self.t("batch_dialog_title"))
        self.geometry("660x480")
        self.resizable(True, True)
        self.mods_list = mods_list
        self.on_confirm_callback = on_confirm_callback
        self.check_vars = []

        self.create_ui()

    def create_ui(self):
        tk.Label(self, text=self.t("batch_select_label"), font=("Segoe UI", 11, "bold"), fg="#107C41").pack(anchor="w", padx=12, pady=8)

        list_frame = tk.Frame(self, padx=8, pady=4)
        list_frame.pack(fill="both", expand=True, padx=12)

        canvas = tk.Canvas(list_frame, borderwidth=0, background="#FFFFFF")
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, background="#FFFFFF")

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for mod_path, name, can_trans, reason in self.mods_list:
            var = tk.BooleanVar(value=can_trans)
            self.check_vars.append((var, mod_path, can_trans))

            row_f = tk.Frame(scrollable_frame, bg="#FFFFFF", pady=3)
            row_f.pack(fill="x", expand=True)

            state = "normal" if can_trans else "disabled"
            status_text = f" ({reason})" if can_trans else f" ({self.t('batch_unsupported')} - {reason})"
            color = "#000000" if can_trans else "#888888"

            chk = tk.Checkbutton(row_f, text=f"{name} {status_text}", variable=var, font=("Segoe UI", 10), state=state, bg="#FFFFFF", fg=color)
            chk.pack(side="left", padx=5)

        btn_f = tk.Frame(self, padx=12, pady=8)
        btn_f.pack(fill="x")

        selection_btn_f = tk.Frame(btn_f)
        selection_btn_f.pack(fill="x", pady=(0, 6))

        tk.Button(selection_btn_f, text=self.t("batch_select_all"), command=self.select_all_mods, font=("Segoe UI", 10, "bold"), bg="#E8F5E9", fg="#1B5E20").pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(selection_btn_f, text=self.t("batch_deselect_all"), command=self.deselect_all_mods, font=("Segoe UI", 10, "bold"), bg="#FFEBEE", fg="#B71C1C").pack(side="left", fill="x", expand=True, padx=(4, 0))

        tk.Button(btn_f, text=self.t("batch_translate_btn"), command=self.confirm_selection, font=("Segoe UI", 11, "bold"), bg="#107C41", fg="white", height=2).pack(fill="x")

    def select_all_mods(self):
        for var, _mod_path, can_trans in self.check_vars:
            var.set(can_trans)

    def deselect_all_mods(self):
        for var, _mod_path, _can_trans in self.check_vars:
            var.set(False)

    def confirm_selection(self):
        selected = [path for var, path, can_trans in self.check_vars if var.get() and can_trans]
        if not selected:
            messagebox.showwarning(self.t("title_notice"), self.t("msg_select_one_mod"))
            return
        self.destroy()
        self.on_confirm_callback(selected)
