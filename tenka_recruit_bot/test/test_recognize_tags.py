# -*- coding: utf-8 -*-
"""
Created on Thu Apr  2 17:51:38 2026

@author: User
"""
from pathlib import Path
import cv2

from src.config_loader import load_config
from src.adb_controller import ADBController
from src.tag_recognizer import TagRecognizer
from src.screen_locator import abs_region


def main():
    cfg = load_config()

    adb = ADBController(
        adb_executable=cfg["adb"]["executable"],
        device=cfg["adb"]["device"],
    )
    adb.connect()

    recognizer = TagRecognizer(
        template_dir="assets/templates/tags",
        threshold=0.90,   # 若誤判太多可改成 0.86~0.90
    )

    print(f"loaded templates: {list(recognizer.templates.keys())}")
    if not recognizer.templates:
        raise RuntimeError("No templates loaded from assets/templates/tags")

    img = adb.screencap()

    debug_dir = Path("assets/debug")
    debug_dir.mkdir(parents=True, exist_ok=True)
    adb.save_debug_screen(img, str(debug_dir / "recognize_full.png"))

    region_cfg = cfg["game"]["regions"]["recruit_conditions"]
    x1, y1, x2, y2 = abs_region(img, region_cfg)
    roi = img[y1:y2, x1:x2].copy()
    cv2.imwrite(str(debug_dir / "recognize_roi.png"), roi)

    tags = recognizer.recognize_available_tags(img, region_cfg)
    print("recognized tags:", tags)

    positions = recognizer.find_tag_positions(img, region_cfg, tags)
    print("positions:", positions)

    vis = img.copy()
    cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)

    for tag, (cx, cy) in positions.items():
        cv2.circle(vis, (cx, cy), 12, (0, 0, 255), 2)
        cv2.putText(
            vis,
            tag,
            (cx + 10, cy - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )

    out_path = debug_dir / "recognized_tags_vis.png"
    cv2.imwrite(str(out_path), vis)
    print(f"saved visualization to: {out_path}")


if __name__ == "__main__":
    main()
