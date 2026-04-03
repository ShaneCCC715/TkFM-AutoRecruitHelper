# -*- coding: utf-8 -*-
"""
Created on Thu Apr  2 23:28:47 2026

@author: User
"""
import time

from src.config_loader import load_config
from src.adb_controller import ADBController
from src.tag_recognizer import TagRecognizer


def main():
    cfg = load_config()

    adb = ADBController(
        adb_executable=cfg["adb"]["executable"],
        device=cfg["adb"]["device"],
    )
    adb.connect()

    recognizer = TagRecognizer(
        template_dir="assets/templates/tags",
        threshold=0.95,
    )

    img = adb.screencap()
    region_cfg = cfg["game"]["regions"]["recruit_conditions"]

    tags = recognizer.recognize_available_tags(img, region_cfg)
    positions = recognizer.find_tag_positions(img, region_cfg, tags)

    print("recognized tags:", tags)
    print("positions:", positions)

    # 先只測一個，避免亂點太多
    target = "fight_stronger"
    if target not in positions:
        print(f"{target} not found")
        return

    x, y = positions[target]
    print(f"tap {target} at ({x}, {y})")
    adb.tap(x, y)

    time.sleep(1.0)
    img2 = adb.screencap()
    adb.save_debug_screen(img2, "assets/debug/after_click_output.png")
    print("saved to assets/debug/after_click_output.png")


if __name__ == "__main__":
    main()