# -*- coding: utf-8 -*-
"""
用途：
1. 已在招募編輯頁時，辨識目前 5 個 tag
2. 檢查是否符合自動招募條件（5 個可判定、且不含 leader）
3. 用 exact DB 按網站邏輯找最佳組合
4. 自動點選最佳組合對應的 tag

注意：
- 這支只做到「自動選擇 tag」。
- 不會按「開始招募」。
- query 只吃英文 canonical tag id。
"""
import time
from pathlib import Path

from src.config_loader import load_config
from src.adb_controller import ADBController
from src.tag_recognizer import TagRecognizer
from src.recruit_guard import evaluate_auto_recruit_guard, format_guard_report
from src.recruit_query_exact import RecruitQueryExact
from data.tag_aliases import normalize_tag_id, tags_to_zh

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import os
print("CWD =", os.getcwd())
print("SCRIPT =", Path(__file__).resolve())
print("TAG_TEMPLATE_DIR =", Path("assets/templates/tags").resolve())

DEBUG_DIR = PROJECT_ROOT / "assets" / "debug"
DEBUG_DIR.mkdir(parents=True, exist_ok=True)


def main():
    cfg = load_config()

    adb = ADBController(
        adb_executable=cfg["adb"]["executable"],
        device=cfg["adb"]["device"],
    )
    adb.connect()

    recognizer = TagRecognizer(
        template_dir=str(PROJECT_ROOT / "assets" / "templates" / "tags"),
        threshold=0.93,
    )
    q = RecruitQueryExact()

    img = adb.screencap()
    region_cfg = cfg["game"]["regions"]["recruit_conditions"]
    adb.save_debug_screen(img, str(DEBUG_DIR / "recognize_to_select_01_raw.png"))

    # 1. 先完全沿用你已驗證可用的辨識流程
    raw_tags = recognizer.recognize_available_tags(img, region_cfg)
    print("raw recognized tags:", raw_tags)

    if not raw_tags:
        adb.save_debug_screen(img, str(DEBUG_DIR / "recognize_to_select_no_raw_tags.png"))
        raise RuntimeError("recognize_available_tags() 沒有辨識到任何 raw tags。")

    # 2. 做標準化，但不要偷偷丟掉資料
    norm_to_raw = {}
    bad_norm = []

    for raw in raw_tags:
        norm = normalize_tag_id(raw)
        print(f"normalize: raw={raw!r} -> norm={norm!r}")

        if not norm:
            bad_norm.append(raw)
            continue

        norm_to_raw[norm] = raw

    normalized_tags = sorted(norm_to_raw.keys())

    print("normalized tags:", normalized_tags)
    print("zh tags:", tags_to_zh(normalized_tags))

    if bad_norm:
        print("[WARN] 以下 raw tags 無法正規化：", bad_norm)

    if not normalized_tags:
        adb.save_debug_screen(img, str(DEBUG_DIR / "recognize_to_select_no_normalized_tags.png"))
        raise RuntimeError(
            "raw tags 有辨識到，但 normalize_tag_id() 後全部變成空值。"
            f" raw_tags={raw_tags}, bad_norm={bad_norm}"
        )

    # 3. guard 檢查
    guard = evaluate_auto_recruit_guard(normalized_tags, expected_count=5)
    print(format_guard_report(guard))

    if not guard["ok"]:
        adb.save_debug_screen(img, str(DEBUG_DIR / "recognize_to_select_guard_blocked.png"))
        raise RuntimeError(f"停止自動選擇：{guard['reason']}")

    query_tags = guard["normalized_tags"]

    # 4. 只做 nonleader exact query
    payload = q.query_exact(query_tags, top_n=10)
    results = payload.get("results", [])

    print("query mode:", payload.get("mode"))
    print("selected tags:", payload.get("selected_tags"))
    print("selected tags zh:", payload.get("selected_tags_zh"))

    if payload.get("mode") != "nonleader":
        adb.save_debug_screen(img, str(DEBUG_DIR / "recognize_to_select_leader_mode.png"))
        raise RuntimeError("目前這支腳本只允許 nonleader 自動選擇。")

    if not results:
        adb.save_debug_screen(img, str(DEBUG_DIR / "recognize_to_select_no_result.png"))
        raise RuntimeError(f"exact DB 查不到任何可用組合。query_tags={query_tags}")

    best = results[0]
    best_combo = best["combo"]
    best_combo_zh = best["combo_zh"]
    best_percent = best["percent_text"]

    print("best combo:", best_combo)
    print("best combo zh:", best_combo_zh)
    print("best percent:", best_percent)
    print("SR/R/N:", best["sr_count"], best["r_count"], best["n_count"])

    # 5. 對回 raw 模板名稱
    raw_best_combo = []
    missing_raw = []

    for tag in best_combo:
        raw = norm_to_raw.get(tag)
        if raw is None:
            missing_raw.append(tag)
        else:
            raw_best_combo.append(raw)

    print("raw best combo:", raw_best_combo)

    if missing_raw:
        adb.save_debug_screen(img, str(DEBUG_DIR / "recognize_to_select_missing_raw_map.png"))
        raise RuntimeError(f"以下最佳組合 tag 無法映射回畫面模板名稱：{missing_raw}")

    # 6. 定位並點選
    positions = recognizer.find_tag_positions(img, region_cfg, raw_best_combo)
    print("positions:", positions)

    missing_pos = [raw for raw in raw_best_combo if raw not in positions]
    if missing_pos:
        adb.save_debug_screen(img, str(DEBUG_DIR / "recognize_to_select_missing_position.png"))
        raise RuntimeError(f"以下 tag 找不到點擊位置：{missing_pos}")

    for raw_tag in raw_best_combo:
        x, y = positions[raw_tag]
        print(f"tap tag {raw_tag} at ({x}, {y})")
        adb.tap(x, y)
        time.sleep(cfg["runtime"]["tap_delay_sec"])

    img_after = adb.screencap()
    adb.save_debug_screen(img_after, str(DEBUG_DIR / "recognize_to_select_02_after_tap.png"))

    print("[SUCCESS] 已完成自動選擇最佳 tag 組合。")
    print("selected combo:", best_combo)
    print("selected combo zh:", best_combo_zh)
    print("exact percent:", best_percent)


if __name__ == "__main__":
    main()