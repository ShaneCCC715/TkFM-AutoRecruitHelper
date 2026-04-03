# -*- coding: utf-8 -*-
"""
Created on Thu Apr  2 23:59:21 2026

@author: User
"""
from pathlib import Path
import cv2

from src.config_loader import load_config
from src.adb_controller import ADBController
from src.template_matcher import TemplateMatcher
from src.screen_locator import centered_search_region


def main():
    cfg = load_config()

    adb = ADBController(
        adb_executable=cfg["adb"]["executable"],
        device=cfg["adb"]["device"],
    )
    adb.connect()

    matcher = TemplateMatcher("assets/templates/buttons")
    img = adb.screencap()

    button_cfg = cfg["game"]["buttons"]["start_recruit"]
    search_region = centered_search_region(img, button_cfg)

    result = matcher.find(
        img,
        template_name="recruitment_begins",
        threshold=0.93,
        search_region=search_region,
    )

    vis = img.copy()
    x1, y1, x2, y2 = search_region
    cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)

    if result is None:
        print("start button not found")
    else:
        cx, cy = result["center"]
        bx, by, bw, bh = result["bbox"]
        print("found:", result)

        cv2.rectangle(vis, (bx, by), (bx + bw, by + bh), (0, 0, 255), 2)
        cv2.circle(vis, (cx, cy), 10, (255, 0, 0), 2)

    Path("assets/debug").mkdir(parents=True, exist_ok=True)
    adb.save_debug_screen(vis, "assets/debug/find_start_button_vis.png")
    print("saved: assets/debug/find_start_button_vis.png")


if __name__ == "__main__":
    main()