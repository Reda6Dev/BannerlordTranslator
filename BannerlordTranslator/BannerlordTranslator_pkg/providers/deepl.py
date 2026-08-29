# -*- coding: utf-8 -*-
"""
providers/deepl.py — محرك DeepL. يحتاج API Key من المستخدم (يدخله بالواجهة).
"""
from deep_translator import DeeplTranslator as _DeeplTranslator
from .base import TranslationProvider


class DeeplProvider(TranslationProvider):
    def __init__(self, source, target, api_key):
        if not api_key:
            raise ValueError("Please provide DeepL API Key.")
        dl_source = None if source == "auto" else source.upper()
        self._engine = _DeeplTranslator(api_key=api_key, source=dl_source, target=target.upper(), use_free_api=True)

    def translate(self, text):
        return self._engine.translate(text)
