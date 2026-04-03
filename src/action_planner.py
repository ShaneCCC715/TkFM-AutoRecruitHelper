# -*- coding: utf-8 -*-
"""
Created on Thu Apr  2 16:25:28 2026

@author: User
"""
import time
from typing import List

from .screen_locator import ratio_to_abs


class ActionPlanner:
    def __init__(self, adb, config: dict, tag_recognizer):
        self.adb = adb
        self.config = config
        self.tag_recognizer = tag_recognizer
        self.tap_delay = config["runtime"]["tap_delay_sec"]

    def set_timer_1_hour(self, img):
        # 這裡先不做真正的加減按鈕控制
        # 因為你截圖裡現在就是 01:00:00
        # 之後可補成真正調整器
        return

    def tap_button(self, img, button_cfg: dict):
        x, y = ratio_to_abs(img, button_cfg["x"], button_cfg["y"])
        self.adb.tap(x, y)
        time.sleep(self.tap_delay)

    def select_tags(self, img, tags_region_cfg: dict, tags: List[str]):
        positions = self.tag_recognizer.find_tag_positions(img, tags_region_cfg, tags)
        for tag in tags:
            if tag not in positions:
                continue
            x, y = positions[tag]
            self.adb.tap(x, y)
            time.sleep(self.tap_delay)

    def start_recruit(self, img):
        self.tap_button(img, self.config["game"]["buttons"]["start_recruit"])

    def go_back(self):
        self.adb.back()
        time.sleep(self.tap_delay)
