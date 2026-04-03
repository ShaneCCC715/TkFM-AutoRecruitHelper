# -*- coding: utf-8 -*-
"""
Created on Thu Apr  2 16:45:27 2026

@author: User
"""
from src.config_loader import load_config
from src.adb_controller import ADBController
import time

cfg = load_config()
adb = ADBController(cfg["adb"]["executable"], cfg["adb"]["device"])
adb.connect()

# 先抓一張當前畫面
img = adb.screencap()
h, w = img.shape[:2]
print(f"screen size = {w}x{h}")

# 點螢幕中央
x = w // 2
y = h // 2
print(f"tap at ({x}, {y})")
adb.tap(x, y)

time.sleep(1.0)

# 再存一張確認點完後有沒有變化
img2 = adb.screencap()
adb.save_debug_screen(img2, "assets/debug/test_after_tap.png")
print("saved to assets/debug/test_after_tap.png")
