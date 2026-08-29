# -*- coding: utf-8 -*-
"""ui/reset_dialog.py — نافذة تأكيد "ضبط المصنع" (حذف الإعدادات/القاموس)."""
import tkinter as tk
from tkinter import ttk, messagebox

class FactoryResetDialog(tk.Toplevel):
    def __init__(self, parent, on_confirm_callback, ui_lang, t_func):
        super().__init__(parent)
        self.on_confirm_callback = on_confirm_callback
        self.ui_lang = ui_lang
        self.t = t_func
        self.title(self.t("reset_dlg_title"))
        self.geometry("520x240")
        self.resizable(False, False)
        self.grab_set()

        self.del_config_var = tk.BooleanVar(value=True)
        self.del_glossary_var = tk.BooleanVar(value=True)

        self.create_ui()

    def create_ui(self):
        tk.Label(self, text=self.t("reset_dlg_header"), font=("Segoe UI", 10, "bold"), fg="#B71C1C", wraplength=480, justify="left").pack(anchor="w", padx=16, pady=(14, 10))

        opts_f = tk.Frame(self, padx=16)
        opts_f.pack(fill="x", expand=True)

        chk1 = tk.Checkbutton(opts_f, text=self.t("reset_opt_config"), variable=self.del_config_var, font=("Segoe UI", 9), anchor="w")
        chk1.pack(fill="x", pady=4)

        chk2 = tk.Checkbutton(opts_f, text=self.t("reset_opt_glossary"), variable=self.del_glossary_var, font=("Segoe UI", 9), anchor="w")
        chk2.pack(fill="x", pady=4)

        btn_f = tk.Frame(self, padx=16, pady=12)
        btn_f.pack(fill="x")

        tk.Button(btn_f, text=self.t("reset_btn_cancel"), command=self.destroy, width=12, font=("Segoe UI", 9)).pack(side="right", padx=4)
        tk.Button(btn_f, text=self.t("reset_btn_confirm"), command=self.confirm_action, bg="#D83B01", fg="white", font=("Segoe UI", 9, "bold"), padx=8).pack(side="right", padx=4)

    def confirm_action(self):
        del_cfg = self.del_config_var.get()
        del_glo = self.del_glossary_var.get()
        if not del_cfg and not del_glo:
            messagebox.showwarning(self.t("reset_dlg_title"), self.t("reset_warn_select"))
            return
        self.destroy()
        self.on_confirm_callback(del_cfg, del_glo)
