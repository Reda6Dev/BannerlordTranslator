# -*- coding: utf-8 -*-
"""
providers/registry.py
نقطة دخول واحدة لاختيار محرك الترجمة حسب رقمه بقائمة الواجهة (engine_cb).
هذا بديل دالة get_translator() اللي كانت جوه الكلاس الرئيسي.

لإضافة محرك جديد مستقبلًا (زي Claude API): أنشئ ملف provider جديد يرث من
TranslationProvider، ثم ضيف شرط جديد هنا بدون ما تلمس أي ملف ثاني.
"""
from .google import GoogleProvider
from .deepl import DeeplProvider


def get_translator(engine_index, src_code, tgt_code, api_key=None):
    """
    engine_index: رقم المحرك المختار بالواجهة (نفس ترتيب engine_cb).
    src_code: كود لغة المصدر ("auto" أو كود ISO).
    tgt_code: كود لغة الهدف.
    api_key: مطلوب فقط لمحرك DeepL (index=1).
    """
    s_code = "auto" if "auto" in src_code.lower() else src_code

    if engine_index == 1:
        return DeeplProvider(source=s_code, target=tgt_code, api_key=api_key)
    else:
        return GoogleProvider(source=s_code, target=tgt_code)
