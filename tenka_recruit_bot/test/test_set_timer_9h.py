# -*- coding: utf-8 -*-
"""
Created on Fri Apr  3 00:57:37 2026

@author: User
"""
from pathlib import Path
import cv2

from src.config_loader import load_config
from src.adb_controller import ADBController
from src.template_matcher import TemplateMatcher
from src.screen_locator import centered_search_region
from src.recruit_flow import set_timer_to_9h_by_panel


def main():
    cfg = load_config()
    adb = ADBController(cfg["adb"]["executable"], cfg["adb"]["device"])
    adb.connect()

    matcher = TemplateMatcher("assets/templates/buttons")

    img = adb.screencap()

    panel_cfg = cfg["game"]["buttons"]["timer_panel"]
    search_region = centered_search_region(img, panel_cfg)

    result = matcher.find(
        img,
        template_name="timer_panel_full",
        threshold=0.93,
        search_region=search_region,
    )

    vis = img.copy()
    sx1, sy1, sx2, sy2 = search_region
    cv2.rectangle(vis, (sx1, sy1), (sx2, sy2), (0, 255, 0), 2)

    if result is None:
        print("timer panel not found")
        Path("assets/debug").mkdir(parents=True, exist_ok=True)
        adb.save_debug_screen(vis, "assets/debug/timer_panel_vis.png")
        print("saved: assets/debug/timer_panel_vis.png")
        return

    bx, by, bw, bh = result["bbox"]
    cv2.rectangle(vis, (bx, by), (bx + bw, by + bh), (0, 0, 255), 2)

    rel_x = cfg["game"]["timer"].get("hour_down_rel_x", 0.19)
    rel_y = cfg["game"]["timer"].get("hour_down_rel_y", 0.80)
    tap_x = int(bx + bw * rel_x)
    tap_y = int(by + bh * rel_y)

    cv2.circle(vis, (tap_x, tap_y), 12, (255, 0, 0), 2)
    cv2.putText(
        vis,
        f"tap ({tap_x},{tap_y})",
        (tap_x + 10, tap_y - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 0, 0),
        2,
        cv2.LINE_AA,
    )

    Path("assets/debug").mkdir(parents=True, exist_ok=True)
    adb.save_debug_screen(vis, "assets/debug/timer_panel_vis.png")
    print("saved: assets/debug/timer_panel_vis.png")
    print("Now applying one tap to hour_down...")

    ok = set_timer_to_9h_by_panel(adb, cfg, matcher)
    print("set_timer_to_9h_by_panel:", ok)

    img2 = adb.screencap()
    adb.save_debug_screen(img2, "assets/debug/after_set_timer.png")
    print("saved: assets/debug/after_set_timer.png")


if __name__ == "__main__":
    main()
