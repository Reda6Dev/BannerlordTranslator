# خريطة هيكلية — BannerlordTranslator (Project Architecture Map)

**الاستخدام:** هذا الملف مرجع دقيق لهيكلة المشروع، مُعدّ للصق مباشرة كسياق (Context) عند توجيه أوامر لأي أداة ذكاء اصطناعي أخرى تعمل على هذا المشروع.

---

## 1. شجرة المشروع (File Tree)

    BannerlordTranslator/
    │
    ├── .gitignore                   # ملف استثناء الملفات الثقيلة من الرفع لـ GitHub (مثل venv و dist)
    ├── icon.ico                     # الأيقونة الرسمية للتطبيق (تُدمج مع ملف exe)
    ├── main.py                      # نقطة الانطلاق الوحيدة (18 سطر)
    ├── main.spec                    # ملف إعدادات بناء التطبيق (تلقائي من PyInstaller)
    │
    ├── dist/                        # يحتوي على التطبيق النهائي (Bannerlord Translator.exe)
    ├── build/                       # مجلدات البناء المؤقتة (يُحذف تلقائياً للتنظيف)
    ├── venv/                        # البيئة الافتراضية المعزولة (مستثناة من GitHub)
    │
    └── BannerlordTranslator_pkg/
        │
        ├── data/                    # بيانات ثابتة فقط - بدون أي منطق تنفيذي
        │   ├── languages.py         # OFFICIAL_LANGUAGES (14 لغة ترجمة)
        │   ├── ui_texts.py          # UI_TEXTS (13 لغة واجهة + تعبئة تلقائية = 14، 155 مفتاح/لغة)
        │   └── glossary.py          # DEFAULT_GLOSSARY (القاموس الافتراضي)
        │
        ├── core/                    # البنية التحتية ومنطق الترجمة الفعلي
        │   ├── paths.py             # مسارات التخزين (APP_DIR, CONFIG_FILE, GLOSSARY_FILE, TM_FILE)
        │   ├── logger.py            # سجل أخطاء يومي (write_log_line)
        │   └── translator_engine.py # ★★ TranslatorEngine - قلب النظام (767 سطر)
        │
        ├── providers/               # طبقة تجريد محركات الترجمة (Strategy Pattern)
        │   ├── base.py              # TranslationProvider (الواجهة المشتركة)
        │   ├── google.py / deepl.py / microsoft.py / mymemory.py / linguee.py
        │   └── registry.py          # ★ نقطة الاختيار الموحّدة (get_translator)
        │
        └── ui/                      # كل ما يتعلق بـTkinter - بدون أي منطق ترجمة فعلي
            ├── widgets.py           # ToolTip (عنصر مشترك)
            ├── main_window.py       # ★★ BannerlordTranslatorV12 - النافذة الرئيسية (633 سطر)
            ├── editor.py            # InteractiveEditorDialog - المحرر التفاعلي (474 سطر)
            ├── glossary_window.py   # GlossaryManagerDialog
            ├── export_dialog.py     # ExportDialog
            ├── batch_dialog.py      # BatchSelectionDialog
            ├── reset_dialog.py      # FactoryResetDialog
            └── help_dialog.py       # HelpNotebookDialog (5 تبويبات)

*(★★ = أهم ملفين بالمشروع، ★ = نقطة دخول مهمة. كل مجلد فيه `__init__.py` فارغ لتعريفه كحزمة.)*

---

## 2. دليل الوظائف (File Roles)

### طبقة `data/` — بيانات بحتة
* **`languages.py`**: قائمة اللغات الممكن الترجمة إليها (14 لغة) بكل تفاصيلها (كود، مجلد الإخراج، معالج النصوص).
* **`ui_texts.py`**: كل نص تعرضه الواجهة (أزرار، رسائل، أخطاء، دليل المساعدة) بـ13 لغة، بمفتاح واحد لكل نص.
* **`glossary.py`**: القاموس الافتراضي لمصطلحات Bannerlord (يُستخدم أول تشغيل و"ضبط المصنع").

### طبقة `core/` — المنطق والبنية التحتية
* **`paths.py`**: يحدد أين يُخزَّن كل شيء على القرص (`Documents/BannerlordTranslator/`).
* **`logger.py`**: يكتب سجل أخطاء يومي بملف نصي (`logs/`)، Best-effort لا يوقف البرنامج أبدًا.
* **`translator_engine.py`**: **يرسل طلبات الترجمة، يقارن النصوص (Smart Diff)، يحمي الـPlaceholders، يدير ذاكرة الترجمة، يكتب ملفات XML الناتجة.** لا يعرف شيئًا عن Tkinter إطلاقًا - يتواصل عبر Callbacks فقط.

### طبقة `providers/` — محركات الترجمة
* **`base.py`**: الشكل الموحّد (`translate(text)`) الذي يلتزم فيه أي محرك.
* **`google.py`, `deepl.py`, `microsoft.py` وغيرها**: غلاف رفيع حول كل محرك ترجمة فعلي.
* **`registry.py`**: نقطة الدخول الوحيدة لاختيار محرك حسب رقمه (`get_translator(engine_index, ...)`).

### طبقة `ui/` — الواجهة الرسومية
* **`main_window.py`**: **يدير الواجهة الرئيسية بالكامل.** يبني كل العناصر، ينشئ `TranslatorEngine` مرة واحدة، ويربط إشاراته بتحديثات فعلية على الشاشة. **هنا تُقرأ إعدادات المستخدم وتُمرَّر للمحرك.**
* **`editor.py`**: مراجعة/تعديل النصوص المترجمة يدويًا. فيه مربع تعديل آمن (RTL)، بحث فوري، إعادة ترجمة سطر واحد، وإعادة فحص أخطاء حي.
* **`glossary_window.py`**: إضافة/تعديل/حذف مصطلحات القاموس.
* **`export_dialog.py`**: تصدير الترجمة (فتح مباشر / مجلد نظيف / مود مستقل / ZIP).
* **`batch_dialog.py`**: اختيار عدة مودات للترجمة دفعة واحدة.
* **`reset_dialog.py`**: تأكيد حذف الإعدادات/القاموس ("ضبط المصنع").
* **`help_dialog.py`**: دليل الاستخدام (5 تبويبات، آخرها محتوى ديناميكي حسب لغة الواجهة).
* **`widgets.py`**: `ToolTip` - تلميح عائم مشترك تستخدمه كل النوافذ.

### أين تُحفظ بيانات المستخدم؟ (مجلد `Documents/BannerlordTranslator/`)
* **`config.json`**: لغة الواجهة المفضّلة، المحرك المفضل، والفاصل الزمني.
* **`glossary.json`**: القاموس المخصّص (يبدأ من `DEFAULT_GLOSSARY` ويتعدّل من `glossary_window.py`).
* **`translation_memory.json`**: كل جملة تُرجمت سابقًا (مشتركة بين كل المودات) - `{لغة: {نص_إنجليزي: ترجمة}}`.
* **`.diff_state.json`**: يخزّن id + النص الأصلي وقته + الترجمة، لآلية Smart Diff (KEPT/CHANGED/NEW).
* **`logs/YYYY-MM-DD_Translator.log`**: سجل الأخطاء اليومي.

---

## 3. دورة العمل (Workflow)

### أ) من فتح البرنامج حتى ظهور الواجهة
1. `main.py` ينشئ نافذة Tkinter جذرية ويمرّرها لـ`BannerlordTranslatorV12`.
2. `__init__` يحدد لغة الواجهة، ثم ينشئ `TranslatorEngine` (يحمّل القاموس وذاكرة الترجمة من القرص فورًا).
3. `build_gui()` يبني كل عناصر الشاشة ويثبّت الألوان (وضع نهاري ثابت فقط).

### ب) من ضغطة "ابدأ" حتى ظهور النص المترجم
1. **الواجهة تقرأ اختيارات المستخدم:** مجلد المود، اللغة المصدر/الهدف، محرك الترجمة، الفاصل الزمني، تفعيل المقارنة الذكية والقاموس.
2. `execute_batch()` يضبط `engine.configure(...)` ويشغّل `engine.run_batch(...)` **بخيط منفصل** (لعدم تجميد الواجهة).
3. **(بالخيط المنفصل)** `run_batch` يبني محرك الترجمة المطلوب عبر `providers/registry.get_translator(...)`، ثم لكل مود:
   * `translate_single_mod()` يكتشف ملفات النصوص تلقائيًا.
   * يفحص عدد النصوص الفعلي مسبقًا - لو صفر، يوقف بدون توليد أي ملف.
   * لكل جملة: `translate_single_text()` يفحص ذاكرة الترجمة أولًا → يحمي الـPlaceholders → يرسل للـAPI → يطبّق القاموس → يتحقق من سلامة الـPlaceholders.
   * يقارن كل جملة بالنسخة القديمة (Smart Diff عبر `.diff_state.json`) لتصنيفها.
   * يكتب ملف XML المترجم + `language_data.xml`.
4. كل تحديث يُرسل كإشارة تستقبلها الواجهة عبر `root.after()` وتحدّث الشاشة بأمان.
5. الواجهة تعرض رسالة النجاح، وتُفعّل زري "تصدير" و"تحرير".

### ج) الإلغاء والتراجع الآمن (Rollback)
1. في حالة الضغط على "إلغاء"، يقوم البرنامج بإنهاء ترجمة السطر الحالي فقط (لمنع تلف ملفات XML).
2. يُخيّر المستخدم بين الاحتفاظ بما تم إنجازه أو إجراء تراجع آمن (Rollback) يمسح كافة الملفات المؤقتة ويعيد مجلد المود نظيفاً كما كان.

### د) التصدير (Export)
1. زر "تصدير" يفتح `ExportDialog` بأربع خيارات، مع تجاهل `.diff_state.json` دائمًا من أي تصدير.

---

## 4. ملاحظات مرجعية سريعة
* **القاعدة الذهبية:** `core/translator_engine.py` لا يستورد `tkinter` أبدًا. أي كود يلمس واجهة يجب أن يكون بمجلد `ui/`.
* **التواصل بين الطبقتين:** يمر دائمًا عبر Callbacks أو عبر قراءة `self.engine.xxx` من الواجهة مباشرة - أبدًا العكس.
* **إضافة محرك ترجمة جديد؟** إنشاء ملف جديد بـ`providers/` + إضافة شرط بـ`registry.py` فقط.
* **إضافة لغة واجهة جديدة؟** ملف `data/ui_texts.py` فقط.
* **أوامر بناء التطبيق:** يتم البناء في بيئة افتراضية نظيفة (`venv`) باستخدام الأمر: 
  `pyinstaller --clean --noconsole --onefile --icon="icon.ico" --add-data "BannerlordTranslator_pkg;BannerlordTranslator_pkg" main.py`
