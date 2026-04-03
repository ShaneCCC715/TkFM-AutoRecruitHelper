# -*- coding: utf-8 -*-
"""
Created on Thu Apr  2 16:41:05 2026

@author: User
"""
from src.config_loader import load_config
from src.adb_controller import ADBController

cfg = load_config()
adb = ADBController(cfg["adb"]["executable"], cfg["adb"]["device"])
adb.connect()

img = adb.screencap()
adb.save_debug_screen(img, "assets/debug/test.png")
print("saved to assets/debug/test.png")
