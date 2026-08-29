# -*- coding: utf-8 -*-
"""
providers/base.py
الشكل الموحّد اللي يجب على أي محرك ترجمة يلتزم فيه. أي محرك جديد (زي Claude
API مستقبلًا) لازم يكون عنده دالة translate(text) بس، وباقي البرنامج يتعامل
معه بنفس الطريقة بدون ما يهتم بتفاصيل المحرك الداخلية.
"""


class TranslationProvider:
    def translate(self, text):
        """يترجم نص واحد ويرجع النتيجة كنص. لازم كل محرك يطبّقها."""
        raise NotImplementedError
