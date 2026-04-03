# -*- coding: utf-8 -*-
"""
Created on Fri Apr  3 01:28:54 2026

@author: User
"""
from pathlib import Path
import json
import argparse
import cv2

from src.config_loader import load_config
from src.adb_controller import ADBController
from src.template_matcher import TemplateMatcher
from src.screen_locator import centered_search_region


def draw_result(img, search_region, result, label):
    vis = img.copy()

    x1, y1, x2, y2 = search_region
    cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # search center
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    cv2.circle(vis, (cx, cy), 8, (0, 255, 255), 2)

    if result is not None:
        bx, by, bw, bh = result["bbox"]
        mx, my = result["center"]
        score = result["score"]

        cv2.rectangle(vis, (bx, by), (bx + bw, by + bh), (0, 0, 255), 2)
        cv2.circle(vis, (mx, my), 10, (255, 0, 0), 2)
        cv2.putText(
            vis,
            f"{label} score={score:.4f}",
            (max(10, bx), max(30, by - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )
    else:
        cv2.putText(
            vis,
            f"{label} NOT FOUND",
            (max(10, x1), max(30, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )

    return vis


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--only",
        type=str,
        default="",
        help="只測某些 buttons，逗號分隔，例如 --only start_recruit,sure"
    )
    parser.add_argument(
        "--recapture-per-button",
        action="store_true",
        help="每個 button 都重新截圖一次；預設只截一次當前畫面"
    )
    args = parser.parse_args()

    cfg = load_config()
    adb = ADBController(cfg["adb"]["executable"], cfg["adb"]["device"])
    adb.connect()

    matcher = TemplateMatcher("assets/templates/buttons")

    buttons_cfg = cfg["game"]["buttons"]
    '''
    selected = None
    if args.only.strip():
        selected = {x.strip() for x in args.only.split(",") if x.strip()}
    '''
    selected = {"start_recruit"}
    
    out_dir = Path("assets/debug/button_test")
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = {}

    # 預設只抓一次當前畫面，方便在同一個頁面校準
    base_img = None if args.recapture_per_button else adb.screencap()

    for button_key, button_cfg in buttons_cfg.items():
        if selected is not None and button_key not in selected:
            continue

        img = adb.screencap() if args.recapture_per_button else base_img.copy()

        template_name = button_cfg.get("template", button_key)
        threshold = float(button_cfg.get("threshold", 0.93))
        search_region = centered_search_region(img, button_cfg)

        result = matcher.find(
            img,
            template_name=template_name,
            threshold=threshold,
            search_region=search_region,
        )

        vis = draw_result(img, search_region, result, button_key)
        out_path = out_dir / f"{button_key}.png"
        adb.save_debug_screen(vis, str(out_path))

        item = {
            "template": template_name,
            "threshold": threshold,
            "search_region": list(search_region),
            "found": result is not None,
        }

        if result is not None:
            item["score"] = float(result["score"])
            item["center"] = list(result["center"])
            item["bbox"] = list(result["bbox"])

        summary[button_key] = item
        print(f"[{button_key}] found={item['found']} template={template_name}")

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved summary to: {summary_path}")


if __name__ == "__main__":
    main()
