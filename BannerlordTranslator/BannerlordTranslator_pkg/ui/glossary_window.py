# -*- coding: utf-8 -*-
"""ui/glossary_window.py — نافذة إدارة قاموس المصطلحات."""
import tkinter as tk
from tkinter import ttk, messagebox

from ..data.languages import OFFICIAL_LANGUAGES
from .widgets import ToolTip

class GlossaryManagerDialog(tk.Toplevel):
    def __init__(self, parent, glossary_data, save_callback, ui_lang, t_func):
        super().__init__(parent)
        self.glossary_data = glossary_data
        self.save_callback = save_callback
        self.ui_lang = ui_lang
        self.t = t_func
        self.title(self.t("glossary_title"))
        self.geometry("740x500")
        self.minsize(650, 420)
        self.selected_lang = self.ui_lang
        self.create_ui()

    def create_ui(self):
        top_f = tk.Frame(self, padx=10, pady=8, bg="#ECEFF1")
        top_f.pack(fill="x")

        tk.Label(top_f, text=self.t("glossary_lang_lbl"), font=("Segoe UI", 9, "bold"), bg="#ECEFF1").pack(side="left", padx=4)
        lang_names = [conf["name"] for conf in OFFICIAL_LANGUAGES.values()]
        self.lang_cb = ttk.Combobox(top_f, values=lang_names, state="readonly", width=22)
        
        default_name = OFFICIAL_LANGUAGES.get(self.ui_lang, OFFICIAL_LANGUAGES["ar"])["name"]
        self.lang_cb.set(default_name)
        self.lang_cb.pack(side="left", padx=4)
        self.lang_cb.bind("<<ComboboxSelected>>", self.on_lang_changed)

        btn_help = tk.Button(top_f, text="?", command=self.show_glossary_help, bg="#CFD8DC", font=("Segoe UI", 9, "bold"), width=3, relief="groove")
        btn_help.pack(side="right", padx=3)
        ToolTip(btn_help, lambda: self.t("glossary_help_title"))

        btn_add = tk.Button(top_f, text=self.t("glossary_add_btn"), command=self.add_term_dialog, bg="#107C41", fg="white", font=("Segoe UI", 9, "bold"))
        btn_add.pack(side="right", padx=3)

        btn_del = tk.Button(top_f, text=self.t("glossary_del_btn"), command=self.delete_term, bg="#D83B01", fg="white", font=("Segoe UI", 9))
        btn_del.pack(side="right", padx=3)

        tree_f = tk.Frame(self, padx=10, pady=5)
        tree_f.pack(fill="both", expand=True)

        columns = ("en", "target")
        self.tree = ttk.Treeview(tree_f, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("en", text=self.t("glossary_col_en"))
        self.tree.heading("target", text=self.t("glossary_col_tgt"))
        self.tree.column("en", width=290)
        self.tree.column("target", width=360)

        sb = ttk.Scrollbar(tree_f, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.load_tree_data()

    def show_glossary_help(self):
        messagebox.showinfo(self.t("glossary_help_title"), self.t("glossary_help_text"))

    def on_lang_changed(self, event=None):
        selected_name = self.lang_cb.get()
        for code, conf in OFFICIAL_LANGUAGES.items():
            if conf["name"] == selected_name:
                self.selected_lang = code
                break
        self.load_tree_data()

    def load_tree_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        terms = self.glossary_data.get(self.selected_lang, {})
        for en_term, target_term in terms.items():
            self.tree.insert("", "end", values=(en_term, target_term))

    def add_term_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title(self.t("glossary_dlg_title"))
        dialog.geometry("400x180")
        dialog.resizable(False, False)

        tk.Label(dialog, text=self.t("glossary_dlg_en")).pack(anchor="w", padx=15, pady=(10, 2))
        en_entry = tk.Entry(dialog, width=40)
        en_entry.pack(padx=15, fill="x")

        tk.Label(dialog, text=self.t("glossary_dlg_tgt")).pack(anchor="w", padx=15, pady=(6, 2))
        tgt_entry = tk.Entry(dialog, width=40)
        tgt_entry.pack(padx=15, fill="x")

        def save_new():
            en_val = en_entry.get().strip()
            tgt_val = tgt_entry.get().strip()
            if en_val and tgt_val:
                if self.selected_lang not in self.glossary_data:
                    self.glossary_data[self.selected_lang] = {}
                self.glossary_data[self.selected_lang][en_val] = tgt_val
                self.save_callback()
                self.load_tree_data()
                dialog.destroy()

        tk.Button(dialog, text=self.t("glossary_dlg_save"), command=save_new, bg="#107C41", fg="white", font=("Segoe UI", 9, "bold")).pack(pady=12)

    def delete_term(self):
        selected = self.tree.selection()
        if not selected:
            return
        item = self.tree.item(selected[0])
        en_term = item["values"][0]
        if self.selected_lang in self.glossary_data and en_term in self.glossary_data[self.selected_lang]:
            del self.glossary_data[self.selected_lang][en_term]
            self.save_callback()
            self.load_tree_data()
