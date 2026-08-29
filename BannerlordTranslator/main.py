# -*- coding: utf-8 -*-
"""
main.py — نقطة تشغيل برنامج Bannerlord Mod Translator.
شغّل هذا الملف فقط: python main.py
"""
import tkinter as tk

from BannerlordTranslator_pkg.ui.main_window import BannerlordTranslatorV12


def main():
    root = tk.Tk()
    app = BannerlordTranslatorV12(root)
    root.mainloop()


if __name__ == "__main__":
    main()
