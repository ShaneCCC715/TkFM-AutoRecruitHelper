# -*- coding: utf-8 -*-
"""
Created on Fri Apr  3 00:33:57 2026

@author: User
"""
import time
from pathlib import Path
import cv2

from .state_machine import detect_state, ScreenState
from .screen_locator import abs_region, centered_search_region


def set_timer_hour_from_assumption(adb, cfg, matcher):
    timer_cfg = cfg["game"]["timer"]
    if not timer_cfg.get("enabled", False):
        print("[INFO] timer auto set disabled")
        return True

    assume_initial = int(timer_cfg.get("assume_initial_hour", 1))
    target_hour = int(timer_cfg.get("target_hour", 9))
    delta = target_hour - assume_initial

    if delta == 0:
        print("[INFO] timer already assumed at target hour")
        return True

    img = adb.screencap()
    button_cfg = cfg["game"]["buttons"]["hour_up"]
    search_region = centered_search_region(img, button_cfg)

    result = matcher.find(
        img,
        template_name="hour_up",
        threshold=0.93,
        search_region=search_region,
    )
    if result is None:
        raise RuntimeError("找不到 hour_up 按鈕模板。")

    x, y = result["center"]

    if delta > 0:
        print(f"[INFO] adjust timer hour: +{delta}")
        for i in range(delta):
            adb.tap(x, y)
            time.sleep(cfg["runtime"]["tap_delay_sec"])
    else:
        raise RuntimeError("目前這版只支援往上加小時，若要往下減再補 hour_down 模板。")

    return True

def open_first_empty_slot(adb, cfg, matcher, timeout_sec=8.0):
    img = adb.screencap()

    if detect_state(img) != ScreenState.MAIN_LIST:
        raise RuntimeError("目前不在主列表頁，無法找空欄位。")

    slot_region = abs_region(img, cfg["game"]["regions"]["slot_list"])
    matches = matcher.find_all(
        img,
        template_name="empty_slot_plus",
        threshold=0.92,
        search_region=slot_region,
        max_results=8,
        nms_iou_threshold=0.2,
    )

    if not matches:
        raise RuntimeError("找不到空的招募欄位。")

    matches.sort(key=lambda m: (m["center"][1], m["center"][0]))
    target = matches[0]
    x, y = target["center"]

    print(f"[INFO] open empty slot at ({x}, {y}), score={target['score']:.4f}")
    adb.tap(x, y)

    start = time.time()
    while time.time() - start < timeout_sec:
        time.sleep(cfg["runtime"]["screen_poll_interval_sec"])
        img2 = adb.screencap()
        state = detect_state(img2)
        if state == ScreenState.RECRUIT_EDIT:
            return True

    return False



def get_empty_slot_matches(adb, cfg, matcher):
    img = adb.screencap()
    slot_region = abs_region(img, cfg["game"]["regions"]["slot_list"])

    matches = matcher.find_all(
        img,
        template_name="empty_slot_plus",
        threshold=0.92,
        search_region=slot_region,
        max_results=8,
        nms_iou_threshold=0.2,
    )

    matches.sort(key=lambda m: (m["center"][1], m["center"][0]))
    return matches

def open_nth_empty_slot(adb, cfg, matcher, slot_index=0, timeout_sec=8.0):
    matches = get_empty_slot_matches(adb, cfg, matcher)

    print(f"[INFO] empty slot count = {len(matches)}")
    if not matches:
        raise RuntimeError("找不到空欄位。")

    if slot_index < 0 or slot_index >= len(matches):
        raise RuntimeError(f"slot_index={slot_index} 超出範圍，只有 {len(matches)} 個空欄。")

    target = matches[slot_index]
    x, y = target["center"]

    print(f"[INFO] open empty slot #{slot_index} at ({x}, {y}), score={target['score']:.4f}")
    adb.tap(x, y)

    start = time.time()
    while time.time() - start < timeout_sec:
        time.sleep(cfg["runtime"]["screen_poll_interval_sec"])
        img2 = adb.screencap()
        state = detect_state(img2)

        if state == ScreenState.RECRUIT_EDIT:
            return True

    return False

def set_timer_to_9h_by_panel(adb, cfg, matcher):
    timer_cfg = cfg["game"]["timer"]
    if not timer_cfg.get("enabled", False):
        print("[INFO] timer auto set disabled")
        return True

    if timer_cfg.get("mode") != "hour_down_once":
        raise RuntimeError("目前只支援 mode=hour_down_once")

    img = adb.screencap()

    panel_cfg = cfg["game"]["buttons"]["timer_panel"]
    search_region = centered_search_region(img, panel_cfg)

    result = matcher.find(
        img,
        template_name="timer_panel_full",
        threshold=0.93,
        search_region=search_region,
    )
    if result is None:
        raise RuntimeError("找不到 timer_panel_full 模板")

    bx, by, bw, bh = result["bbox"]

    rel_x = timer_cfg.get("hour_down_rel_x", 0.19)
    rel_y = timer_cfg.get("hour_down_rel_y", 0.80)

    tap_x = int(bx + bw * rel_x)
    tap_y = int(by + bh * rel_y)

    print(f"[INFO] tap hour_down once at ({tap_x}, {tap_y}), panel score={result['score']:.4f}")
    adb.tap(tap_x, tap_y)
    time.sleep(cfg["runtime"]["tap_delay_sec"])

    return True

def save_slot_matches_debug(adb, cfg, matcher, out_path="assets/debug/slot_matches_vis.png"):
    img = adb.screencap()
    vis = img.copy()

    slot_region = abs_region(img, cfg["game"]["regions"]["slot_list"])
    x1, y1, x2, y2 = slot_region
    cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)

    matches = matcher.find_all(
        img,
        template_name="empty_slot_plus",
        threshold=0.92,
        search_region=slot_region,
        max_results=8,
        nms_iou_threshold=0.2,
    )

    for i, m in enumerate(matches):
        bx, by, bw, bh = m["bbox"]
        cx, cy = m["center"]
        cv2.rectangle(vis, (bx, by), (bx + bw, by + bh), (0, 0, 255), 2)
        cv2.circle(vis, (cx, cy), 10, (255, 0, 0), 2)
        cv2.putText(
            vis,
            f"{i}:{m['score']:.2f}",
            (cx + 8, cy - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )

    Path("assets/debug").mkdir(parents=True, exist_ok=True)
    adb.save_debug_screen(vis, out_path)
    print(f"[INFO] saved: {out_path}")
    
def count_empty_slots_in_image(img, cfg, matcher):
    slot_region = abs_region(img, cfg["game"]["regions"]["slot_list"])

    matches = matcher.find_all(
        img,
        template_name="empty_slot_plus",
        threshold=0.92,
        search_region=slot_region,
        max_results=8,
        nms_iou_threshold=0.2,
    )
    matches.sort(key=lambda m: (m["center"][1], m["center"][0]))
    return len(matches), matches

def has_start_recruit_button(img, cfg, matcher):
    button_cfg = cfg["game"]["buttons"]["start_recruit"]
    search_region = centered_search_region(img, button_cfg)

    result = matcher.find(
        img,
        template_name="start_recruit",
        threshold=0.93,
        search_region=search_region,
    )
    return result is not None

def wait_until_recruit_started(adb, cfg, matcher, empty_count_before, timeout_sec=10.0):
    start = time.time()
    last_img = None

    while time.time() - start < timeout_sec:
        img = adb.screencap()
        last_img = img

        start_btn_exists = has_start_recruit_button(img, cfg, matcher)
        empty_count_now, _ = count_empty_slots_in_image(img, cfg, matcher)

        print(
            f"[WAIT] start_btn_exists={start_btn_exists}, "
            f"empty_count_before={empty_count_before}, "
            f"empty_count_now={empty_count_now}"
        )

        if (not start_btn_exists) and (empty_count_now == max(empty_count_before - 1, 0)):
            return True, img, empty_count_now

        time.sleep(cfg["runtime"]["screen_poll_interval_sec"])

    return False, last_img, None

def find_button_by_cfg(img, cfg, matcher, button_key, template_name=None, threshold=0.93):
    if template_name is None:
        template_name = button_key

    button_cfg = cfg["game"]["buttons"][button_key]
    search_region = centered_search_region(img, button_cfg)

    return matcher.find(
        img,
        template_name=template_name,
        threshold=threshold,
        search_region=search_region,
    )


def wait_for_button(adb, cfg, matcher, button_key, template_name=None, threshold=0.93, timeout_sec=8.0):
    import time

    start = time.time()
    last_img = None
    while time.time() - start < timeout_sec:
        img = adb.screencap()
        last_img = img

        result = find_button_by_cfg(
            img,
            cfg,
            matcher,
            button_key=button_key,
            template_name=template_name,
            threshold=threshold,
        )
        if result is not None:
            return True, img, result

        time.sleep(cfg["runtime"]["screen_poll_interval_sec"])

    return False, last_img, None


def click_button_when_available(adb, cfg, matcher, button_key, template_name=None, threshold=0.93, timeout_sec=8.0):
    ok, img, result = wait_for_button(
        adb,
        cfg,
        matcher,
        button_key=button_key,
        template_name=template_name,
        threshold=threshold,
        timeout_sec=timeout_sec,
    )
    if not ok:
        return False, None

    x, y = result["center"]
    print(f"[INFO] click {button_key} at ({x}, {y}), score={result['score']:.4f}")
    adb.tap(x, y)
    time.sleep(cfg["runtime"]["tap_delay_sec"])
    return True, result


def get_urgent_recruit_matches(adb, cfg, matcher):
    img = adb.screencap()
    slot_region = abs_region(img, cfg["game"]["regions"]["slot_list"])

    matches = matcher.find_all(
        img,
        template_name="urgent_recruitment",
        threshold=0.93,
        search_region=slot_region,
        max_results=8,
        nms_iou_threshold=0.2,
    )
    matches.sort(key=lambda m: (m["center"][1], m["center"][0]))
    return img, matches


def click_nth_urgent_recruit(adb, cfg, matcher, slot_index=0):
    import time

    img, matches = get_urgent_recruit_matches(adb, cfg, matcher)
    print(f"[INFO] urgent recruit count = {len(matches)}")

    if not matches:
        raise RuntimeError("找不到『緊急徵召』按鈕。")

    if slot_index < 0 or slot_index >= len(matches):
        raise RuntimeError(f"slot_index={slot_index} 超出範圍，只有 {len(matches)} 個緊急徵召按鈕。")

    target = matches[slot_index]
    x, y = target["center"]
    print(f"[INFO] click urgent_recruitment #{slot_index} at ({x}, {y}), score={target['score']:.4f}")
    adb.tap(x, y)
    time.sleep(cfg["runtime"]["tap_delay_sec"])
    return True


def wait_until_no_button(adb, cfg, matcher, button_key, template_name=None, threshold=0.93, timeout_sec=8.0):
    import time

    start = time.time()
    last_img = None
    while time.time() - start < timeout_sec:
        img = adb.screencap()
        last_img = img

        result = find_button_by_cfg(
            img,
            cfg,
            matcher,
            button_key=button_key,
            template_name=template_name,
            threshold=threshold,
        )
        if result is None:
            return True, img

        time.sleep(cfg["runtime"]["screen_poll_interval_sec"])

    return False, last_img

def urgent_recruit_and_sure(adb, cfg, matcher, slot_index=0):
    click_nth_urgent_recruit(adb, cfg, matcher, slot_index=slot_index)

    ok, _ = click_button_when_available(
        adb, cfg, matcher,
        button_key="sure",
        template_name="sure",
        threshold=0.93,
        timeout_sec=6.0,
    )
    if not ok:
        raise RuntimeError("按下『緊急徵召』後，找不到『確定』按鈕。")

    time.sleep(0.8)
    return True


def one_time_admission_skip_close(adb, cfg, matcher):
    ok, _ = click_button_when_available(
        adb, cfg, matcher,
        button_key="one_time_admission",
        template_name="one_time_admission",
        threshold=0.93,
        timeout_sec=8.0,
    )
    if not ok:
        raise RuntimeError("找不到『一鍵錄取』按鈕。")

    ok, _ = click_button_when_available(
        adb, cfg, matcher,
        button_key="skip",
        template_name="skip",
        threshold=0.90,
        timeout_sec=5.0,
    )
    if ok:
        print("[INFO] skip clicked")
    else:
        print("[INFO] skip not found, continue")

    ok, _ = click_button_when_available(
        adb, cfg, matcher,
        button_key="close",
        template_name="close",
        threshold=0.93,
        timeout_sec=6.0,
    )
    if ok:
        print("[INFO] close clicked")
    else:
        print("[INFO] no close found")

    time.sleep(0.8)
    return True
