# -*- coding: utf-8 -*-
"""
Created on Fri Apr  3 00:34:23 2026

@author: User
"""
from src.config_loader import load_config
from src.adb_controller import ADBController
from src.template_matcher import TemplateMatcher
from src.recruit_flow import open_nth_empty_slot, save_slot_matches_debug


def main():
    cfg = load_config()
    adb = ADBController(cfg["adb"]["executable"], cfg["adb"]["device"])
    adb.connect()

    matcher = TemplateMatcher("assets/templates/buttons")

    save_slot_matches_debug(adb, cfg, matcher)
    ok = open_nth_empty_slot(adb, cfg, matcher)
    print("open_first_empty_slot:", ok)


if __name__ == "__main__":
    main()
