# -*- coding: utf-8 -*-
"""ui/editor.py — المحرر التفاعلي: مراجعة وتعديل النصوص المترجمة يدويًا،
مع شارات NEW/CHANGED/KEPT وفحص Placeholder وميزة إعادة الفحص والتنقل بين الأخطاء."""
import os
import re
import tkinter as tk
from tkinter import ttk, messagebox
import xml.etree.ElementTree as ET

from ..core.logger import write_log_line

class InteractiveEditorDialog(tk.Toplevel):
    def __init__(self, parent, xml_file_paths, original_cache, newly_updated_ids, changed_ids, placeholder_issues, empty_ids, untranslated_ids, current_glossary, ui_lang, t_func, retranslate_func=None, on_save_sync=None):
        super().__init__(parent)
        self.ui_lang = ui_lang
        self.t = t_func
        self.retranslate_func = retranslate_func  # (text, on_done) -> None، تمرره الواجهة الرئيسية
        self.on_save_sync = on_save_sync  # (id_text_pairs, file_path) -> None، لمزامنة ذاكرة الترجمة/Smart Diff بعد الحفظ
        self.title(self.t("edit_title"))
        self.geometry("1060x600")
        self.xml_file_paths = xml_file_paths
        self.original_cache = original_cache
        self.newly_updated_ids = newly_updated_ids
        self.changed_ids = changed_ids
        self.placeholder_issues = placeholder_issues
        self.empty_ids = empty_ids
        self.untranslated_ids = untranslated_ids
        self.current_glossary = current_glossary
        self.current_tree = None
        self.current_path = None
        self.entries = []
        self.row_widgets = []  # [(row_frame, str_id, orig_val, ent)] - للفلترة بشريط البحث
        self.issue_widgets = []
        self.all_issues = []
        self.current_issue_index = -1
        self.active_entry = None  # (elem, ent) الخاصين بالصف المحدد حاليًا بمربع التعديل الآمن

        self.create_ui()
        self.bind("<Control-r>", lambda e: self.retranslate_selected_line())
        self.bind("<Control-R>", lambda e: self.retranslate_selected_line())

    def create_ui(self):
        top_f = tk.Frame(self, padx=12, pady=8, bg="#ECEFF1")
        top_f.pack(fill="x")

        tk.Label(top_f, text=self.t("edit_select"), font=("Segoe UI", 10, "bold"), bg="#ECEFF1").pack(side="left", padx=5)

        self.file_cb = ttk.Combobox(top_f, values=[os.path.basename(p) for p in self.xml_file_paths], state="readonly", width=35)
        self.file_cb.pack(side="left", padx=5)
        self.file_cb.bind("<<ComboboxSelected>>", self.load_file)

        # شريط التنقل بين الأخطاء
        self.nav_frame = tk.Frame(top_f, bg="#ECEFF1")
        self.nav_frame.pack(side="left", padx=10)

        self.prev_btn = tk.Button(self.nav_frame, text=self.t("nav_prev"), command=self.go_to_prev_issue, font=("Segoe UI", 9, "bold"), bg="#546E7A", fg="white", width=8)
        self.prev_btn.pack(side="left", padx=2)

        self.issue_counter_lbl = tk.Label(self.nav_frame, text="", font=("Segoe UI", 9, "bold"), bg="#ECEFF1", fg="#D32F2F")
        self.issue_counter_lbl.pack(side="left", padx=8)

        self.next_btn = tk.Button(self.nav_frame, text=self.t("nav_next"), command=self.go_to_next_issue, font=("Segoe UI", 9, "bold"), bg="#E53935", fg="white", width=8)
        self.next_btn.pack(side="left", padx=2)

        save_btn = tk.Button(top_f, text=self.t("edit_save"), command=self.save_current_file, font=("Segoe UI", 10, "bold"), bg="#107C41", fg="white", padx=12)
        save_btn.pack(side="right", padx=5)

        self.rescan_btn = tk.Button(top_f, text=self.t("rescan_btn"), command=self.rescan_all_errors, font=("Segoe UI", 9, "bold"), bg="#FF9800", fg="white", padx=10)
        self.rescan_btn.pack(side="right", padx=5)

        hdr_frame = tk.Frame(self, padx=15, pady=4, bg="#DFE4EA")
        hdr_frame.pack(fill="x")
        
        tk.Label(hdr_frame, text=self.t("edit_status"), font=("Segoe UI", 9, "bold"), width=8, anchor="center", bg="#DFE4EA").pack(side="left", padx=2)
        tk.Label(hdr_frame, text=self.t("edit_id"), font=("Segoe UI", 9, "bold"), width=22, anchor="w", bg="#DFE4EA").pack(side="left", padx=2)
        tk.Label(hdr_frame, text=self.t("edit_orig"), font=("Segoe UI", 9, "bold"), width=34, anchor="w", bg="#DFE4EA").pack(side="left", padx=4)
        tk.Label(hdr_frame, text=self.t("edit_trans"), font=("Segoe UI", 9, "bold"), width=36, anchor="w", bg="#DFE4EA").pack(side="left", fill="x", expand=True, padx=2)
        tk.Label(hdr_frame, text=self.t("edit_glossary"), font=("Segoe UI", 9, "bold"), width=14, anchor="center", bg="#DFE4EA").pack(side="right", padx=4)

        # شريط البحث السريع (يفلتر الجدول فورًا أثناء الكتابة)
        search_frame = tk.Frame(self, padx=15, pady=4, bg="#FAFAFA")
        search_frame.pack(fill="x")
        tk.Label(search_frame, text=self.t("edit_search_label"), font=("Segoe UI", 9), bg="#FAFAFA").pack(side="left", padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var, font=("Segoe UI", 10))
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_var.trace_add("write", lambda *a: self.filter_rows())

        # مربع التعديل الآمن (يحل مشاكل الكتابة بالعربي/RTL داخل خانة الجدول الضيقة)
        bottom_edit_frame = tk.Frame(self, padx=12, pady=8, bg="#F1F2F6")
        bottom_edit_frame.pack(side="bottom", fill="x")

        tk.Label(bottom_edit_frame, text=self.t("edit_selected_label"), font=("Segoe UI", 9, "bold"), bg="#F1F2F6").pack(anchor="w")

        text_row = tk.Frame(bottom_edit_frame, bg="#F1F2F6")
        text_row.pack(fill="x", pady=4)

        self.edit_text = tk.Text(text_row, height=4, font=("Segoe UI", 11), wrap="word")
        self.edit_text.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.edit_text.bind("<Control-KeyPress>", self._on_edit_text_control_key)
        self.edit_text.bind("<Return>", self._on_edit_text_enter)

        update_btn = tk.Button(text_row, text=self.t("edit_update_line"), command=self.update_selected_line, font=("Segoe UI", 10, "bold"), bg="#1976D2", fg="white", padx=12)
        update_btn.pack(side="left", padx=(0, 4))

        self.retranslate_btn = tk.Button(text_row, text=self.t("edit_retranslate_btn"), command=self.retranslate_selected_line, font=("Segoe UI", 10, "bold"), bg="#8E24AA", fg="white", padx=12)
        self.retranslate_btn.pack(side="left")

        container = tk.Frame(self, padx=10, pady=5)
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, background="#FFFFFF")
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, background="#FFFFFF")

        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.bind_mouse_scroll(self)
        self.bind_mouse_scroll(self.canvas)
        self.bind_mouse_scroll(self.scroll_frame)

        self.refresh_issues_list()
        self.update_issue_counter()

        if self.xml_file_paths:
            self.file_cb.current(0)
            self.load_file()

    def bind_mouse_scroll(self, widget):
        widget.bind("<MouseWheel>", self.on_mousewheel)

    def on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def load_file(self, event=None):
        idx = self.file_cb.current()
        target_path = self.xml_file_paths[idx]

        # نحافظ على أي تعديل حي (زر "تحديث السطر") ما انحفظ للقرص بعد، بس
        # لو نفس الملف يُعاد تحميله (مثلاً بعد إعادة الفحص) مو تبديل لملف
        # ثاني - عشان rescan_all_errors ما تمسح تعديل المستخدم قبل ما يحفظ.
        live_edits = {}
        if self.entries and target_path == self.current_path:
            live_edits = {elem.get("id", ""): ent.get() for elem, ent in self.entries}

        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.entries = []
        self.row_widgets = []
        self.issue_widgets = {}
        self.active_entry = None
        self.edit_text.delete("1.0", "end")
        self.search_var.set("")

        self.current_path = target_path
        self.current_tree = ET.parse(self.current_path)

        for s in self.current_tree.getroot().iter("string"):
            str_id = s.get("id", "")
            text_val = live_edits.get(str_id, s.get("text", ""))
            orig_val = self.original_cache.get(str_id, "")
            is_new = str_id in self.newly_updated_ids
            is_changed = str_id in self.changed_ids
            has_ph_issue = str_id in self.placeholder_issues
            is_empty = str_id in self.empty_ids
            is_untranslated = str_id in self.untranslated_ids

            has_glossary_match = any(re.search(rf"\b{re.escape(k)}\b", orig_val, re.IGNORECASE) for k in self.current_glossary.keys())

            row_bg = "#FFEBEE" if (has_ph_issue or is_empty or is_untranslated) else ("#F0FFF0" if is_new else ("#FFFDE7" if is_changed else "#FFFFFF"))
            row = tk.Frame(self.scroll_frame, bg=row_bg, pady=2)
            row.pack(fill="x", expand=True, padx=4)
            self.bind_mouse_scroll(row)
            self.row_widgets.append([row, str_id, orig_val, None])  # العنصر الرابع (ent) يُملأ لاحقًا بعد إنشائه

            if has_ph_issue or is_empty or is_untranslated:
                self.issue_widgets[str_id] = row

            if is_new:
                badge_text, badge_bg, badge_fg = "NEW", "#2ED573", "white"
            elif is_changed:
                badge_text, badge_bg, badge_fg = "CHANGED", "#FFC107", "#3D3D3D"
            else:
                badge_text, badge_bg, badge_fg = "KEPT", "#E4E7EB", "#57606F"
            lbl_badge = tk.Label(row, text=badge_text, font=("Consolas", 8, "bold"), width=7, bg=badge_bg, fg=badge_fg)
            lbl_badge.pack(side="left", padx=2)
            self.bind_mouse_scroll(lbl_badge)

            ph_badge_text = "⚠ PH" if has_ph_issue else "✓"
            ph_badge_bg = "#E53935" if has_ph_issue else "#FAFAFA"
            ph_badge_fg = "white" if has_ph_issue else "#C7C7C7"
            lbl_ph = tk.Label(row, text=ph_badge_text, font=("Consolas", 8, "bold"), width=5, bg=ph_badge_bg, fg=ph_badge_fg)
            lbl_ph.pack(side="left", padx=2)
            self.bind_mouse_scroll(lbl_ph)

            # شارة الـValidator: نص فاضي أو نفس النص الإنجليزي (احتمال ما تُرجم)
            if is_empty:
                qc_text, qc_bg, qc_fg = "∅ EMPTY", "#B71C1C", "white"
            elif is_untranslated:
                qc_text, qc_bg, qc_fg = "=EN?", "#FB8C00", "white"
            else:
                qc_text, qc_bg, qc_fg = "✓", "#FAFAFA", "#C7C7C7"
            lbl_qc = tk.Label(row, text=qc_text, font=("Consolas", 8, "bold"), width=8, bg=qc_bg, fg=qc_fg)
            lbl_qc.pack(side="left", padx=2)
            self.bind_mouse_scroll(lbl_qc)

            lbl_id = tk.Label(row, text=str_id, font=("Consolas", 8, "bold"), width=22, anchor="w", bg="#F1F2F6")
            lbl_id.pack(side="left", padx=2)
            self.bind_mouse_scroll(lbl_id)

            lbl_orig = tk.Label(row, text=orig_val, font=("Segoe UI", 9), width=34, anchor="w", bg="#FAFAFA", fg="#57606F", wraplength=250, justify="left")
            lbl_orig.pack(side="left", padx=4)
            self.bind_mouse_scroll(lbl_orig)

            ent = tk.Entry(row, font=("Segoe UI", 10))
            ent.insert(0, text_val)
            ent.config(state="readonly")
            ent.pack(side="left", fill="x", expand=True, padx=2)
            ent.bind("<Button-1>", lambda e, elem=s, entry=ent: self.select_row_for_editing(elem, entry))
            self.entries.append((s, ent))
            self.row_widgets[-1][3] = ent

            glossary_badge_bg = "#E8F5E9" if has_glossary_match else "#FAFAFA"
            glossary_badge_fg = "#2E7D32" if has_glossary_match else "#9E9E9E"
            glossary_text = "✔" if has_glossary_match else "-"
            lbl_g = tk.Label(row, text=glossary_text, font=("Segoe UI", 8, "bold"), width=12, bg=glossary_badge_bg, fg=glossary_badge_fg)
            lbl_g.pack(side="right", padx=4)
            self.bind_mouse_scroll(lbl_g)

        # لو فيه تنقل جاري، رجّع تظليل السطر الحالي بعد إعادة بناء الجدول
        if 0 <= self.current_issue_index < len(self.all_issues):
            _, current_sid = self.all_issues[self.current_issue_index]
            row_widget = self.issue_widgets.get(current_sid)
            if row_widget:
                self.after(50, lambda: self._scroll_to_row(row_widget))

    def refresh_issues_list(self):
        """
        يجمع كل الأخطاء الحالية (Placeholder / فاضي / يحتمل غير مترجم) من كل الملفات
        بقائمة واحدة self.all_issues = [(مسار_الملف, str_id), ...] للتنقل بينها.
        """
        self.all_issues = []
        issue_ids = self.placeholder_issues | self.empty_ids | self.untranslated_ids
        if not issue_ids:
            return
        for path in self.xml_file_paths:
            try:
                tree = ET.parse(path)
                for s in tree.getroot().iter("string"):
                    sid = s.get("id", "")
                    if sid in issue_ids:
                        self.all_issues.append((path, sid))
            except Exception:
                pass

    def update_issue_counter(self):
        count = len(self.all_issues)
        if count == 0:
            text = self.t("issue_counter_none")
        else:
            current = self.current_issue_index + 1 if self.current_issue_index >= 0 else 1
            text = self.t("issue_counter_fmt").format(current=current, total=count)
        self.issue_counter_lbl.config(text=text)

    def rescan_all_errors(self):
        """
        يعيد فحص كل الملفات من الصفر (نفس منطق Validator) عشان يلتقط أي تعديل
        يدوي سواه المستخدم بالمحرر، ويحدّث قائمة الأخطاء والعداد.

        الملف المفتوح حاليًا بالجدول (self.current_path) يُفحص من self.entries
        مباشرة (القيم المعروضة بالجدول الحي)، مو من القرص - عشان أي تعديل
        سويته بزر "تحديث السطر" ينعكس فورًا هنا حتى لو ما ضغطت "حفظ" بعد.
        باقي الملفات غير المفتوحة حاليًا تُفحص من القرص (ما فيه نسخة حية
        منها بالذاكرة أصلًا).
        """
        self.placeholder_issues.clear()
        self.empty_ids.clear()
        self.untranslated_ids.clear()

        for path in self.xml_file_paths:
            if path == self.current_path and self.entries:
                id_text_pairs = [(elem.get("id", ""), ent.get()) for elem, ent in self.entries]
            else:
                id_text_pairs = []
                try:
                    tree = ET.parse(path)
                    id_text_pairs = [(s.get("id", ""), s.get("text", "")) for s in tree.getroot().iter("string")]
                except Exception as e:
                    write_log_line("WARN", f"Rescan failed to read {path}: {e}")
                    continue

            for str_id, text_val in id_text_pairs:
                orig_val = self.original_cache.get(str_id, "")

                if not text_val.strip():
                    self.empty_ids.add(str_id)
                if orig_val.strip() and text_val.strip() == orig_val.strip():
                    self.untranslated_ids.add(str_id)

                phs = re.findall(r"\{[^{}]+\}|<[^>]+>|\$[A-Za-z_][A-Za-z0-9_]*", orig_val)
                if not all(ph in text_val for ph in phs):
                    self.placeholder_issues.add(str_id)

        self.refresh_issues_list()
        self.current_issue_index = -1
        self.update_issue_counter()
        self.load_file()

        messagebox.showinfo(self.t("title_done"), self.t("rescan_done_msg").format(n=len(self.all_issues)))

    def go_to_next_issue(self):
        if not self.all_issues:
            messagebox.showinfo(self.t("title_notice"), self.t("issue_counter_none"))
            return
        self.current_issue_index = (self.current_issue_index + 1) % len(self.all_issues)
        self._jump_to_current_issue()

    def go_to_prev_issue(self):
        if not self.all_issues:
            messagebox.showinfo(self.t("title_notice"), self.t("issue_counter_none"))
            return
        if self.current_issue_index <= 0:
            self.current_issue_index = len(self.all_issues) - 1
        else:
            self.current_issue_index -= 1
        self._jump_to_current_issue()

    def _jump_to_current_issue(self):
        if not (0 <= self.current_issue_index < len(self.all_issues)):
            return
        target_path, target_id = self.all_issues[self.current_issue_index]
        self.update_issue_counter()

        if target_path != self.current_path:
            try:
                new_idx = self.xml_file_paths.index(target_path)
                self.file_cb.current(new_idx)
                self.load_file()
                return  # load_file بيسوي التمرير والتظليل بنفسه بعد إعادة البناء
            except ValueError:
                return

        row_widget = self.issue_widgets.get(target_id)
        if row_widget:
            self._scroll_to_row(row_widget)

    def _scroll_to_row(self, row_widget):
        try:
            self.canvas.update_idletasks()
            bbox = self.canvas.bbox("all")
            if not bbox:
                return
            total_height = bbox[3] - bbox[1]
            row_y = row_widget.winfo_y()
            if total_height > 0:
                self.canvas.yview_moveto(max(0, (row_y - 40) / total_height))
            orig_bg = row_widget.cget("bg")
            row_widget.config(bg="#FFF59D")
            row_widget.after(800, lambda: row_widget.config(bg=orig_bg) if row_widget.winfo_exists() else None)
        except Exception:
            pass

    def select_row_for_editing(self, elem, ent):
        """
        يحمّل نص أي صف بمربع التعديل الآمن أسفل النافذة عند النقر عليه.
        الجدول يبقى للعرض فقط (Entry بوضع readonly) - التعديل الفعلي
        يصير هنا بمربع نص كبير يتفادى مشاكل عرض/كتابة العربي (RTL) بخانة ضيقة.
        """
        self.active_entry = (elem, ent)
        self.edit_text.delete("1.0", "end")
        self.edit_text.insert("1.0", ent.get())

    def update_selected_line(self):
        """يرجّع النص المعدَّل من مربع التعديل الآمن لخانة الصف بالجدول (بدون حفظ نهائي للملف بعد)."""
        if self.active_entry is None:
            messagebox.showinfo(self.t("title_notice"), self.t("edit_selected_label"))
            return
        elem, ent = self.active_entry
        new_text = self.edit_text.get("1.0", "end-1c")
        ent.config(state="normal")
        ent.delete(0, "end")
        ent.insert(0, new_text)
        ent.config(state="readonly")

    def filter_rows(self):
        """يفلتر صفوف الجدول فورًا حسب النص المكتوب بشريط البحث (يبحث بالـID والنص الأصلي والمترجم)."""
        query = self.search_var.get().strip().lower()
        for row, str_id, orig_val, ent in self.row_widgets:
            if not query:
                row.pack(fill="x", expand=True, padx=4)
                continue
            trans_val = ent.get().lower() if ent else ""
            match = query in str_id.lower() or query in orig_val.lower() or query in trans_val
            if match:
                row.pack(fill="x", expand=True, padx=4)
            else:
                row.pack_forget()

    def _on_edit_text_enter(self, event):
        """Enter بمربع التعديل = تحديث السطر (بدل إدراج سطر جديد بالنص)."""
        self.update_selected_line()
        return "break"

    def _on_edit_text_control_key(self, event):
        """يدعم النسخ واللصق عند استخدام تخطيط لوحة المفاتيح العربية."""
        keycode_commands = {67: "<<Copy>>", 86: "<<Paste>>"}
        command = keycode_commands.get(event.keycode)
        if command:
            self.edit_text.event_generate(command)
            return "break"

    def retranslate_selected_line(self):
        """
        يرسل النص الأصلي للسطر المحدد حاليًا لمحرك الترجمة النشط (عبر
        retranslate_func الممرّرة من الواجهة الرئيسية) ويحط النتيجة بمربع
        التعديل. الترجمة تصير بخيط منفصل بالواجهة الرئيسية (عشان ما تجمّد
        النافذة)، وهذا الزر بس يعطّل نفسه مؤقتًا لحد ما توصل النتيجة.
        """
        if self.retranslate_func is None:
            return
        if self.active_entry is None:
            messagebox.showinfo(self.t("title_notice"), self.t("edit_selected_label"))
            return

        elem, ent = self.active_entry
        str_id = elem.get("id", "")
        orig_text = self.original_cache.get(str_id, "")
        if not orig_text:
            return

        self.retranslate_btn.config(state="disabled", text=self.t("edit_retranslating"))

        def on_done(result_text, error):
            self.retranslate_btn.config(state="normal", text=self.t("edit_retranslate_btn"))
            if error is not None:
                messagebox.showerror(self.t("title_error"), str(error))
                return
            self.edit_text.delete("1.0", "end")
            self.edit_text.insert("1.0", result_text)

        self.retranslate_func(orig_text, on_done)

    def save_current_file(self):
        if not self.current_tree or not self.current_path:
            return
        id_text_pairs = []
        for elem, ent in self.entries:
            str_id = elem.get("id", "")
            new_text = ent.get()
            elem.set("text", new_text)
            id_text_pairs.append((str_id, new_text))
            # إذا المستخدم صحح النص يدويًا وصارت الـPlaceholders كلها موجودة، نشيل التحذير
            if str_id in self.placeholder_issues:
                orig_val = self.original_cache.get(str_id, "")
                phs = re.findall(r"\{[^{}]+\}|<[^>]+>|\$[A-Za-z_][A-Za-z0-9_]*", orig_val)
                if all(ph in new_text for ph in phs):
                    self.placeholder_issues.discard(str_id)
            # تحديث حالة الـValidator (فاضي / غير مترجم) بعد التعديل اليدوي
            if new_text.strip():
                self.empty_ids.discard(str_id)
            orig_val_check = self.original_cache.get(str_id, "")
            if not (orig_val_check.strip() and new_text.strip() == orig_val_check.strip()):
                self.untranslated_ids.discard(str_id)
        self.current_tree.write(self.current_path, encoding="utf-8", xml_declaration=True)

        # نزامن ذاكرة الترجمة العامة وملف .diff_state.json الخاص بهذا المود
        # عشان أي تشغيل قادم (Smart Diff أو مود ثاني فيه نفس الجملة) ما يرجّع
        # الترجمة القديمة فوق التصحيح اليدوي اللي سويته الحين.
        if self.on_save_sync is not None:
            try:
                self.on_save_sync(id_text_pairs, self.current_path)
            except Exception:
                pass  # فشل المزامنة الثانوية ما لازم يمنع نجاح الحفظ الأساسي (الملف انحفظ فعلًا)

        self.refresh_issues_list()
        self.update_issue_counter()
        messagebox.showinfo(self.t("msg_saved_title"), self.t("msg_saved_body"))
        self.load_file()
