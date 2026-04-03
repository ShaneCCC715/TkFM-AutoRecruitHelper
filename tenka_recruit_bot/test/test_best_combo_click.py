# -*- coding: utf-8 -*-
"""
Created on Thu Apr  2 23:42:53 2026

@author: User
"""
import time

from src.config_loader import load_config
from src.adb_controller import ADBController
from src.tag_recognizer import TagRecognizer
from src.recruit_optimizer import RecruitOptimizer
from data.tag_aliases import normalize_tag_id, tags_to_zh


def main():
    cfg = load_config()

    adb = ADBController(
        adb_executable=cfg["adb"]["executable"],
        device=cfg["adb"]["device"],
    )
    adb.connect()

    recognizer = TagRecognizer(
        template_dir="assets/templates/tags",
        threshold=0.90,
    )
    optimizer = RecruitOptimizer()

    img = adb.screencap()
    region_cfg = cfg["game"]["regions"]["recruit_conditions"]

    # 1. 讀到的是模板檔名 id
    raw_tags = recognizer.recognize_available_tags(img, region_cfg)
    print("raw recognized tags:", raw_tags)

    # 2. 做標準化，並保留 normalized -> raw 對照
    norm_to_raw = {}
    for raw in raw_tags:
        norm = normalize_tag_id(raw)
        norm_to_raw[norm] = raw

    normalized_tags = sorted(norm_to_raw.keys())
    print("normalized tags:", normalized_tags)
    print("zh tags:", tags_to_zh(normalized_tags))

    # 3. 選最佳組合
    best_combo, score = optimizer.pick_best_combo(normalized_tags, max_select=3)
    print("best combo (id):", best_combo)
    print("best combo (zh):", tags_to_zh(best_combo))
    print("score:", score)

    # 4. 找回原模板名稱，才能定位按鈕位置
    raw_best_combo = [norm_to_raw[t] for t in best_combo if t in norm_to_raw]
    print("raw best combo:", raw_best_combo)

    positions = recognizer.find_tag_positions(img, region_cfg, raw_best_combo)
    print("positions:", positions)

    # 5. 依序點擊
    for raw_tag in raw_best_combo:
        if raw_tag not in positions:
            print(f"[WARN] position not found for {raw_tag}")
            continue

        x, y = positions[raw_tag]
        print(f"tap {raw_tag} at ({x}, {y})")
        adb.tap(x, y)
        time.sleep(0.8)

    time.sleep(1.0)
    img2 = adb.screencap()
    adb.save_debug_screen(img2, "assets/debug/after_best_combo_click.png")
    print("saved to assets/debug/after_best_combo_click.png")


if __name__ == "__main__":
    main()
