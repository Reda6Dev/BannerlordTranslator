# -*- coding: utf-8 -*-
"""
ui/main_window.py — النافذة الرئيسية (واجهة Tkinter فقط).

كل منطق الترجمة الفعلي انتقل لـ core/translator_engine.py (TranslatorEngine).
هذا الملف مسؤول فقط عن: بناء الواجهة، قراءة اختيارات المستخدم، وتحويل
إشارات المحرك (on_progress/on_log/on_finish/on_error) لتحديثات فعلية
بالشاشة عبر root.after() (عشان يضل التحديث Thread-safe).
"""
import json
import locale
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import winsound
except ImportError:
    class _WinsoundStub:
        MB_ICONASTERISK = 0
        @staticmethod
        def MessageBeep(*a, **k):
            pass
    winsound = _WinsoundStub()

from ..data.languages import OFFICIAL_LANGUAGES
from ..data.ui_texts import UI_TEXTS
from ..core.paths import APP_DIR, CONFIG_FILE, GLOSSARY_FILE, TM_FILE
from ..core.logger import write_log_line
from ..core.translator_engine import TranslatorEngine
from .widgets import ToolTip
from .reset_dialog import FactoryResetDialog
from .glossary_window import GlossaryManagerDialog
from .help_dialog import HelpNotebookDialog
from .editor import InteractiveEditorDialog
from .batch_dialog import BatchSelectionDialog
from .export_dialog import ExportDialog

EXCLUDED_MODULES = {"native", "sandboxcore", "sandbox", "custombattle", "storymode", "birthanddeath", "arabic", "translation", "fonts"}

# ألوان الواجهة الثابتة (وضع نهاري فقط - لا يوجد وضع ليلي بالبرنامج)
APP_COLORS = {
    "bg": "#F5F6FA", "fg": "#1E1E1E",
    "frame_bg": "#ECEFF1", "frame_fg": "#1E1E1E",
    "entry_bg": "#FFFFFF", "entry_fg": "#1E1E1E",
    "text_bg": "#F8F8F8", "text_fg": "#1E1E1E",
}


class BannerlordTranslatorV12:
    def __init__(self, root):
        self.root = root
        self.ui_lang = self.detect_initial_language()
        self.root.title(self.t("title"))
        self.root.geometry("900x700")
        self.root.minsize(820, 620)
        self.root.resizable(True, True)

        self.font_main = ("Segoe UI", 10)
        self.font_bold = ("Segoe UI", 10, "bold")

        self.manual_selected_mods = []

        self.engine = TranslatorEngine(
            t_func=self.t,
            on_progress=self._handle_engine_progress,
            on_log=self._handle_engine_log,
            on_finish=self._handle_engine_finish,
            on_error=self._handle_engine_error,
        )

        self.build_gui()

    def load_config_settings(self):
        if not os.path.exists(CONFIG_FILE):
            return {}
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            return loaded if isinstance(loaded, dict) else {}
        except Exception as e:
            write_log_line("WARN", f"Failed to read config.json: {e}")
            return {}

    def save_config_settings(self, **updates):
        cfg = self.load_config_settings()
        cfg.update(updates)
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            write_log_line("WARN", f"Failed to save config.json: {e}")

    def detect_initial_language(self):
        cfg = self.load_config_settings()
        saved = cfg.get("ui_language")
        if saved in OFFICIAL_LANGUAGES:
            return saved
        try:
            sys_locale = locale.getdefaultlocale()[0]
            if sys_locale:
                sys_lang = sys_locale.split("_")[0].lower()
                if sys_lang in OFFICIAL_LANGUAGES:
                    return sys_lang
        except Exception as e:
            write_log_line("WARN", f"Failed to detect system locale: {e}")
        return "ar"

    def save_language_preference(self, lang_code):
        self.save_config_settings(ui_language=lang_code)

    def get_saved_engine_index(self):
        cfg = self.load_config_settings()
        try:
            saved_index = int(cfg.get("selected_engine", 0))
        except (TypeError, ValueError):
            saved_index = 0
        engines = [self.t("eng_google"), self.t("eng_deepl")]
        return saved_index if 0 <= saved_index < len(engines) else 0

    def restore_saved_engine_state(self):
        cfg = self.load_config_settings()
        saved_index = self.get_saved_engine_index()
        engines = [self.t("eng_google"), self.t("eng_deepl")]
        self.engine_cb.set(engines[saved_index])
        self.save_config_settings(selected_engine=saved_index)

        saved_key = str(cfg.get("deepl_api_key", "")).strip()
        self.api_key_entry.config(state="normal")
        self.api_key_entry.delete(0, tk.END)
        if saved_key:
            self.api_key_entry.insert(0, saved_key)

        if saved_index == 1:
            self.api_key_entry.config(state="normal")
            self.api_key_lbl.config(fg="#000000")
        else:
            self.api_key_entry.config(state="disabled")
            self.api_key_lbl.config(fg="#888888")

    def execute_batch(self, selected_mods):
        if not selected_mods:
            return

        self.start_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.export_btn.config(state="disabled")
        self.edit_btn.config(state="disabled")

        src_idx = self.src_lang_cb.current()
        src_code = "auto"
        if src_idx > 0:
            src_name = self.src_lang_cb.get()
            for code, conf in OFFICIAL_LANGUAGES.items():
                if conf["name"] == src_name:
                    src_code = conf["code"]
                    break

        tgt_name = self.tgt_lang_cb.get()
        tgt_conf = None
        for code, conf in OFFICIAL_LANGUAGES.items():
            if conf["name"] == tgt_name:
                tgt_conf = conf
                break

        engine_index = self.engine_cb.current()
        api_key = self.api_key_entry.get().strip() if engine_index == 1 else None
        if engine_index == 1:
            self.save_config_settings(deepl_api_key=api_key or "")

        self.engine.configure(
            delay=self.delay_var.get(),
            smart_cache_enabled=self.smart_cache_var.get(),
            apply_glossary_enabled=self.glossary_var.get(),
        )

        threading.Thread(
            target=self.engine.run_batch,
            args=(selected_mods, src_code, tgt_conf, engine_index),
            kwargs={"api_key": api_key},
            daemon=True,
        ).start()

    def _handle_engine_progress(self, current, total, status_text):
        self.root.after(0, self._update_progress_ui, current, total, status_text)

    def _update_progress_ui(self, current, total, status_text):
        if current is not None and total is not None:
            self.progress_bar["maximum"] = total
            self.progress_bar["value"] = current
        if status_text:
            self.status_label.config(text=status_text)

    def _handle_engine_log(self, message, level=None):
        self.log(message, level)

    def _handle_engine_finish(self, report):
        self.root.after(0, self._on_engine_finish_ui, report)

    def _on_engine_finish_ui(self, report):
        self.start_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")

        if report.get("canceled"):
            self.handle_rollback()
            return

        if report.get("zero_strings"):
            self.status_label.config(text=self.t("waiting"))
            messagebox.showwarning(self.t("title_notice"), self.t("msg_zero_strings_found"))
            return

        self.status_label.config(text=self.t("status_done"))
        self.export_btn.config(state="normal")
        self.edit_btn.config(state="normal")
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass
        messagebox.showinfo(self.t("success_title"), self.t("success_msg"))

    def _handle_engine_error(self, exc):
        self.root.after(0, self._on_engine_error_ui, exc)

    def _on_engine_error_ui(self, exc):
        self.start_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        messagebox.showerror(self.t("title_engine_error"), str(exc))

    def handle_rollback(self):
        self.status_label.config(text=self.t("log_op_canceled").strip())
        self.log(self.t("log_op_canceled"))
        if messagebox.askyesno(self.t("cancel_confirm_title"), self.t("cancel_confirm_msg")):
            ok, failed_count = self.engine.rollback_files()
            if not ok:
                self.log(self.t("log_rollback_partial").format(n=failed_count))
            else:
                self.log(self.t("log_rollback_ok"))

    def open_reset_dialog(self):
        FactoryResetDialog(self.root, self.execute_factory_reset, self.ui_lang, self.t)

    def execute_factory_reset(self, del_config, del_glossary):
        try:
            if del_config and os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)
            if del_glossary and os.path.exists(GLOSSARY_FILE):
                os.remove(GLOSSARY_FILE)
            if del_glossary and os.path.exists(TM_FILE):
                os.remove(TM_FILE)
        except Exception as e:
            write_log_line("WARN", f"Factory reset cleanup issue: {e}")

        if del_config:
            self.ui_lang = "ar"
            self.ui_lang_cb.set(OFFICIAL_LANGUAGES["ar"]["name"])
            self.on_ui_language_selected()

        if del_glossary:
            self.engine.reset_glossary_to_default()
            self.engine.clear_translation_memory()

        messagebox.showinfo(self.t("reset_done_title"), self.t("reset_done_msg"))

    def t(self, key):
        lang_dict = UI_TEXTS.get(self.ui_lang, UI_TEXTS.get("en", {}))
        return lang_dict.get(key, UI_TEXTS["en"].get(key, ""))
    def build_gui(self):
        top_bar = tk.Frame(self.root, padx=6, pady=4, bg="#ECEFF1")
        top_bar.pack(fill="x")

        self.title_lbl = tk.Label(top_bar, text=self.t("title"), font=("Segoe UI", 9, "bold"), fg="#107C41", bg="#ECEFF1")
        self.title_lbl.pack(side="left", padx=2)

        lang_names = [conf["name"] for conf in OFFICIAL_LANGUAGES.values()]
        self.ui_lang_cb = ttk.Combobox(top_bar, values=lang_names, state="readonly", width=16, font=("Segoe UI", 9, "bold"))
        
        current_name = OFFICIAL_LANGUAGES[self.ui_lang]["name"]
        self.ui_lang_cb.set(current_name)
        self.ui_lang_cb.pack(side="right", padx=2)
        self.ui_lang_cb.bind("<<ComboboxSelected>>", self.on_ui_language_selected)

        self.ui_lbl = tk.Label(top_bar, text=self.t("ui_lbl"), font=("Segoe UI", 8, "bold"), bg="#ECEFF1")
        self.ui_lbl.pack(side="right", padx=1)

        self.glossary_btn = tk.Button(top_bar, text=self.t("glossary_btn"), command=self.open_glossary_manager, font=("Segoe UI", 8, "bold"), bg="#0288D1", fg="white", padx=4, relief="groove")
        self.glossary_btn.pack(side="right", padx=2)
        ToolTip(self.glossary_btn, lambda: self.t("tip_glossary_btn"))

        self.help_btn = tk.Button(top_bar, text=self.t("help_btn"), command=self.show_custom_help, font=("Segoe UI", 8, "bold"), bg="#CFD8DC", padx=4, relief="groove")
        self.help_btn.pack(side="right", padx=2)
        ToolTip(self.help_btn, lambda: self.t("tip_help"))

        self.reset_btn = tk.Button(top_bar, text=self.t("reset_btn"), command=self.open_reset_dialog, font=("Segoe UI", 8), bg="#FFCDD2", fg="#B71C1C", padx=3, relief="groove")
        self.reset_btn.pack(side="right", padx=2)
        ToolTip(self.reset_btn, lambda: self.t("tip_reset"))

        self.path_frame = tk.LabelFrame(self.root, text=self.t("sec1"), font=self.font_bold, padx=10, pady=8)
        self.path_frame.pack(fill="x", padx=12, pady=4)

        self.path_entry = tk.Entry(self.path_frame, font=self.font_main)
        self.path_entry.pack(side="left", padx=4, fill="x", expand=True)
        ToolTip(self.path_entry, lambda: self.t("tip_path"))

        self.single_btn = tk.Button(self.path_frame, text=self.t("browse_single"), command=self.browse_single_folder, font=self.font_main, bg="#0078D7", fg="white", padx=8)
        self.single_btn.pack(side="left", padx=2)
        ToolTip(self.single_btn, lambda: self.t("tip_single"))

        self.multi_btn = tk.Button(self.path_frame, text=self.t("browse_multi"), command=self.open_manual_mod_selector, font=self.font_bold, bg="#2B579A", fg="white", padx=8)
        self.multi_btn.pack(side="left", padx=2)
        ToolTip(self.multi_btn, lambda: self.t("tip_multi"))

        self.opt_frame = tk.LabelFrame(self.root, text=self.t("sec2"), font=self.font_bold, padx=10, pady=8)
        self.opt_frame.pack(fill="x", padx=12, pady=4)

        self.lbl_src = tk.Label(self.opt_frame, text=self.t("src_lang"), font=self.font_main)
        self.lbl_src.grid(row=0, column=0, sticky="w", padx=4, pady=3)

        self.src_lang_cb = ttk.Combobox(self.opt_frame, state="readonly", font=self.font_main, width=24)
        self.update_src_combobox_values()
        self.src_lang_cb.current(0)
        self.src_lang_cb.grid(row=0, column=1, padx=4, pady=3)
        ToolTip(self.src_lang_cb, lambda: self.t("tip_src"))

        self.lbl_tgt = tk.Label(self.opt_frame, text=self.t("tgt_lang"), font=self.font_main)
        self.lbl_tgt.grid(row=0, column=2, sticky="w", padx=10, pady=3)

        self.tgt_lang_cb = ttk.Combobox(self.opt_frame, values=lang_names, state="readonly", font=self.font_main, width=24)
        self.sync_target_language()
        self.tgt_lang_cb.grid(row=0, column=3, padx=4, pady=3)
        ToolTip(self.tgt_lang_cb, lambda: self.t("tip_tgt"))

        self.lbl_engine = tk.Label(self.opt_frame, text=self.t("engine"), font=self.font_main)
        self.lbl_engine.grid(row=1, column=0, sticky="w", padx=4, pady=4)

        self.engine_cb = ttk.Combobox(self.opt_frame, state="readonly", font=self.font_main, width=26)
        self.update_engine_combobox_values()
        self.engine_cb.grid(row=1, column=1, padx=4, pady=4)
        self.engine_cb.bind("<<ComboboxSelected>>", self.on_engine_change)
        ToolTip(self.engine_cb, lambda: self.t("tip_engine"))

        self.api_key_lbl = tk.Label(self.opt_frame, text=self.t("deepl_key"), font=self.font_main, fg="#888888")
        self.api_key_lbl.grid(row=1, column=2, sticky="w", padx=10, pady=4)

        self.api_key_entry = tk.Entry(self.opt_frame, font=self.font_main, width=24, state="disabled")
        self.api_key_entry.grid(row=1, column=3, padx=4, pady=4)
        self.restore_saved_engine_state()
        ToolTip(self.api_key_entry, lambda: self.t("tip_key"))

        delay_f = tk.Frame(self.opt_frame)
        delay_f.grid(row=2, column=0, columnspan=4, sticky="we", pady=4)

        self.lbl_delay = tk.Label(delay_f, text=self.t("delay_lbl"), font=self.font_main)
        self.lbl_delay.pack(side="left", padx=4)

        self.delay_var = tk.DoubleVar(value=0.50)
        self.delay_scale = ttk.Scale(delay_f, from_=0.00, to=2.00, variable=self.delay_var, orient="horizontal", length=180, command=self.on_delay_slider_change)
        self.delay_scale.pack(side="left", padx=6)
        ToolTip(self.delay_scale, lambda: self.t("tip_delay"))

        self.delay_val_lbl = tk.Label(delay_f, text=f"{self.delay_var.get():.2f}s", font=self.font_bold, fg="#107C41", width=6)
        self.delay_val_lbl.pack(side="left", padx=2)
        ToolTip(self.delay_val_lbl, lambda: self.t("tip_delay"))

        self.lbl_delay_desc = tk.Label(delay_f, text=self.t("delay_desc"), font=("Segoe UI", 8), fg="#666666")
        self.lbl_delay_desc.pack(side="left", padx=6)

        check_f = tk.Frame(self.opt_frame)
        check_f.grid(row=3, column=0, columnspan=4, sticky="w", pady=3)

        self.smart_cache_var = tk.BooleanVar(value=True)
        self.cache_chk = tk.Checkbutton(check_f, text=self.t("cache"), variable=self.smart_cache_var, font=self.font_main)
        self.cache_chk.pack(side="left", padx=4)
        ToolTip(self.cache_chk, lambda: self.t("tip_cache"))

        self.glossary_var = tk.BooleanVar(value=True)
        self.glossary_chk = tk.Checkbutton(check_f, text=self.t("glossary"), variable=self.glossary_var, font=self.font_main)
        self.glossary_chk.pack(side="left", padx=15)
        ToolTip(self.glossary_chk, lambda: self.t("tip_glossary"))

        action_frame = tk.Frame(self.root, padx=12, pady=4)
        action_frame.pack(fill="x")

        self.start_btn = tk.Button(action_frame, text=self.t("start_btn"), command=self.start_workflow, font=("Segoe UI", 10, "bold"), bg="#107C41", fg="white", height=2)
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))
        ToolTip(self.start_btn, lambda: self.t("tip_start"))

        self.cancel_btn = tk.Button(action_frame, text=self.t("cancel_btn"), command=self.request_cancel, font=self.font_bold, bg="#D83B01", fg="white", state="disabled", height=2, padx=14)
        self.cancel_btn.pack(side="right")
        ToolTip(self.cancel_btn, lambda: self.t("tip_cancel"))

        bottom_frame = tk.Frame(self.root, padx=12, pady=6)
        bottom_frame.pack(side="bottom", fill="x")

        self.edit_btn = tk.Button(bottom_frame, text=self.t("edit_btn"), command=self.open_text_editor, font=self.font_bold, bg="#495057", fg="white", state="disabled", height=2, padx=12)
        self.edit_btn.pack(side="left", padx=(0, 4))
        ToolTip(self.edit_btn, lambda: self.t("tip_edit"))

        self.export_btn = tk.Button(bottom_frame, text=self.t("export_btn"), command=self.open_export_window, font=self.font_bold, bg="#0078D7", fg="white", state="disabled", height=2)
        self.export_btn.pack(side="left", fill="x", expand=True)
        ToolTip(self.export_btn, lambda: self.t("tip_export"))

        self.progress_frame = tk.LabelFrame(self.root, text=self.t("sec3"), font=self.font_bold, padx=10, pady=6)
        self.progress_frame.pack(fill="both", expand=True, padx=12, pady=4)

        self.status_label = tk.Label(self.progress_frame, text=self.t("waiting"), font=self.font_main, anchor="w")
        self.status_label.pack(fill="x")

        self.progress_bar = ttk.Progressbar(self.progress_frame, mode="determinate")
        self.progress_bar.pack(fill="x", pady=4)

        log_scroll = ttk.Scrollbar(self.progress_frame)
        log_scroll.pack(side="right", fill="y")

        self.log_text = tk.Text(self.progress_frame, font=("Consolas", 9), height=7, state="disabled", bg="#F8F8F8", yscrollcommand=log_scroll.set)
        self.log_text.pack(fill="both", expand=True)
        log_scroll.config(command=self.log_text.yview)

        self.apply_light_theme()

    def apply_light_theme(self):
        """
        يثبّت ألوان الواجهة على الوضع النهاري (الوحيد المتاح بالبرنامج - لا
        يوجد وضع ليلي ولا أي إمكانية تبديل). يمشي على شجرة الواجهة كاملة
        بشكل تكراري ويتأكد إن كل النصوص (Labels/Entry/Text) تظهر بلون داكن
        واضح فوق خلفية فاتحة.
        """
        self.root.config(bg=APP_COLORS["bg"])

        style = ttk.Style()
        try:
            style.theme_use("clam")  # لازم قبل تخصيص الألوان، لأن الثيمات الافتراضية بويندوز/ماك تتجاهل الألوان المخصصة
        except Exception:
            pass
        style.configure("TCombobox", fieldbackground=APP_COLORS["entry_bg"], background=APP_COLORS["frame_bg"], foreground=APP_COLORS["entry_fg"])
        style.configure("Horizontal.TScale", background=APP_COLORS["frame_bg"])
        style.configure("TProgressbar", background="#107C41", troughcolor=APP_COLORS["frame_bg"])
        style.configure("TScrollbar", background=APP_COLORS["frame_bg"], troughcolor=APP_COLORS["bg"])

        self._style_widget(self.root)

    def _style_widget(self, widget):
        cls = widget.winfo_class()
        try:
            if cls in ("Frame", "Labelframe"):
                widget.config(bg=APP_COLORS["frame_bg"])
            elif cls == "Label":
                widget.config(bg=APP_COLORS["frame_bg"], fg=APP_COLORS["fg"])
            elif cls == "Entry":
                widget.config(bg=APP_COLORS["entry_bg"], fg=APP_COLORS["entry_fg"], insertbackground=APP_COLORS["entry_fg"])
            elif cls == "Text":
                widget.config(bg=APP_COLORS["text_bg"], fg=APP_COLORS["text_fg"], insertbackground=APP_COLORS["text_fg"])
            elif cls == "Checkbutton":
                widget.config(bg=APP_COLORS["frame_bg"], fg=APP_COLORS["fg"], activebackground=APP_COLORS["frame_bg"], selectcolor=APP_COLORS["entry_bg"])
            # الأزرار (Button) نتعمّد ما نلمسها - ألوانها (أخضر/أحمر/أزرق) تحمل معنى وظيفي
            # (بدء/إلغاء/تصدير...) ونفضّل تضل واضحة بنفس اللون دايمًا.
        except Exception:
            pass

        for child in widget.winfo_children():
            self._style_widget(child)

    def sync_target_language(self):
        if self.ui_lang in OFFICIAL_LANGUAGES:
            target_name = OFFICIAL_LANGUAGES[self.ui_lang]["name"]
            self.tgt_lang_cb.set(target_name)
    def on_delay_slider_change(self, val):
        self.delay_val_lbl.config(text=f"{float(val):.2f}s")
    def update_src_combobox_values(self):
        curr = self.src_lang_cb.current()
        lang_names = [conf["name"] for conf in OFFICIAL_LANGUAGES.values()]
        self.src_lang_cb.config(values=[self.t("auto_src")] + lang_names)
        self.src_lang_cb.current(curr if curr >= 0 else 0)
    def update_engine_combobox_values(self):
        curr = self.engine_cb.current()
        engines = [self.t("eng_google"), self.t("eng_deepl")]
        self.engine_cb.config(values=engines)
        if curr == 4:
            curr = 1
        self.engine_cb.current(curr if 0 <= curr < len(engines) else 0)
    def on_ui_language_selected(self, event=None):
        selected_name = self.ui_lang_cb.get()
        for code, conf in OFFICIAL_LANGUAGES.items():
            if conf["name"] == selected_name:
                self.ui_lang = code
                break
        self.save_language_preference(self.ui_lang)
        
        self.root.title(self.t("title"))
        self.title_lbl.config(text=self.t("title"))
        self.ui_lbl.config(text=self.t("ui_lbl"))
        self.help_btn.config(text=self.t("help_btn"))
        self.reset_btn.config(text=self.t("reset_btn"))
        self.glossary_btn.config(text=self.t("glossary_btn"))
        
        self.path_frame.config(text=self.t("sec1"))
        self.single_btn.config(text=self.t("browse_single"))
        self.multi_btn.config(text=self.t("browse_multi"))
        
        self.opt_frame.config(text=self.t("sec2"))
        self.lbl_src.config(text=self.t("src_lang"))
        self.lbl_tgt.config(text=self.t("tgt_lang"))
        self.lbl_engine.config(text=self.t("engine"))
        self.api_key_lbl.config(text=self.t("deepl_key"))
        self.lbl_delay.config(text=self.t("delay_lbl"))
        self.lbl_delay_desc.config(text=self.t("delay_desc"))
        self.cache_chk.config(text=self.t("cache"))
        self.glossary_chk.config(text=self.t("glossary"))
        
        self.update_src_combobox_values()
        self.update_engine_combobox_values()
        self.sync_target_language()
        
        self.start_btn.config(text=self.t("start_btn"))
        self.cancel_btn.config(text=self.t("cancel_btn"))
        
        self.progress_frame.config(text=self.t("sec3"))
        if not self.engine.is_running:
            self.status_label.config(text=self.t("waiting"))
            
        self.export_btn.config(text=self.t("export_btn"))
        self.edit_btn.config(text=self.t("edit_btn"))
    def on_engine_change(self, event=None):
        idx = self.engine_cb.current()
        self.save_config_settings(selected_engine=idx)

        if idx == 1:
            self.api_key_lbl.config(fg="#000000")
            self.api_key_entry.config(state="normal")
            api_key = self.api_key_entry.get().strip()
            if api_key:
                self.save_config_settings(deepl_api_key=api_key)
        else:
            self.api_key_lbl.config(fg="#888888")
            self.api_key_entry.config(state="disabled")
    def log(self, message, level=None):
        if level is None:
            if message.startswith("[!]") or "Error" in message:
                level = "ERROR"
            elif message.startswith("[⚠]") or message.startswith("[-]"):
                level = "WARN"
            else:
                level = "INFO"
        write_log_line(level, message)
        self.root.after(0, self._append_log, message)
    def _append_log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")
    def show_custom_help(self):
        HelpNotebookDialog(self.root, self.ui_lang, self.t)
    def open_glossary_manager(self):
        GlossaryManagerDialog(self.root, self.engine.glossary_data, self.engine.save_glossary, self.ui_lang, self.t)
    def browse_single_folder(self):
        folder = filedialog.askdirectory(title=self.t("sec1"))
        if folder:
            self.manual_selected_mods = []
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, folder)
    def open_manual_mod_selector(self):
        root_dir = filedialog.askdirectory(title=self.t("sec1"))
        if not root_dir:
            return

        available_mods = []
        for item in os.listdir(root_dir):
            full_item_path = os.path.join(root_dir, item)
            if os.path.isdir(full_item_path) and os.path.exists(os.path.join(full_item_path, "SubModule.xml")):
                mod_name = item
                if mod_name.lower() in EXCLUDED_MODULES:
                    continue
                can_trans, reason = self.engine.check_mod_translatable(full_item_path)
                available_mods.append((full_item_path, mod_name, can_trans, reason))

        if not available_mods:
            messagebox.showwarning(self.t("title_notice"), self.t("msg_no_valid_mods"))
            return

        BatchSelectionDialog(self.root, available_mods, self.on_manual_selection_confirmed, self.ui_lang, self.t)
    def on_manual_selection_confirmed(self, selected_paths):
        self.manual_selected_mods = selected_paths
        self.path_entry.delete(0, tk.END)
        self.path_entry.insert(0, f"[{len(selected_paths)} Mods Selected]")
    def request_cancel(self):
        if self.engine.is_running:
            self.engine.cancel_requested = True
            self.log(self.t("log_canceling"))
    def start_workflow(self):
        if self.manual_selected_mods:
            mods_to_process = self.manual_selected_mods
        else:
            path = self.path_entry.get().strip()
            if not path or not os.path.isdir(path):
                messagebox.showerror(self.t("title_error"), self.t("msg_invalid_dir"))
                return

            sub_items = [os.path.join(path, d) for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
            is_modules_root = any(os.path.exists(os.path.join(d, "SubModule.xml")) for d in sub_items)

            if is_modules_root:
                available_mods = []
                for mod_dir in sub_items:
                    mod_name = os.path.basename(mod_dir)
                    if mod_name.lower() in EXCLUDED_MODULES:
                        continue
                    can_trans, reason = self.engine.check_mod_translatable(mod_dir)
                    available_mods.append((mod_dir, mod_name, can_trans, reason))

                BatchSelectionDialog(self.root, available_mods, self.execute_batch, self.ui_lang, self.t)
                return
            else:
                mods_to_process = [path]

        self.execute_batch(mods_to_process)
    def open_text_editor(self):
        if not self.engine.last_translated_files:
            messagebox.showinfo(self.t("title_notice"), self.t("msg_no_files_edit"))
            return
        tgt_code = self.engine.current_tgt_conf["code"] if self.engine.current_tgt_conf else "ar"
        InteractiveEditorDialog(self.root, self.engine.last_translated_files, self.engine.original_cache, self.engine.newly_updated_ids, self.engine.changed_ids, self.engine.placeholder_issues, self.engine.empty_ids, self.engine.untranslated_ids, self.engine.glossary_data.get(tgt_code, {}), self.ui_lang, self.t, retranslate_func=self.retranslate_line, on_save_sync=self.sync_saved_edits)

    def sync_saved_edits(self, id_text_pairs, file_path):
        """
        تُستدعى من المحرر التفاعلي بعد كل عملية حفظ ناجحة. تحدّث ذاكرة
        الترجمة العامة (translation_memory.json) وملف .diff_state.json
        الخاص بمجلد هذا الملف بالنصوص الجديدة اللي عدّلها المستخدم يدويًا -
        عشان أي تشغيل قادم (لنفس المود أو مود ثاني فيه نفس الجملة الإنجليزية)
        يستخدم التصحيح اليدوي بدل ما يرجّع الترجمة القديمة فوقه.
        """
        tgt_conf = self.engine.current_tgt_conf
        if not tgt_conf:
            return
        tgt_code = tgt_conf["code"]

        tm_changed = False
        for str_id, new_text in id_text_pairs:
            orig_text = self.engine.original_cache.get(str_id, "")
            if orig_text and new_text.strip():
                self.engine.translation_memory.setdefault(tgt_code, {})[orig_text] = new_text
                tm_changed = True
        if tm_changed:
            self.engine.save_translation_memory()

        out_dir = os.path.dirname(file_path)
        file_name = os.path.basename(file_path)
        diff_state = self.engine.load_diff_state(out_dir)
        file_state = diff_state.get(file_name, {})
        for str_id, new_text in id_text_pairs:
            orig_text = self.engine.original_cache.get(str_id, "")
            existing = file_state.get(str_id, {})
            file_state[str_id] = {
                "src": orig_text if orig_text else existing.get("src", ""),
                "text": new_text,
                "ph_ok": existing.get("ph_ok", True),
            }
        diff_state[file_name] = file_state
        self.engine.save_diff_state(out_dir, diff_state)

    def retranslate_line(self, text, on_done):
        """
        يترجم جملة واحدة بمحرك الترجمة النشط حاليًا بالواجهة (مو بالضرورة
        نفس المحرك المستخدم بآخر عملية ترجمة كاملة)، بخيط منفصل عشان ما
        يجمّد المحرر. يستدعي on_done(result_text, error) بالخيط الرئيسي
        عبر root.after() لضمان التحديث الآمن للواجهة.
        """
        engine_index = self.engine_cb.current()
        api_key = self.api_key_entry.get().strip() if engine_index == 1 else None
        tgt_conf = self.engine.current_tgt_conf

        def worker():
            try:
                translator = self.engine.get_translator("auto", tgt_conf["code"], engine_index, api_key=api_key)
                result_text, ok, missing = self.engine.translate_single_text(text, translator, tgt_conf["code"])
                self.root.after(0, on_done, result_text, None)
            except Exception as e:
                self.root.after(0, on_done, None, e)

        threading.Thread(target=worker, daemon=True).start()

    def open_export_window(self):
        if not self.engine.last_target_dir or not os.path.exists(self.engine.last_target_dir):
            messagebox.showerror(self.t("title_error"), self.t("msg_no_files_export"))
            return
        ExportDialog(self.root, self.engine.last_mod_name, self.engine.last_target_dir, self.engine.current_tgt_conf["folder"], self.ui_lang, self.t)
