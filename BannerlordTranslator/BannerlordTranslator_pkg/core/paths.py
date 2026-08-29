# -*- coding: utf-8 -*-
"""
core/paths.py
كل مسارات التخزين اللي يستخدمها البرنامج (مجلد المستندات، ملفات الإعدادات،
القاموس، ذاكرة الترجمة، مجلد السجلات). ملف واحد بسيط عشان أي تغيير بمكان
التخزين (مثلاً لو حبينا نغيره لمجلد ثاني مستقبلًا) يصير بمكان واحد فقط.
"""
import os


def get_app_storage_dir():
    home = os.path.expanduser("~")
    docs = os.path.join(home, "Documents", "BannerlordTranslator")
    os.makedirs(docs, exist_ok=True)
    return docs


APP_DIR = get_app_storage_dir()
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
GLOSSARY_FILE = os.path.join(APP_DIR, "glossary.json")
TM_FILE = os.path.join(APP_DIR, "translation_memory.json")

LOG_DIR = os.path.join(APP_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
