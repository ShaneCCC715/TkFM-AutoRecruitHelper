# -*- coding: utf-8 -*-
"""
Created on Fri Apr  3 01:25:06 2026

@author: User
"""
from src.config_loader import load_config
from src.adb_controller import ADBController
from src.template_matcher import TemplateMatcher
from src.recruit_flow import urgent_recruit_and_one_time_admission


def main():
    cfg = load_config()
    adb = ADBController(cfg["adb"]["executable"], cfg["adb"]["device"])
    adb.connect()

    matcher = TemplateMatcher("assets/templates/buttons")

    ok = urgent_recruit_and_one_time_admission(
        adb,
        cfg,
        matcher,
        slot_index=0,   # 第 0 個緊急徵召
    )
    print("urgent_recruit_and_one_time_admission:", ok)


if __name__ == "__main__":
    main()
