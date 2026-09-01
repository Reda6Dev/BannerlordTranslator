# ⚔️ Bannerlord Auto-Translator (مترجم بانرلوود الآلي)

[English description below]

أداة ذكية ومفتوحة المصدر لترجمة مودات لعبة Mount & Blade II: Bannerlord حصرياً لتسريع عملية التعريب مع ضمان سلامة الأكواد اللغوية.

## 🌟 التحديثات الجديدة (الإصدار 1.2.0)
* **دعم محرك DeepL الرسمي:** انتقال كامل لواجهة برمجة تطبيقات (API) الخاصة بـ DeepL لترجمة أسرع، أدق، وبدون مشاكل حظر الـ IP.
* **دعم ديناميكي للغات (14 لغة):** المحرك الآن يستقبل رموز اللغات ديناميكياً لتشغيل الترجمة بجميع لغات الأداة المتاحة بدلاً من التقيد بلغة واحدة.
* **إصلاح واجهة المستخدم والحفظ:** الأداة الآن تتذكر آخر محرك تم استخدامه وتقوم بحقن مفتاح الـ API الخاص بك تلقائياً عند الإقلاع دون تدخل يدوي.
* **معالجة ذكية للأخطاء (Graceful Error Handling):** حماية كاملة ضد انهيار البرنامج في حال انتهاء رصيد المفتاح أو إدخال مفتاح خاطئ أثناء الترجمة الجماعية.

## ⚙️ الميزات الأساسية
* **الترجمة السياقية الذكية:** الحفاظ على أكواد اللعبة المتغيرة (مثل `{TARGET_CHARACTER}`) دون إتلافها أو ترجمتها بالخطأ.
* **المقارنة الذكية (Smart Diff):** الأداة تترجم النصوص الجديدة فقط وتتجاهل ما تم ترجمته مسبقاً لتوفير الوقت ورصيد الـ API.
* **محرر تفاعلي مدمج:** مراجعة وتعديل النصوص برمجياً من داخل الأداة مع مزامنة فورية لملفات الذاكرة (`translation_memory.json`).
* **نظام القاموس (Glossary):** توحيد المصطلحات الهامة في اللعبة وفرضها على محرك الترجمة لضمان اتساق النصوص.

## 🚀 التحميل والاستخدام
يمكنك تحميل النسخة الجاهزة للتشغيل (ملف `.exe`) مباشرة من قسم الإصدارات (**Releases**) على يمين الصفحة، أو عبر صفحة الأداة الرسمية على موقع [Nexus Mods](https://www.nexusmods.com/mountandblade2bannerlord/mods/12960?tab=description).
لا تحتاج إلى تثبيت بيئة بايثون إذا قمت بتحميل ملف الـ `exe`.

---

# ⚔️ Bannerlord Auto-Translator

An intelligent, open-source translation tool dedicated to Mount & Blade II: Bannerlord mods, designed to speed up the localization process while ensuring code integrity.

## 🌟 What's New (v1.2.0)
* **Official DeepL API Integration:** Fully migrated to DeepL API for faster, more accurate translations without IP ban issues.
* **Dynamic Language Support (14 Languages):** The engine now dynamically processes target language codes for all supported UI languages.
* **UI Config State Fix:** The tool now remembers your last used engine and automatically injects your API key on startup.
* **Graceful Error Handling:** Full protection against crashes due to API quota limits or invalid keys during batch processing.

## ⚙️ Core Features
* **Smart Contextual Translation:** Preserves game placeholders (e.g., `{TARGET_CHARACTER}`) from being corrupted during translation.
* **Smart Diff System:** Only translates new strings and skips previously translated ones to save time and API quota.
* **Interactive Editor:** Review and manually edit strings directly within the tool with instant translation memory syncing.
* **Glossary System:** Force specific terminology to ensure translation consistency across mods.

## 🚀 Download & Usage
You can download the standalone executable (`.exe`) directly from the **Releases** tab on the right, or via our official [Nexus Mods page](https://www.nexusmods.com/mountandblade2bannerlord/mods/12960?tab=description).
No Python installation is required if you download the compiled release.
