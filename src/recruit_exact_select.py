# -*- coding: utf-8 -*-
"""
Created on Fri Apr  3 12:08:37 2026

@author: User
"""
import time

from src.recruit_guard import (
    GuardStopError,
    evaluate_auto_recruit_guard,
    format_guard_report,
)
from src.recruit_query_exact import RecruitQueryExact
from data.tag_aliases import normalize_tag_id, tags_to_zh


def auto_select_best_tags_exact(adb, cfg, recognizer, q):
    img = adb.screencap()
    region_cfg = cfg["game"]["regions"]["recruit_conditions"]
    
    adaptive = recognizer.recognize_available_tags_adaptive(
        img,
        region_cfg,
        expected_count=5,
        default_threshold=0.95,
        min_threshold=0.90,
        max_threshold=0.99,
        step=0.01,
    )
    
    for r in adaptive["rounds"]:
        print(
            f"[TAG-ADAPT] thr={r['threshold']:.2f}, "
            f"count={r['count']}, tags={r['tags']}"
        )
    
    raw_tags = adaptive["tags"]
    print("adaptive threshold:", adaptive["threshold"])
    print("raw recognized tags:", raw_tags)
    
    '''
    raw_tags = recognizer.recognize_available_tags(img, region_cfg)
    print("raw recognized tags:", raw_tags)
    '''
    
    if not raw_tags:
        raise RuntimeError("沒有辨識到任何詞條。")

    norm_to_raw = {}
    for raw in raw_tags:
        norm = normalize_tag_id(raw)
        if norm:
            norm_to_raw[norm] = raw

    normalized_tags = sorted(norm_to_raw.keys())
    print("normalized tags:", normalized_tags)
    print("zh tags:", tags_to_zh(normalized_tags))

    guard = evaluate_auto_recruit_guard(normalized_tags, expected_count=5)
    print(format_guard_report(guard))
    if not guard["ok"]:
        raise GuardStopError(f"停止自動招募：{guard['reason']}")

    payload = q.query_exact(guard["normalized_tags"], top_n=10)
    results = payload.get("results", [])

    if payload.get("mode") != "nonleader":
        raise RuntimeError("目前自動流程只允許 nonleader exact query。")

    if not results:
        raise RuntimeError("exact DB 查不到任何可用組合。")

    best = results[0]
    best_combo = best["combo"]
    print("best combo:", best_combo)
    print("best combo zh:", best["combo_zh"])
    print("best percent:", best["percent_text"])

    raw_best_combo = []
    for tag in best_combo:
        raw = norm_to_raw.get(tag)
        if raw is None:
            raise RuntimeError(f"最佳組合 tag 無法映射回 raw tag：{tag}")
        raw_best_combo.append(raw)

    positions = recognizer.find_tag_positions(img, region_cfg, raw_best_combo)
    print("positions:", positions)

    for raw_tag in raw_best_combo:
        if raw_tag not in positions:
            raise RuntimeError(f"tag 找不到點擊位置：{raw_tag}")
        x, y = positions[raw_tag]
        print(f"tap tag {raw_tag} at ({x}, {y})")
        adb.tap(x, y)
        time.sleep(cfg["runtime"]["tap_delay_sec"])

    return {
        "raw_tags": raw_tags,
        "normalized_tags": normalized_tags,
        "best_combo": best_combo,
        "best_combo_zh": best["combo_zh"],
        "best_percent": best["percent_text"],
    }
