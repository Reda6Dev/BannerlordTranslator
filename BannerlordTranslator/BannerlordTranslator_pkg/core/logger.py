# -*- coding: utf-8 -*-
"""
core/logger.py
سجل أخطاء يومي بسيط (logs/YYYY-MM-DD_Translator.log). Best-effort دائمًا:
لو فشلت الكتابة (مثلاً القرص محمي) ما يوقف البرنامج أبدًا.
"""
import time
import os

from .paths import LOG_DIR


def get_log_file_path():
    return os.path.join(LOG_DIR, time.strftime("%Y-%m-%d") + "_Translator.log")


def write_log_line(level, message):
    try:
        line = f"[{time.strftime('%H:%M:%S')}] {level:<5} {message}"
        with open(get_log_file_path(), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
