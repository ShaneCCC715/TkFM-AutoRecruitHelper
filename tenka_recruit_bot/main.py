# -*- coding: utf-8 -*-
"""
Created on Fri Apr  3 12:09:34 2026

@author: 夏爾克 - shane
"""
import time
from pathlib import Path

from src.config_loader import load_config
from src.adb_controller import ADBController
from src.template_matcher import TemplateMatcher
from src.tag_recognizer import TagRecognizer
from src.recruit_query_exact import RecruitQueryExact
from src.recruit_exact_select import auto_select_best_tags_exact
from src.recruit_guard import GuardStopError

from src.recruit_flow import (
    count_empty_slots_in_image,
    open_nth_empty_slot,
    set_timer_to_9h_by_panel,
    wait_until_recruit_started,
    click_button_when_available,
    urgent_recruit_and_sure,
    one_time_admission_skip_close,
)
from src.state_machine import detect_state, ScreenState

def wait_until_recruit_edit(adb, timeout_sec=8.0, poll_sec=0.6):
    start = time.time()
    while time.time() - start < timeout_sec:
        img = adb.screencap()
        state = detect_state(img)
        if state == ScreenState.RECRUIT_EDIT:
            return True, img
        time.sleep(poll_sec)
    return False, None


def do_one_empty_slot_cycle(adb, cfg, matcher, recognizer, q):
    img0 = adb.screencap()
    empty_count_before, _ = count_empty_slots_in_image(img0, cfg, matcher)
    print(f"[INFO] empty_count_before = {empty_count_before}")

    if empty_count_before <= 0:
        return False

    ok = open_nth_empty_slot(adb, cfg, matcher, slot_index=0)
    if not ok:
        raise RuntimeError("無法進入空的招募欄位。")

    ok, _ = wait_until_recruit_edit(
        adb,
        timeout_sec=8.0,
        poll_sec=cfg["runtime"]["screen_poll_interval_sec"],
    )
    if not ok:
        raise RuntimeError("沒有成功進入招募編輯頁。")

    set_timer_to_9h_by_panel(adb, cfg, matcher)
    time.sleep(0.8)

    auto_select_best_tags_exact(adb, cfg, recognizer, q)

    ok, _ = click_button_when_available(
        adb, cfg, matcher,
        button_key="start_recruit",
        template_name="start_recruit",
        threshold=0.93,
        timeout_sec=6.0,
    )
    if not ok:
        raise RuntimeError("找不到『開始招募』按鈕。")

    ok, _, empty_count_after = wait_until_recruit_started(
        adb,
        cfg,
        matcher,
        empty_count_before=empty_count_before,
        timeout_sec=10.0,
    )
    if not ok:
        raise RuntimeError("開始招募後，沒有成功回到主列表或空欄數未減少。")

    print(f"[INFO] recruit started, empty_count_after = {empty_count_after}")

    urgent_recruit_and_sure(adb, cfg, matcher, slot_index=0)
    return True


def run_single_full_cycle(adb, cfg, matcher, recognizer, q):
    filled_count = 0

    while True:
        img = adb.screencap()
        empty_count, _ = count_empty_slots_in_image(img, cfg, matcher)
        print(f"[LOOP] current empty_count = {empty_count}")

        if empty_count <= 0:
            break

        ok = do_one_empty_slot_cycle(adb, cfg, matcher, recognizer, q)
        if not ok:
            break

        filled_count += 1
        print(f"[LOOP] filled_count = {filled_count}")

    print("[INFO] no empty slot left, run one_time_admission flow once")
    one_time_admission_skip_close(adb, cfg, matcher)

    return {
        "filled_count": filled_count,
    }


def run_full_auto_batches(adb, cfg, matcher, recognizer, q, max_rounds):
    completed_rounds = 0

    for round_idx in range(1, max_rounds + 1):
        print("=" * 60)
        print(f"[BATCH] round {round_idx}/{max_rounds} start")

        try:
            summary = run_single_full_cycle(adb, cfg, matcher, recognizer, q)
            completed_rounds += 1
            print(
                f"[BATCH] round {round_idx} completed, "
                f"filled_count={summary['filled_count']}"
            )
        except GuardStopError as e:
            print(f"[STOP] guard triggered at round {round_idx}: {e}")
            break
        except Exception as e:
            print(f"[STOP] runtime error at round {round_idx}: {e}")
            break

    print("=" * 60)
    print(
        f"[DONE] completed_rounds={completed_rounds}, "
        f"requested_rounds={max_rounds}"
    )

    return {
        "completed_rounds": completed_rounds,
        "requested_rounds": max_rounds,
    }


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
        threshold=0.90,
    )
    q = RecruitQueryExact()

    Path("assets/debug").mkdir(parents=True, exist_ok=True)

    max_rounds = int(cfg.get("runtime", {}).get("max_auto_rounds", 1))
    summary = run_full_auto_batches(
        adb=adb,
        cfg=cfg,
        matcher=matcher,
        recognizer=recognizer,
        q=q,
        max_rounds=max_rounds,
    )

    print(f"[SUCCESS] full auto recruit cycle finished: {summary}")


if __name__ == "__main__":
    main()
