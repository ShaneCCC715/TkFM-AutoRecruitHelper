# -*- coding: utf-8 -*-
"""
Created on Thu Apr  2 23:47:59 2026

@author: User
"""
import time

from src.config_loader import load_config
from src.adb_controller import ADBController
from src.tag_recognizer import TagRecognizer
from src.recruit_optimizer import RecruitOptimizer
from src.screen_locator import ratio_to_abs, centered_search_region
from src.state_machine import detect_state, ScreenState
from src.template_matcher import TemplateMatcher
from data.tag_aliases import normalize_tag_id, tags_to_zh


def wait_until_leave_recruit_edit(adb, timeout_sec=10.0, poll_sec=0.6):
    start = time.time()
    last_state = None

    while time.time() - start < timeout_sec:
        img = adb.screencap()
        state = detect_state(img)
        last_state = state

        if state != ScreenState.RECRUIT_EDIT:
            return True, state, img

        time.sleep(poll_sec)

    img = adb.screencap()
    return False, last_state, img


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
    optimizer = RecruitOptimizer()
    
    matcher = TemplateMatcher("assets/templates/buttons")

    img = adb.screencap()
    state = detect_state(img)
    print("initial state:", state.name)

    if state != ScreenState.RECRUIT_EDIT:
        raise RuntimeError("請先把畫面停在『全境徵才 -> 招募條件編輯頁』再執行。")

    region_cfg = cfg["game"]["regions"]["recruit_conditions"]

    raw_tags = recognizer.recognize_available_tags(img, region_cfg)
    print("raw recognized tags:", raw_tags)

    norm_to_raw = {}
    for raw in raw_tags:
        norm = normalize_tag_id(raw)
        norm_to_raw[norm] = raw

    normalized_tags = sorted(norm_to_raw.keys())
    print("normalized tags:", normalized_tags)
    print("zh tags:", tags_to_zh(normalized_tags))

    if not normalized_tags:
        raise RuntimeError("沒有辨識到任何詞條。")

    best_combo, score = optimizer.pick_best_combo(normalized_tags, max_select=3)
    print("best combo (id):", best_combo)
    print("best combo (zh):", tags_to_zh(best_combo))
    print("score:", score)

    raw_best_combo = [norm_to_raw[t] for t in best_combo if t in norm_to_raw]
    positions = recognizer.find_tag_positions(img, region_cfg, raw_best_combo)
    print("positions:", positions)

    # 點三詞
    for raw_tag in raw_best_combo:
        if raw_tag not in positions:
            print(f"[WARN] position not found for {raw_tag}")
            continue

        x, y = positions[raw_tag]
        print(f"tap tag {raw_tag} at ({x}, {y})")
        adb.tap(x, y)
        time.sleep(cfg["runtime"]["tap_delay_sec"])

    # 存一下選詞後畫面
    img_after_tags = adb.screencap()
    adb.save_debug_screen(img_after_tags, "assets/debug/after_select_tags.png")
    print("saved: assets/debug/after_select_tags.png")

    # 點開始招募
    img_after_tags = adb.screencap()
    adb.save_debug_screen(img_after_tags, "assets/debug/after_select_tags.png")
    print("saved: assets/debug/after_select_tags.png")
    
    button_cfg = cfg["game"]["buttons"]["start_recruit"]
    search_region = centered_search_region(img_after_tags, button_cfg)
    
    result = matcher.find(
        img_after_tags,
        template_name="recruitment_begins",
        threshold=0.93,
        search_region=search_region,
    )
    
    if result is None:
        raise RuntimeError("找不到『開始招募』按鈕，請檢查模板、搜尋範圍或 threshold。")
    
    sx, sy = result["center"]
    print(f"tap start_recruit by template at ({sx}, {sy}), score={result['score']:.4f}")
    adb.tap(sx, sy)

    # 等到離開 RECRUIT_EDIT
    ok, new_state, img_after = wait_until_leave_recruit_edit(
        adb,
        timeout_sec=10.0,
        poll_sec=cfg["runtime"]["screen_poll_interval_sec"],
    )

    adb.save_debug_screen(img_after, "assets/debug/after_start_recruit.png")
    print("saved: assets/debug/after_start_recruit.png")

    if ok:
        print(f"[SUCCESS] left RECRUIT_EDIT, new state = {new_state.name}")
    else:
        print(f"[FAIL] still in RECRUIT_EDIT after timeout, last state = {new_state.name}")


if __name__ == "__main__":
    main()
