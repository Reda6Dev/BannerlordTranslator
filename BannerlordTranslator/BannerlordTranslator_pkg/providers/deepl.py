# -*- coding: utf-8 -*-
"""
providers/deepl.py — محرك DeepL. يحتاج API Key من المستخدم (يدخله بالواجهة).
"""
import deepl
from .base import TranslationProvider


class DeeplProvider(TranslationProvider):
    def __init__(self, source, target, api_key):
        if not api_key:
            raise ValueError("Please provide DeepL API Key.")

        self.api_key = api_key
        self.source = None if source == "auto" else str(source).upper()
        self.target = "AR" if not target else str(target).upper()
        self._engine = deepl.Translator(self.api_key)

    def translate(self, text, target_lang=None):
        target_lang = (target_lang or self.target or "AR").upper()
        params = {"text": text, "target_lang": target_lang}
        if self.source:
            params["source_lang"] = self.source

        try:
            result = self._engine.translate_text(**params)
            return result.text
        except deepl.exceptions.AuthorizationException:
            return "خطأ: المفتاح غير صالح"
        except deepl.exceptions.QuotaExceededException:
            return "خطأ: انتهى رصيد DeepL"
        except Exception:
            return "خطأ: فشل الترجمة عبر DeepL"
