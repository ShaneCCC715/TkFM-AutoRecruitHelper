# -*- coding: utf-8 -*-
"""
Created on Thu Apr  2 16:25:08 2026

@author: User
"""
from pathlib import Path
from typing import List, Dict, Tuple

import cv2
import numpy as np

from .screen_locator import abs_region


class TagRecognizer:
    def __init__(self, template_dir: str = "assets/templates/tags", threshold: float = 0.82):
        self.template_dir = Path(template_dir)
        self.threshold = threshold
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, np.ndarray]:
        templates = {}
        if not self.template_dir.exists():
            return templates

        for p in self.template_dir.glob("*.png"):
            img = cv2.imread(str(p), cv2.IMREAD_COLOR)
            if img is not None:
                templates[p.stem] = img
        return templates

    def recognize_available_tags(self, full_img: np.ndarray, region_cfg: dict) -> List[str]:
        x1, y1, x2, y2 = abs_region(full_img, region_cfg)
        region = full_img[y1:y2, x1:x2].copy()

        found: List[str] = []
        for name, template in self.templates.items():
            res = cv2.matchTemplate(region, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            if max_val >= self.threshold:
                found.append(name)

        return sorted(set(found))

    def find_tag_positions(self, full_img: np.ndarray, region_cfg: dict, tags: List[str]) -> Dict[str, Tuple[int, int]]:
        x1, y1, x2, y2 = abs_region(full_img, region_cfg)
        region = full_img[y1:y2, x1:x2].copy()

        positions = {}
        for tag in tags:
            template = self.templates.get(tag)
            if template is None:
                continue

            res = cv2.matchTemplate(region, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            if max_val >= self.threshold:
                th, tw = template.shape[:2]
                cx = x1 + max_loc[0] + tw // 2
                cy = y1 + max_loc[1] + th // 2
                positions[tag] = (cx, cy)

        return positions
    
    def recognize_available_tags_adaptive(
        self,
        image,
        region_cfg,
        expected_count=5,
        default_threshold=0.95,
        min_threshold=0.90,
        max_threshold=0.99,
        step=0.01,
        max_rounds=10,
    ):
        """
        依照辨識到的 tag 數量，自動微調 threshold：
        - count > expected_count -> 收嚴
        - count < expected_count -> 放寬
        - count == expected_count -> 接受
    
        回傳:
            {
                "tags": [...],
                "threshold": 0.93,
                "rounds": [...],
                "ok": True/False,
            }
        """
        original_threshold = getattr(self, "threshold", default_threshold)
        current_threshold = float(default_threshold)
    
        rounds = []
        best_tags = []
        best_threshold = current_threshold
        best_gap = 10**9
    
        try:
            for _ in range(max_rounds):
                self.threshold = current_threshold
                tags = self.recognize_available_tags(image, region_cfg)
                count = len(tags)
    
                rounds.append({
                    "threshold": round(current_threshold, 4),
                    "count": count,
                    "tags": list(tags),
                })
    
                gap = abs(count - expected_count)
                if gap < best_gap:
                    best_gap = gap
                    best_tags = list(tags)
                    best_threshold = current_threshold
    
                if count == expected_count:
                    return {
                        "tags": list(tags),
                        "threshold": round(current_threshold, 4),
                        "rounds": rounds,
                        "ok": True,
                    }
    
                if count > expected_count:
                    next_threshold = round(current_threshold + step, 4)
                    if next_threshold > max_threshold:
                        break
                    current_threshold = next_threshold
                else:
                    next_threshold = round(current_threshold - step, 4)
                    if next_threshold < min_threshold:
                        break
                    current_threshold = next_threshold
    
            return {
                "tags": best_tags,
                "threshold": round(best_threshold, 4),
                "rounds": rounds,
                "ok": (len(best_tags) == expected_count),
            }
    
        finally:
            self.threshold = original_threshold