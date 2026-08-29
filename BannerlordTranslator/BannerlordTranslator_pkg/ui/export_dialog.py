# -*- coding: utf-8 -*-
"""ui/export_dialog.py — نافذة خيارات التصدير (ZIP / مود مستقل)."""
import os
import shutil
import subprocess
import zipfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

class ExportDialog(tk.Toplevel):
    def __init__(self, parent, mod_name, lang_dir, tgt_subfolder, ui_lang, t_func):
        super().__init__(parent)
        self.ui_lang = ui_lang
        self.t = t_func
        self.title(self.t("export_dialog_title"))
        self.geometry("640x390")
        self.resizable(True, True)
        self.mod_name = mod_name
        self.lang_dir = lang_dir
        self.tgt_subfolder = tgt_subfolder

        self.create_ui()

    def create_ui(self):
        tk.Label(self, text=self.t("exp_title"), font=("Segoe UI", 11, "bold"), fg="#107C41").pack(pady=10)

        btn1 = tk.Button(self, text=self.t("exp_b1"), font=("Segoe UI", 10), command=self.open_direct_folder, height=2, bg="#F3F3F3", relief="groove")
        btn1.pack(fill="x", padx=20, pady=4)

        btn2 = tk.Button(self, text=self.t("exp_b2"), font=("Segoe UI", 10), command=self.export_lang_only, height=2, bg="#F3F3F3", relief="groove")
        btn2.pack(fill="x", padx=20, pady=4)

        btn3 = tk.Button(self, text=self.t("exp_b3"), font=("Segoe UI", 10), command=self.export_standalone_mod, height=2, bg="#F3F3F3", relief="groove")
        btn3.pack(fill="x", padx=20, pady=4)

        btn4 = tk.Button(self, text=self.t("exp_b4"), font=("Segoe UI", 10, "bold"), command=self.export_zip_package, height=2, bg="#107C41", fg="white")
        btn4.pack(fill="x", padx=20, pady=6)

    def open_direct_folder(self):
        target_path = os.path.join(self.lang_dir, self.tgt_subfolder)
        if not os.path.exists(target_path):
            target_path = self.lang_dir
        subprocess.Popen(f'explorer "{os.path.normpath(target_path)}"')

    def export_lang_only(self):
        dest = filedialog.askdirectory(title=self.t("dlg_select_dest_folder"))
        if dest:
            out_path = os.path.join(dest, f"{self.mod_name}_{self.tgt_subfolder}_Data", "ModuleData", "Languages", self.tgt_subfolder)
            os.makedirs(out_path, exist_ok=True)
            self.copy_clean_translation(out_path)
            subprocess.Popen(f'explorer "{os.path.normpath(os.path.join(dest, f"{self.mod_name}_{self.tgt_subfolder}_Data"))}"')
            messagebox.showinfo(self.t("title_done"), self.t("msg_export_done"))

    def export_standalone_mod(self):
        dest = filedialog.askdirectory(title=self.t("dlg_select_dest_folder"))
        if dest:
            mod_root = os.path.join(dest, f"[{self.tgt_subfolder}] {self.mod_name}")
            lang_dest = os.path.join(mod_root, "ModuleData", "Languages", self.tgt_subfolder)
            os.makedirs(lang_dest, exist_ok=True)
            self.copy_clean_translation(lang_dest)
            self.create_submodule_xml(mod_root, self.mod_name)
            subprocess.Popen(f'explorer "{os.path.normpath(mod_root)}"')
            messagebox.showinfo(self.t("title_done"), self.t("msg_standalone_done"))

    def export_zip_package(self):
        dest = filedialog.asksaveasfilename(
            defaultextension=".zip", 
            filetypes=[("ZIP Archive", "*.zip")], 
            initialfile=f"{self.mod_name}_{self.tgt_subfolder}_Translation.zip", 
            title=self.t("dlg_save_zip")
        )
        if dest:
            tgt_folder_src = os.path.join(self.lang_dir, self.tgt_subfolder)
            with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
                if os.path.exists(tgt_folder_src):
                    for file in os.listdir(tgt_folder_src):
                        if file == ".diff_state.json":
                            continue
                        full = os.path.join(tgt_folder_src, file)
                        if os.path.isfile(full):
                            z.write(full, os.path.join(self.mod_name, "ModuleData", "Languages", self.tgt_subfolder, file))

            subprocess.Popen(f'explorer /select,"{os.path.normpath(dest)}"')
            messagebox.showinfo(self.t("title_done"), self.t("msg_zip_done"))

    def copy_clean_translation(self, dst_folder):
        tgt_folder_src = os.path.join(self.lang_dir, self.tgt_subfolder)
        if os.path.exists(tgt_folder_src):
            for item in os.listdir(tgt_folder_src):
                if item == ".diff_state.json":
                    continue
                s = os.path.join(tgt_folder_src, item)
                d = os.path.join(dst_folder, item)
                if os.path.isfile(s):
                    shutil.copy2(s, d)

    def create_submodule_xml(self, target_folder, orig_name):
        sub_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<Module>
    <Name value="[{self.tgt_subfolder}] {orig_name}"/>
    <Id value="{orig_name}_{self.tgt_subfolder}"/>
    <Version value="v1.0.0"/>
    <SingleplayerModule value="true"/>
    <MultiplayerModule value="false"/>
    <DependedModules>
        <DependedModule Id="{orig_name}"/>
    </DependedModules>
</Module>"""
        with open(os.path.join(target_folder, "SubModule.xml"), "w", encoding="utf-8") as f:
            f.write(sub_xml)
