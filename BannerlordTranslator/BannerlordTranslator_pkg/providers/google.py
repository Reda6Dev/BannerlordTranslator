# -*- coding: utf-8 -*-
"""providers/google.py — محرك جوجل ترانسليت (المحرك الافتراضي، مجاني)."""
from deep_translator import GoogleTranslator as _GoogleTranslator
from .base import TranslationProvider


class GoogleProvider(TranslationProvider):
    def __init__(self, source, target):
        self._engine = _GoogleTranslator(source=source, target=target)

    def translate(self, text):
        return self._engine.translate(text)
