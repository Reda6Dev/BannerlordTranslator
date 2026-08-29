# -*- coding: utf-8 -*-
"""
data/languages.py
قائمة اللغات الرسمية اللي يقدر البرنامج يترجم مودات Bannerlord لها.
كل لغة فيها: الاسم المعروض، الكود (ISO)، اسم المعالج بمحرك اللعبة، اسم المجلد، إلخ.
"""

OFFICIAL_LANGUAGES = {
    "ar": {"name": "العربية (Arabic)", "code": "ar", "id": "Arabic", "xml_name": "العربية", "sub_ext": "ar", "iso": "ar,ar-SA", "processor": "TaleWorlds.Localization.TextProcessor.LanguageProcessors.ArabicTextProcessor", "folder": "AR"},
    "en": {"name": "English (الإنجليزية)", "code": "en", "id": "English", "xml_name": "English", "sub_ext": "en", "iso": "en,en-US", "processor": "", "folder": "EN"},
    "fr": {"name": "Français (الفرنسية)", "code": "fr", "id": "French", "xml_name": "Français", "sub_ext": "fr", "iso": "fr,fr-FR", "processor": "", "folder": "FR"},
    "de": {"name": "Deutsch (الألمانية)", "code": "de", "id": "German", "xml_name": "Deutsch", "sub_ext": "de", "iso": "de,de-DE", "processor": "", "folder": "DE"},
    "zh-CN": {"name": "简体中文 (Chinese Simplified)", "code": "zh-CN", "id": "Chinese", "xml_name": "简体中文", "sub_ext": "zh", "iso": "zh,zh-CN", "processor": "", "folder": "CNs"},
    "zh-TW": {"name": "繁體中文 (Chinese Traditional)", "code": "zh-TW", "id": "TraditionalChinese", "xml_name": "繁體中文", "sub_ext": "zh-TW", "iso": "zh-TW", "processor": "", "folder": "CNt"},
    "tr": {"name": "Türkçe (التركية)", "code": "tr", "id": "Turkish", "xml_name": "Türkçe", "sub_ext": "tr", "iso": "tr,tr-TR", "processor": "", "folder": "TR"},
    "ru": {"name": "Русский (الروسية)", "code": "ru", "id": "Russian", "xml_name": "Русский", "sub_ext": "ru", "iso": "ru,ru-RU", "processor": "", "folder": "RU"},
    "es": {"name": "Español (الإسبانية)", "code": "es", "id": "Spanish", "xml_name": "Español", "sub_ext": "es", "iso": "es,es-ES", "processor": "", "folder": "SP"},
    "pt": {"name": "Português (البرتغالية)", "code": "pt", "id": "Portuguese", "xml_name": "Português", "sub_ext": "pt", "iso": "pt,pt-BR", "processor": "", "folder": "BR"},
    "pl": {"name": "Polski (البولندية)", "code": "pl", "id": "Polish", "xml_name": "Polski", "sub_ext": "pl", "iso": "pl,pl-PL", "processor": "", "folder": "PL"},
    "it": {"name": "Italiano (الإيطالية)", "code": "it", "id": "Italian", "xml_name": "Italiano", "sub_ext": "it", "iso": "it,it-IT", "processor": "", "folder": "IT"},
    "ko": {"name": "한국어 (الكورية)", "code": "ko", "id": "Korean", "xml_name": "한국어", "sub_ext": "ko", "iso": "ko,ko-KR", "processor": "", "folder": "KO"},
    "ja": {"name": "日本語 (اليابانية)", "code": "ja", "id": "Japanese", "xml_name": "日本語", "sub_ext": "ja", "iso": "ja,ja-JP", "processor": "", "folder": "JP"}
}
