# -*- coding: utf-8 -*-
"""
core/translator_engine.py
محرك الترجمة الفعلي — لا يعرف شيء عن Tkinter أو أي واجهة رسومية أبدًا.
يتواصل مع أي واجهة تستخدمه فقط عبر 4 دوال استدعاء (Callbacks):

    on_progress(current, total, status_text)
        current/total: أرقام تقدّم الشريط، أو (None, None) لو التحديث نص حالة بس بدون تغيير الشريط.
    on_log(message, level="INFO")
        سطر جديد يُضاف لسجل العمليات.
    on_finish(report)
        انتهت عملية الترجمة. report فيه dict بالنتائج، أو {"canceled": True} لو انلغت.
    on_error(exception)
        صار خطأ قاتل قبل ما تبدأ الترجمة (مثلاً محرك الترجمة رفض المفتاح).

الواجهة (ui/main_window.py) هي المسؤولة عن تحويل هالإشارات لتحديثات فعلية
بالشاشة عبر root.after()، عشان يضل التحديث Thread-safe.
"""
import os
import re
import time
import json
import random
import xml.etree.ElementTree as ET

from ..data.glossary import DEFAULT_GLOSSARY
from ..core.paths import GLOSSARY_FILE, TM_FILE
from ..core.logger import write_log_line
from ..providers import registry as translator_registry

# اللغات "غير الرسمية" (اللي ما تدعمها اللعبة أصلًا وتحتاج ملف language_data.xml
# كامل بكل التفاصيل: supported_iso, subtitle_extension, text_processor...).
# أي لغة ثانية غير موجودة هنا تُعتبر "رسمية مدعومة من اللعبة" وتاخذ الهيكل المبسط.
# المطابقة تتم على tgt_conf["folder"] (الحروف الكبيرة، مثل "AR", "SP"...).
CUSTOM_LANGUAGES = ["AR"]

# المعرّفات الرسمية الأصلية (Native Language ID) اللي تتوقعها محركات Bannerlord
# لملف language_data.xml للغات الرسمية. المطابقة على tgt_conf["code"] (رمز اللغة
# الثابت زي "zh-CN") لا على tgt_conf["id"] النصي، لأن الصينية عندها قيمتا id
# مختلفتان شكليًا ("Chinese" / "TraditionalChinese") عن التسميات الشائعة
# ("Chinese (Simplified)" / "Chinese (Traditional)") - المطابقة بالـcode تضمن
# عدم فوات أي لغة بالغلط والرجوع للإنجليزي.
OFFICIAL_LANGUAGE_NATIVE_IDS = {
    "ru": "Русский",
    "tr": "Türkçe",
    "ja": "日本語",
    "fr": "Français",
    "de": "Deutsch",
    "es": "Español",
    "zh-CN": "简体中文",
    "zh-TW": "繁體中文",
    "ko": "한국어",
    "pt": "Português Brasileiro",
    "pl": "Polski",
    "it": "Italiano",
    "en": "English",
}


class TranslatorEngine:
    def __init__(self, t_func, on_progress=None, on_log=None, on_finish=None, on_error=None):
        self.t = t_func
        self.on_progress = on_progress or (lambda *a, **k: None)
        self.on_log = on_log or (lambda *a, **k: None)
        self.on_finish = on_finish or (lambda *a, **k: None)
        self.on_error = on_error or (lambda *a, **k: None)

        self.glossary_data = self.load_glossary()
        self.translation_memory = self.load_translation_memory()
        self.tm_hits = 0

        self.is_running = False
        self.cancel_requested = False
        self.created_files_session = []
        self.last_target_dir = None
        self.last_mod_name = "CustomMod"
        self.current_tgt_conf = None
        self.last_translated_files = []
        self.original_cache = {}
        self.newly_updated_ids = set()
        self.changed_ids = set()
        self.placeholder_issues = set()
        self.empty_ids = set()
        self.untranslated_ids = set()
        self.total_strings_found = 0  # إجمالي النصوص الفعلية المكتشفة بكل الجلسة (لكشف "النجاح الخادع")

        # إعدادات تضبطها الواجهة قبل كل عملية ترجمة عبر configure()
        self.delay = 0.0
        self.smart_cache_enabled = True
        self.apply_glossary_enabled = True

    def configure(self, delay=0.0, smart_cache_enabled=True, apply_glossary_enabled=True):
        self.delay = delay
        self.smart_cache_enabled = smart_cache_enabled
        self.apply_glossary_enabled = apply_glossary_enabled

    def get_translator(self, src_code, tgt_code, engine_index, api_key=None):
        return translator_registry.get_translator(engine_index, src_code, tgt_code, api_key=api_key)

    def fix_literal_newlines(self, xml_file_path):
        """
        يفحص الملف بعد كتابته: لو فيه رمز \\n حرفي (باكسلاش + n، مو سطر جديد
        فعلي) داخل أي نص مترجم، يحوّله بأمان لـ&#10; (الترميز الصحيح لسطر
        جديد داخل XML attribute تفهمه اللعبة). لازم يصير هذا بعد الكتابة
        مباشرة عبر تعديل نصي خام على الملف - لو سويناها قبل الكتابة عن طريق
        ET.set()، مكتبة XML بتـ"تهرّب" الـ& تلقائيًا وتطلع &amp;#10; مكسورة.
        لو الملف ما فيه \\n حرفي أصلًا، يُترك كما هو تمامًا بدون أي لمس.
        """
        try:
            with open(xml_file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            write_log_line("WARN", f"fix_literal_newlines failed to read {xml_file_path}: {e}")
            return

        if "\\n" not in content:
            return  # نظيف من الأصل - ما نلمسه

        fixed_content = content.replace("\\n", "&#10;")
        try:
            with open(xml_file_path, "w", encoding="utf-8") as f:
                f.write(fixed_content)
        except Exception as e:
            write_log_line("WARN", f"fix_literal_newlines failed to write {xml_file_path}: {e}")

    def validate_xml_file(self, xml_file_path):
        """يتأكد من أن ملف XML الناتج قابل للقراءة قبل استخدامه داخل اللعبة."""
        try:
            ET.parse(xml_file_path)
        except ET.ParseError as e:
            self.on_log(
                f"[!] الملف {os.path.basename(xml_file_path)} تالف برمجياً بسبب خطأ من محرك الترجمة ويجب مراجعته يدوياً: {e}",
                "ERROR",
            )

    def reset_glossary_to_default(self):
        """يُستخدم بميزة "ضبط المصنع" لإرجاع القاموس للنسخة الافتراضية وحفظها."""
        self.glossary_data = DEFAULT_GLOSSARY.copy()
        self.save_glossary()

    def clear_translation_memory(self):
        """يُستخدم بميزة "ضبط المصنع" لمسح ذاكرة الترجمة من الذاكرة (الملف ينحذف من الواجهة)."""
        self.translation_memory = {}

    def load_glossary(self):
        if os.path.exists(GLOSSARY_FILE):
            try:
                with open(GLOSSARY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                write_log_line("ERROR", f"Failed to read glossary.json (falling back to defaults): {e}")
        glossary = DEFAULT_GLOSSARY.copy()
        try:
            with open(GLOSSARY_FILE, "w", encoding="utf-8") as f:
                json.dump(glossary, f, ensure_ascii=False, indent=2)
        except Exception as e:
            write_log_line("WARN", f"Failed to write default glossary.json: {e}")
        return glossary
    def save_glossary(self):
        try:
            with open(GLOSSARY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.glossary_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            write_log_line("ERROR", f"Failed to save glossary.json: {e}")
    def load_translation_memory(self):
        """
        يقرأ ذاكرة الترجمة العامة (translation_memory.json) من مجلد المستندات.
        الشكل: { "ar": {"English text": "الترجمة", ...}, "es": {...}, ... }
        هذه الذاكرة مشتركة بين كل المودات، فأي نص تكرر بمود ثاني يترجم فورًا بدون API.
        """
        if os.path.exists(TM_FILE):
            try:
                with open(TM_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                write_log_line("ERROR", f"Failed to read translation_memory.json: {e}")
        return {}
    def save_translation_memory(self):
        try:
            with open(TM_FILE, "w", encoding="utf-8") as f:
                json.dump(self.translation_memory, f, ensure_ascii=False, indent=2)
        except Exception as e:
            write_log_line("ERROR", f"Failed to save translation_memory.json: {e}")
    def apply_glossary(self, text, tgt_code):
        if not self.apply_glossary_enabled or not text:
            return text
        rules = self.glossary_data.get(tgt_code.lower(), {})
        for en_term, target_term in rules.items():
            pattern = rf"\b{re.escape(en_term)}\b"
            text = re.sub(pattern, target_term, text, flags=re.IGNORECASE)
        return text
    def mask_placeholders(self, text):
        # يغطي: {PLAYER_NAME} {=ID} {GOLD} {?COND}..{\?} <tag> $VARIABLE
        placeholders = re.findall(r"\{[^{}]+\}|<[^>]+>|\$[A-Za-z_][A-Za-z0-9_]*", text)
        masked = text
        for i, ph in enumerate(placeholders):
            masked = masked.replace(ph, f" _X{i}X_ ")
        return masked, placeholders
    def validate_placeholders(self, placeholders, translated_text):
        """
        يتأكد أن كل الـPlaceholders الأصلية (زي {PLAYER_NAME} أو {GOLD}) موجودة
        بنفس الشكل بالنص المترجم النهائي. يرجع (ok, قائمة_المفقود).
        """
        if not translated_text:
            return (not placeholders, list(placeholders))
        missing = [ph for ph in placeholders if ph not in translated_text]
        return (len(missing) == 0, missing)
    def unmask_and_repair(self, text, placeholders):
        if not text:
            return text
        repaired = text
        for i, ph in enumerate(placeholders):
            repaired = re.sub(rf"_\s*X\s*{i}\s*X\s*_", ph, repaired, flags=re.IGNORECASE)
            repaired = re.sub(rf"__*\s*VAR\s*{i}\s*__*", ph, repaired, flags=re.IGNORECASE)
        repaired = re.sub(r"\{([a-zA-Z0-9_\-]+)\}_", r"{\1}", repaired)
        return repaired
    def translate_single_text(self, text, translator, tgt_code):
        """
        يترجم نص واحد ويحمي الـPlaceholders، ثم يتحقق أنها كلها رجعت سليمة.
        قبل اللجوء للـAPI، يفحص ذاكرة الترجمة (Translation Memory) المشتركة
        بين كل المودات - لو نفس النص تُرجم سابقًا لنفس اللغة، يستخدمه فورًا.
        يرجع tuple: (النص_المترجم, ph_ok, قائمة_placeholders_المفقودة)
        """
        if not text or not text.strip():
            return text, True, []

        # 1) فحص ذاكرة الترجمة أول شيء (بدون أي طلب API)
        if self.smart_cache_enabled:
            tm_cached = self.translation_memory.get(tgt_code, {}).get(text)
            if tm_cached:
                ok, missing = self.validate_placeholders(self.mask_placeholders(text)[1], tm_cached)
                if ok:
                    self.tm_hits += 1
                    return tm_cached, True, []

        masked, phs = self.mask_placeholders(text)

        base_delay = self.delay
        retry_waits = [1, 2, 5, 10]  # Exponential Backoff
        max_attempts = len(retry_waits)
        last_reason = ""
        last_result = None  # (final_text, ok, missing) آخر نتيجة ناجحة بالاتصال حتى لو فيها Placeholder ناقص

        for attempt in range(max_attempts):
            try:
                if base_delay > 0:
                    time.sleep(base_delay)
                res = translator.translate(masked, target_lang=tgt_code)
                if res and "Error 500" not in res:
                    unmasked = self.unmask_and_repair(res, phs)
                    final_text = self.apply_glossary(unmasked, tgt_code)
                    ok, missing = self.validate_placeholders(phs, final_text)
                    last_result = (final_text, ok, missing)
                    if ok:
                        # نخزن بالذاكرة العامة فقط لو الترجمة سليمة (Placeholders موجودة)
                        self.translation_memory.setdefault(tgt_code, {})[text] = final_text
                        return final_text, True, []
                    last_reason = f"Placeholder(s) missing: {', '.join(missing)}"
                else:
                    last_reason = "Engine returned empty result / Error 500"
            except Exception as e:
                last_reason = str(e)

            if attempt < max_attempts - 1:
                wait_s = retry_waits[attempt] + random.uniform(0, retry_waits[attempt] * 0.3)
                self.on_log(self.t("log_retry").format(attempt=attempt + 1, max=max_attempts, reason=last_reason, wait=f"{wait_s:.1f}"))
                time.sleep(wait_s)

        if last_result is not None:
            # فيه ترجمة رجعت من المحرك لكن فيها مشكلة Placeholder حتى بعد كل المحاولات
            self.on_log(self.t("log_ph_persist").format(max=max_attempts, reason=last_reason))
            return last_result

        self.on_log(self.t("log_translate_failed").format(max=max_attempts, reason=last_reason))
        ok, missing = self.validate_placeholders(phs, text)
        return text, ok, missing
    def diff_state_path(self, out_target_dir):
        return os.path.join(out_target_dir, ".diff_state.json")
    def load_diff_state(self, out_target_dir):
        """
        يقرأ ملف حالة المقارنة الذكية (id -> {src, text}) المحفوظ من آخر تشغيل.
        إذا الملف غير موجود (أول تشغيل بعد التحديث)، يرجع dict فاضي
        ويعتبر أن كل شيء غير معروف السطر السابق (سيُعامل كل ID موجود
        بترجمة قديمة على أنه KEPT لمرة واحدة فقط، وابتداءً من هذا التشغيل
        سيبدأ حفظ النص الأصلي للمقارنة الصحيحة في المرات القادمة).
        """
        state_path = self.diff_state_path(out_target_dir)
        if os.path.exists(state_path):
            try:
                with open(state_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                write_log_line("WARN", f"Failed to read diff_state at {state_path}: {e}")
        return {}
    def save_diff_state(self, out_target_dir, state):
        state_path = self.diff_state_path(out_target_dir)
        try:
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            write_log_line("ERROR", f"Failed to save diff_state at {state_path}: {e}")
    def check_mod_translatable(self, mod_path):
        target_lang = mod_path
        if not os.path.basename(mod_path).lower() == "languages":
            for root, dirs, _ in os.walk(mod_path):
                for d in dirs:
                    if d.lower() == "languages":
                        target_lang = os.path.join(root, d)
                        break

        if os.path.exists(target_lang):
            for root, _, files in os.walk(target_lang):
                for f in files:
                    if f.endswith(".xml") and not f.startswith("language_data"):
                        return True, "XML Files"

        pattern = rb"\{=([a-zA-Z0-9_\-]+)\}(.*?)(?=\x00|\"|\\n|\r|\n|$)"
        for root, _, files in os.walk(mod_path):
            for f in files:
                if f.lower().endswith(".dll"):
                    try:
                        with open(os.path.join(root, f), "rb") as fl:
                            if re.search(pattern, fl.read()):
                                return True, "DLL Keys"
                    except Exception:
                        pass
        return False, "Unsupported"
    def extract_keys_from_dlls(self, base_folder):
        extracted = {}
        pattern = rb"\{=([a-zA-Z0-9_\-]+)\}(.*?)(?=\x00|\"|\\n|\r|\n|$)"
        for root, _, files in os.walk(base_folder):
            for file in files:
                if file.lower().endswith(".dll"):
                    try:
                        with open(os.path.join(root, file), "rb") as f:
                            for key_b, val_b in re.findall(pattern, f.read()):
                                k = key_b.decode("utf-8", errors="ignore").strip()
                                v = val_b.decode("utf-8", errors="ignore").strip()
                                if k and v and k not in extracted:
                                    extracted[k] = v
                    except Exception as e:
                        write_log_line("WARN", f"Failed to scan DLL {file}: {e}")
        return extracted
    def translate_single_mod(self, mod_path, translator, tgt_conf):
        mod_name = os.path.basename(mod_path.rstrip(r"\/"))
        self.last_mod_name = mod_name
        self.on_log(self.t("log_processing").format(mod=mod_name))

        target_lang_dir = mod_path
        if not os.path.basename(mod_path).lower() == "languages":
            for root, dirs, _ in os.walk(mod_path):
                for d in dirs:
                    if d.lower() == "languages":
                        target_lang_dir = os.path.join(root, d)
                        break

        self.last_target_dir = target_lang_dir
        out_subfolder = tgt_conf["folder"]
        out_target_dir = os.path.join(target_lang_dir, out_subfolder)

        xml_files = []
        if os.path.exists(target_lang_dir):
            # الخطوة 1: البحث مباشرة بجذر مجلد اللغات (Languages/) - لو فيه ملفات XML هناك، تُعتمد فورًا
            for file in os.listdir(target_lang_dir):
                fpath = os.path.join(target_lang_dir, file)
                if os.path.isfile(fpath) and file.endswith(".xml") and not file.lower().startswith("language_data"):
                    xml_files.append((fpath, file))

            # الخطوة 2: ما فيه شي بالجذر -> ندور جوه المجلدات الفرعية (EN, SP, ...)
            # ونختار المجلد "الأغنى" (أكثر عدد ملفات XML)، مع استثناء مجلد
            # الإخراج الخاص باللغة الهدف نفسها (عشان ما نلخبط نتيجة قديمة بمصدر).
            if not xml_files:
                best_folder = None
                best_files = []
                out_subfolder_norm = os.path.normpath(out_target_dir)

                for item in os.listdir(target_lang_dir):
                    ipath = os.path.join(target_lang_dir, item)
                    if not os.path.isdir(ipath):
                        continue
                    if os.path.normpath(ipath) == out_subfolder_norm:
                        continue  # نتجاهل مجلد نتيجة اللغة الهدف نفسها

                    candidate_files = [
                        f for f in os.listdir(ipath)
                        if os.path.isfile(os.path.join(ipath, f)) and f.endswith(".xml") and not f.lower().startswith("language_data")
                    ]
                    if len(candidate_files) > len(best_files):
                        best_folder = ipath
                        best_files = candidate_files

                if best_folder:
                    for f in best_files:
                        xml_files.append((os.path.join(best_folder, f), f))

        if xml_files:
            # فحص مسبق: نتأكد إن فيه عناصر <string> فعلية قبل ما ننشئ أي ملف أو مجلد.
            # هذا يمنع "النجاح الخادع" لو الملفات المكتشفة XML عادية (خرائط، بيانات)
            # مو ملفات نصوص ترجمة أصلًا.
            probe_count = 0
            for full_path, file_name in xml_files:
                try:
                    probe_tree = ET.parse(full_path)
                    probe_count += len(list(probe_tree.getroot().iter("string")))
                except Exception:
                    pass

            if probe_count == 0:
                self.on_log(self.t("log_skip_mod").format(mod=mod_name))
                return

            self.total_strings_found += probe_count

            os.makedirs(out_target_dir, exist_ok=True)
            self.created_files_session.append(out_target_dir)
            created_files = []

            for full_path, file_name in xml_files:
                if self.cancel_requested:
                    return

                out_file_path = os.path.join(out_target_dir, file_name)

                # حالة الـSmart Diff: id -> {"src": النص الأصلي وقت آخر ترجمة, "text": الترجمة}
                diff_state = {}
                # توافق مع نسخ سابقة: لو موجود ملف مترجم قديم بدون diff_state (أول تشغيل بعد التحديث)
                legacy_translations = {}

                if self.smart_cache_enabled:
                    diff_state = self.load_diff_state(out_target_dir).get(file_name, {})
                    if not diff_state and os.path.exists(out_file_path):
                        try:
                            ex_tree = ET.parse(out_file_path)
                            for s in ex_tree.getroot().iter("string"):
                                val = s.get("text", "")
                                if val and "Error 500" not in val:
                                    legacy_translations[s.get("id")] = val
                        except Exception as e:
                            write_log_line("WARN", f"Failed to read legacy translation {out_file_path}: {e}")

                try:
                    tree = ET.parse(full_path)
                    root = tree.getroot()

                    tags = root.find("tags")
                    if tags is not None:
                        tag = tags.find("tag")
                        if tag is not None:
                            tag.set("language", tgt_conf["xml_name"])

                    string_nodes = list(root.iter("string"))
                    self.on_progress(0, len(string_nodes), "")

                    cached_count = 0
                    newly_translated_count = 0
                    changed_count = 0
                    new_file_state = {}

                    for i, node in enumerate(string_nodes, 1):
                        if self.cancel_requested:
                            return
                        str_id = node.get("id")
                        orig_text = node.get("text", "")
                        self.original_cache[str_id] = orig_text

                        prev = diff_state.get(str_id)
                        legacy_val = legacy_translations.get(str_id) if not diff_state else None

                        if prev and prev.get("text") and prev.get("src") == orig_text:
                            # نفس الـID ونفس النص الأصلي بالضبط -> نحتفظ بالترجمة القديمة
                            node.set("text", prev["text"])
                            new_file_state[str_id] = prev
                            cached_count += 1
                            if not prev.get("ph_ok", True):
                                self.placeholder_issues.add(str_id)
                        elif legacy_val:
                            # توافق مع نسخة قديمة من الأداة (بدون diff_state):
                            # نحتفظ بالترجمة السابقة لأننا لا نعرف نصها الأصلي وقتها
                            node.set("text", legacy_val)
                            ph_ok_legacy, missing_legacy = self.validate_placeholders(self.mask_placeholders(orig_text)[1], legacy_val)
                            new_file_state[str_id] = {"src": orig_text, "text": legacy_val, "ph_ok": ph_ok_legacy}
                            cached_count += 1
                            if not ph_ok_legacy:
                                self.placeholder_issues.add(str_id)
                        else:
                            if self.cancel_requested:
                                return
                            trans_res, ph_ok, missing_ph = self.translate_single_text(orig_text, translator, tgt_conf["code"])
                            node.set("text", trans_res)
                            new_file_state[str_id] = {"src": orig_text, "text": trans_res, "ph_ok": ph_ok}
                            newly_translated_count += 1
                            if not ph_ok:
                                self.placeholder_issues.add(str_id)
                                self.on_log(self.t("log_ph_missing").format(id=str_id, list=', '.join(missing_ph)))
                            if str_id in diff_state:
                                # الـID كان موجود من قبل لكن النص الأصلي تغيّر
                                self.changed_ids.add(str_id)
                                changed_count += 1
                            else:
                                self.newly_updated_ids.add(str_id)

                        status_str = self.t("status_progress").format(mod=mod_name, file=file_name, i=i, total=len(string_nodes), new=newly_translated_count - changed_count, changed=changed_count)
                        self.on_progress(i, len(string_nodes), status_str)

                    tree.write(out_file_path, encoding="utf-8", xml_declaration=True)
                    self.fix_literal_newlines(out_file_path)
                    self.validate_xml_file(out_file_path)
                    self.created_files_session.append(out_file_path)
                    self.last_translated_files.append(out_file_path)
                    created_files.append(file_name)

                    if self.smart_cache_enabled:
                        full_state = self.load_diff_state(out_target_dir)
                        full_state[file_name] = new_file_state
                        self.save_diff_state(out_target_dir, full_state)

                    file_ph_issues = sum(1 for sid in new_file_state if sid in self.placeholder_issues)
                    ph_suffix = self.t("log_ph_suffix").format(n=file_ph_issues) if file_ph_issues else ""
                    self.on_log(self.t("log_file_done").format(file=file_name, total=len(string_nodes), kept=cached_count, changed=changed_count, new=newly_translated_count - changed_count) + ph_suffix)

                except Exception as e:
                    self.on_log(self.t("log_file_error").format(file=file_name, error=e))

            self.on_progress(None, None, self.t("status_gen"))
            self.generate_lang_data(out_target_dir, created_files, tgt_conf)
            self.save_translation_memory()

        else:
            extracted = self.extract_keys_from_dlls(mod_path)
            if not extracted:
                self.on_log(self.t("log_skip_mod").format(mod=mod_name))
                return

            self.total_strings_found += len(extracted)

            mod_data_dir = os.path.join(mod_path, "ModuleData") if os.path.exists(os.path.join(mod_path, "ModuleData")) else mod_path
            target_lang_dir = os.path.join(mod_data_dir, "Languages")
            out_target_dir = os.path.join(target_lang_dir, out_subfolder)
            os.makedirs(out_target_dir, exist_ok=True)
            self.created_files_session.append(out_target_dir)

            out_xml = os.path.join(out_target_dir, "std_module_strings_xml.xml")

            diff_state = {}
            legacy_translations = {}
            if self.smart_cache_enabled:
                diff_state = self.load_diff_state(out_target_dir).get("std_module_strings_xml.xml", {})
                if not diff_state and os.path.exists(out_xml):
                    try:
                        ex_tree = ET.parse(out_xml)
                        for s in ex_tree.getroot().iter("string"):
                            val = s.get("text", "")
                            if val and "Error 500" not in val:
                                legacy_translations[s.get("id")] = val
                    except Exception as e:
                        write_log_line("WARN", f"Failed to read legacy DLL translation {out_xml}: {e}")

            base_elem = ET.Element("base", {"type": "string"})
            tags_elem = ET.SubElement(base_elem, "tags")
            ET.SubElement(tags_elem, "tag", {"language": tgt_conf["xml_name"]})
            strings_elem = ET.SubElement(base_elem, "strings")

            dll_items = list(extracted.items())
            self.on_progress(0, len(dll_items), "")

            cached_count = 0
            newly_translated_count = 0
            changed_count = 0
            new_file_state = {}

            for idx, (str_id, orig_text) in enumerate(dll_items, 1):
                if self.cancel_requested:
                    return
                self.original_cache[str_id] = orig_text

                prev = diff_state.get(str_id)
                legacy_val = legacy_translations.get(str_id) if not diff_state else None

                if prev and prev.get("text") and prev.get("src") == orig_text:
                    ET.SubElement(strings_elem, "string", {"id": str_id, "text": prev["text"]})
                    new_file_state[str_id] = prev
                    cached_count += 1
                    if not prev.get("ph_ok", True):
                        self.placeholder_issues.add(str_id)
                elif legacy_val:
                    ET.SubElement(strings_elem, "string", {"id": str_id, "text": legacy_val})
                    ph_ok_legacy, _ = self.validate_placeholders(self.mask_placeholders(orig_text)[1], legacy_val)
                    new_file_state[str_id] = {"src": orig_text, "text": legacy_val, "ph_ok": ph_ok_legacy}
                    cached_count += 1
                    if not ph_ok_legacy:
                        self.placeholder_issues.add(str_id)
                else:
                    if self.cancel_requested:
                        return
                    trans_text, ph_ok, missing_ph = self.translate_single_text(orig_text, translator, tgt_conf["code"])
                    ET.SubElement(strings_elem, "string", {"id": str_id, "text": trans_text})
                    new_file_state[str_id] = {"src": orig_text, "text": trans_text, "ph_ok": ph_ok}
                    newly_translated_count += 1
                    if not ph_ok:
                        self.placeholder_issues.add(str_id)
                        self.on_log(self.t("log_ph_missing").format(id=str_id, list=', '.join(missing_ph)))
                    if str_id in diff_state:
                        self.changed_ids.add(str_id)
                        changed_count += 1
                    else:
                        self.newly_updated_ids.add(str_id)

                status_str = self.t("status_progress_dll").format(mod=mod_name, i=idx, total=len(dll_items), new=newly_translated_count - changed_count, changed=changed_count)
                self.on_progress(idx, len(dll_items), status_str)

            tree = ET.ElementTree(base_elem)
            ET.indent(tree, space="  ", level=0)
            tree.write(out_xml, encoding="utf-8", xml_declaration=True)
            self.fix_literal_newlines(out_xml)
            self.validate_xml_file(out_xml)
            self.created_files_session.append(out_xml)
            self.last_translated_files.append(out_xml)

            if self.smart_cache_enabled:
                full_state = self.load_diff_state(out_target_dir)
                full_state["std_module_strings_xml.xml"] = new_file_state
                self.save_diff_state(out_target_dir, full_state)

            dll_ph_issues = sum(1 for sid in new_file_state if sid in self.placeholder_issues)
            ph_suffix_dll = self.t("log_ph_suffix").format(n=dll_ph_issues) if dll_ph_issues else ""
            self.on_log(self.t("log_dll_done").format(total=len(dll_items), kept=cached_count, changed=changed_count, new=newly_translated_count - changed_count) + ph_suffix_dll)
            
            self.on_progress(None, None, self.t("status_gen"))
            self.generate_lang_data(out_target_dir, ["std_module_strings_xml.xml"], tgt_conf)
            self.save_translation_memory()
    def generate_lang_data(self, target_folder, files, tgt_conf):
        is_custom = tgt_conf["folder"].upper() in CUSTOM_LANGUAGES

        if is_custom:
            # لغة غير رسمية (زي العربية) -> هيكل كامل يحتاجه محرك اللعبة عشان يتعرف عليها
            attrs = {
                "id": tgt_conf["id"],
                "name": tgt_conf["xml_name"],
                "subtitle_extension": tgt_conf["sub_ext"],
                "supported_iso": tgt_conf["iso"],
                "under_development": "false",
            }
            if tgt_conf["processor"]:
                attrs["text_processor"] = tgt_conf["processor"]
        else:
            # لغة رسمية مدعومة أصلًا من اللعبة -> هيكل مبسّط: id بس، لكن بالمعرّف
            # الأصلي (Native ID) اللي تتعرف عليه اللعبة، مو بالاسم الإنجليزي
            native_id = OFFICIAL_LANGUAGE_NATIVE_IDS.get(tgt_conf["code"], tgt_conf["id"])
            attrs = {"id": native_id}

        root_data = ET.Element("LanguageData", attrs)
        for f in files:
            ET.SubElement(root_data, "LanguageFile", {"xml_path": f"{tgt_conf['folder']}/{f}"})

        tree = ET.ElementTree(root_data)
        ET.indent(tree, space="  ", level=0)

        out_file = os.path.join(target_folder, "language_data.xml")
        tree.write(out_file, encoding="utf-8", xml_declaration=True)
        self.validate_xml_file(out_file)
        self.created_files_session.append(out_file)
        self.on_log(self.t("log_langdata_created").format(folder=tgt_conf['folder']))
    def run_validator(self):
        """
        فحص جودة نهائي بعد اكتمال كل الترجمة (كل المودات وكل اللغات بهالجلسة).
        يفحص كل الملفات اللي انترجمت (self.last_translated_files) ويدور على:
          1) نصوص فاضية (text="")
          2) نصوص طلعت مطابقة تمامًا للنص الإنجليزي الأصلي (احتمال كبير إنها ما تُرجمت)
        نتائج الـPlaceholders موجودة أصلًا بـ self.placeholder_issues من وقت الترجمة نفسها.
        يرجع dict فيه ملخص الأرقام، ويحدّث self.empty_ids و self.untranslated_ids
        عشان يقدر المحرر التفاعلي يعرضها كشارات.
        """
        self.empty_ids = set()
        self.untranslated_ids = set()
        total = 0
        tgt_code = self.current_tgt_conf.get("code") if self.current_tgt_conf else ""
        is_target_english = tgt_code == "en"

        checked_paths = set()
        for path in self.last_translated_files:
            if path in checked_paths or not os.path.exists(path):
                continue
            checked_paths.add(path)
            try:
                tree = ET.parse(path)
                for node in tree.getroot().iter("string"):
                    str_id = node.get("id", "")
                    text_val = node.get("text", "")
                    total += 1
                    if not text_val or not text_val.strip():
                        self.empty_ids.add(str_id)
                        continue
                    if not is_target_english:
                        orig_val = self.original_cache.get(str_id, "")
                        if orig_val.strip() and text_val.strip() == orig_val.strip():
                            self.untranslated_ids.add(str_id)
            except Exception as e:
                write_log_line("WARN", f"Validator failed to read {path}: {e}")

        return {
            "total": total,
            "empty": len(self.empty_ids),
            "untranslated": len(self.untranslated_ids),
            "placeholder_issues": len(self.placeholder_issues),
        }

    def rollback_files(self):
        """
        يحذف كل الملفات/المجلدات اللي انسوت هالجلسة (created_files_session)
        بترتيب عكسي (الأحدث أول). يرجع (نجح_بالكامل: bool, عدد_الفشل: int).
        """
        failed = []
        for p in reversed(self.created_files_session):
            try:
                if os.path.isfile(p):
                    os.remove(p)
                elif os.path.isdir(p) and not os.listdir(p):
                    os.rmdir(p)
            except Exception as e:
                write_log_line("ERROR", f"Rollback failed to remove {p}: {e}")
                failed.append(p)
        return (len(failed) == 0, len(failed))

    def run_batch(self, mods, src_code, tgt_conf, engine_index, api_key=None):
        """
        نقطة الدخول الرئيسية: يترجم قائمة مودات كاملة. مصمم يشتغل بخيط منفصل
        (threading.Thread) من طرف الواجهة، وكل تواصل معها يمر بالـCallbacks.
        """
        self.is_running = True
        self.cancel_requested = False
        self.created_files_session = []
        self.last_translated_files = []
        self.original_cache = {}
        self.newly_updated_ids = set()
        self.changed_ids = set()
        self.placeholder_issues = set()
        self.empty_ids = set()
        self.untranslated_ids = set()
        self.tm_hits = 0
        self.total_strings_found = 0
        self.current_tgt_conf = tgt_conf

        try:
            translator = self.get_translator(src_code, tgt_conf["code"], engine_index, api_key=api_key)
        except Exception as e:
            self.on_log(self.t("log_engine_error").format(error=e))
            self.is_running = False
            self.on_error(e)
            return

        for mod_folder in mods:
            if self.cancel_requested:
                break
            self.translate_single_mod(mod_folder, translator, tgt_conf)

        self.is_running = False

        if self.cancel_requested:
            self.on_finish({"canceled": True})
            return

        if self.total_strings_found == 0:
            # "النجاح الخادع": ما لقينا أي نص فعلي قابل للترجمة بكل المودات المختارة.
            # نوقف هنا بدون توليد تقرير Validator ولا رسالة نجاح.
            self.on_finish({"canceled": False, "zero_strings": True})
            return

        if self.tm_hits:
            self.on_log(self.t("log_tm_summary").format(n=self.tm_hits))

        report = self.run_validator()
        self.on_log(self.t("log_validator_title"))
        self.on_log(self.t("log_validator_total").format(n=report["total"]))
        if report["empty"]:
            self.on_log(self.t("log_validator_empty").format(n=report["empty"]))
        if report["untranslated"]:
            self.on_log(self.t("log_validator_untranslated").format(n=report["untranslated"]))
        if report["placeholder_issues"]:
            self.on_log(self.t("log_validator_ph").format(n=report["placeholder_issues"]))
        if not (report["empty"] or report["untranslated"] or report["placeholder_issues"]):
            self.on_log(self.t("log_validator_clean"))
        self.on_log("\n[✔] " + self.t("status_done"))
        report["canceled"] = False
        self.on_finish(report)
