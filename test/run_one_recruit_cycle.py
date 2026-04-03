# -*- coding: utf-8 -*-
"""
Created on Fri Apr  3 01:01:30 2026

@author: User
"""
import time
from pathlib import Path

from src.config_loader import load_config
from src.adb_controller import ADBController
from src.template_matcher import TemplateMatcher
from src.tag_recognizer import TagRecognizer
from src.recruit_optimizer import RecruitOptimizer
from src.recruit_flow import open_nth_empty_slot, set_timer_to_9h_by_panel, count_empty_slots_in_image, wait_until_recruit_started
from src.screen_locator import centered_search_region
from src.state_machine import detect_state, ScreenState
from data.tag_aliases import normalize_tag_id, tags_to_zh


def wait_until_recruit_edit(adb, timeout_sec=8.0, poll_sec=0.6):
    start = time.time()
    last_state = None
    while time.time() - start < timeout_sec:
        img = adb.screencap()
        state = detect_state(img)
        last_state = state
        if state == ScreenState.RECRUIT_EDIT:
            return True, img
        time.sleep(poll_sec)
    return False, None


def wait_until_leave_recruit_edit(adb, timeout_sec=10.0, poll_sec=0.6):
    start = time.time()
    last_state = None
    last_img = None
    while time.time() - start < timeout_sec:
        img = adb.screencap()
        state = detect_state(img)
        last_state = state
        last_img = img
        if state != ScreenState.RECRUIT_EDIT:
            return True, state, img
        time.sleep(poll_sec)
    return False, last_state, last_img


def main():
    cfg = load_config()

    adb = ADBController(
        adb_executable=cfg["adb"]["executable"],
        device=cfg["adb"]["device"],
    )
    adb.connect()

    matcher = TemplateMatcher("assets/templates/buttons")
    recognizer = TagRecognizer(
        template_dir="assets/templates/tags",
        threshold=0.95,
    )
    optimizer = RecruitOptimizer()

    Path("assets/debug").mkdir(parents=True, exist_ok=True)
    
    img0 = adb.screencap()
    empty_count_before, matches_before = count_empty_slots_in_image(img0, cfg, matcher)
    print("empty_count_before:", empty_count_before)
    
    # 1. 從主列表打開第 0 個空欄
    ok = open_nth_empty_slot(adb, cfg, matcher, slot_index=0)
    print("open_nth_empty_slot:", ok)
    if not ok:
        raise RuntimeError("無法進入空的招募欄位。")

    ok, img = wait_until_recruit_edit(
        adb,
        timeout_sec=8.0,
        poll_sec=cfg["runtime"]["screen_poll_interval_sec"],
    )
    if not ok:
        raise RuntimeError("沒有成功進入招募編輯頁。")

    adb.save_debug_screen(img, "assets/debug/cycle_step_1_enter_edit.png")
    print("saved: assets/debug/cycle_step_1_enter_edit.png")

    # 2. 調整時間到 9 小時
    set_timer_to_9h_by_panel(adb, cfg, matcher)
    time.sleep(0.8)

    img = adb.screencap()
    adb.save_debug_screen(img, "assets/debug/cycle_step_2_after_timer.png")
    print("saved: assets/debug/cycle_step_2_after_timer.png")

    # 3. 辨識可選詞條
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

    # 4. 選最佳三詞
    best_combo, score = optimizer.pick_best_combo(normalized_tags, max_select=3)
    print("best combo (id):", best_combo)
    print("best combo (zh):", tags_to_zh(best_combo))
    print("score:", score)

    raw_best_combo = [norm_to_raw[t] for t in best_combo if t in norm_to_raw]
    positions = recognizer.find_tag_positions(img, region_cfg, raw_best_combo)
    print("positions:", positions)

    # 5. 點三詞
    for raw_tag in raw_best_combo:
        if raw_tag not in positions:
            print(f"[WARN] position not found for {raw_tag}")
            continue

        x, y = positions[raw_tag]
        print(f"tap tag {raw_tag} at ({x}, {y})")
        adb.tap(x, y)
        time.sleep(cfg["runtime"]["tap_delay_sec"])

    img = adb.screencap()
    adb.save_debug_screen(img, "assets/debug/cycle_step_3_after_tags.png")
    print("saved: assets/debug/cycle_step_3_after_tags.png")

    # 6. 模板定位「開始招募」
    button_cfg = cfg["game"]["buttons"]["start_recruit"]
    search_region = centered_search_region(img, button_cfg)

    result = matcher.find(
        img,
        template_name="recruitment_begins",
        threshold=0.93,
        search_region=search_region,
    )
    if result is None:
        raise RuntimeError("找不到『開始招募』按鈕。")

    sx, sy = result["center"]
    print(f"tap start_recruit at ({sx}, {sy}), score={result['score']:.4f}")
    adb.tap(sx, sy)

    # 7. 確認已離開編輯頁
    ok, img_after, empty_count_after = wait_until_recruit_started(
        adb,
        cfg,
        matcher,
        empty_count_before=empty_count_before,
        timeout_sec=10.0,
    )
    
    if img_after is not None:
        adb.save_debug_screen(img_after, "assets/debug/cycle_step_4_after_start.png")
        print("saved: assets/debug/cycle_step_4_after_start.png")
    
    if ok:
        print(
            f"[SUCCESS] recruit started. "
            f"empty_count_before={empty_count_before}, "
            f"empty_count_after={empty_count_after}"
        )
    else:
        print("[FAIL] recruit start not confirmed within timeout")
    

if __name__ == "__main__":
    main()
