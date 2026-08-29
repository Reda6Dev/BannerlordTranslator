# -*- coding: utf-8 -*-
"""ui/help_dialog.py — نافذة المساعدة (تبويبات شرح الاستخدام)."""
import tkinter as tk
from tkinter import ttk

class HelpNotebookDialog(tk.Toplevel):
    def __init__(self, parent, ui_lang, t_func):
        super().__init__(parent)
        self.ui_lang = ui_lang
        self.t = t_func
        self.title(self.t("help_btn"))
        self.geometry("760x540")
        self.minsize(700, 480)
        self.create_ui()

    def create_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        tab1 = tk.Frame(notebook, padx=12, pady=12)
        notebook.add(tab1, text=self.t("guide_t1"))
        t1_txt = tk.Text(tab1, font=("Segoe UI", 10), wrap="word", relief="flat", bg="#FAFAFA")
        t1_txt.pack(fill="both", expand=True)
        t1_txt.insert("1.0", self.t("guide_c1"))
        t1_txt.config(state="disabled")

        tab2 = tk.Frame(notebook, padx=12, pady=12)
        notebook.add(tab2, text=self.t("guide_t2"))
        t2_txt = tk.Text(tab2, font=("Segoe UI", 10), wrap="word", relief="flat", bg="#FAFAFA")
        t2_txt.pack(fill="both", expand=True)
        t2_txt.insert("1.0", self.t("guide_c2"))
        t2_txt.config(state="disabled")

        tab3 = tk.Frame(notebook, padx=12, pady=12)
        notebook.add(tab3, text=self.t("guide_t3"))
        t3_txt = tk.Text(tab3, font=("Segoe UI", 10), wrap="word", relief="flat", bg="#FAFAFA")
        t3_txt.pack(fill="both", expand=True)
        t3_txt.insert("1.0", self.t("guide_c3"))
        t3_txt.config(state="disabled")

        tab4 = tk.Frame(notebook, padx=12, pady=12)
        notebook.add(tab4, text=self.t("guide_t4"))
        t4_txt = tk.Text(tab4, font=("Segoe UI", 10), wrap="word", relief="flat", bg="#FAFAFA")
        t4_txt.pack(fill="both", expand=True)
        # العربية فيها مشكلة RTL فعلية بخانة الجدول الضيقة -> شرح تفصيلي بالتحذير.
        # أي لغة ثانية ما عندها هالمشكلة -> شرح عام مختصر لكيفية استخدام مربع التعديل.
        guide4_content = self.t("guide_c4") if self.ui_lang == "ar" else self.t("guide_c4_generic")
        t4_txt.insert("1.0", guide4_content)
        t4_txt.config(state="disabled")

        tab5 = tk.Frame(notebook, padx=12, pady=12)
        notebook.add(tab5, text=self.t("guide_t5"))
        t5_txt = tk.Text(tab5, font=("Segoe UI", 10), wrap="word", relief="flat", bg="#FAFAFA")
        t5_txt.pack(fill="both", expand=True)
        t5_txt.insert("1.0", self.t("guide_c5"))
        t5_txt.config(state="disabled")
