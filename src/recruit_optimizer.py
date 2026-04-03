# -*- coding: utf-8 -*-
"""
Created on Thu Apr  2 16:25:19 2026

@author: User
"""
from itertools import combinations
from pathlib import Path
import json

from data.tag_aliases import normalize_tag_id


class RecruitOptimizer:
    def __init__(self, combo_score_path: str = "data/recruit_combo_scores.json"):
        self.combo_score_path = Path(combo_score_path)
        self.combo_scores = self._load_combo_scores()

        # 這裡只是暫時讓流程能跑，不代表真實最佳率
        self.fallback_tag_priority = {
            "dark_attribute": 2.0,
            "wind_attribute": 1.6,
            "mass_attack": 1.8,
            "output": 1.7,
            "defense": 1.2,
            "protect": 1.0,
            "reply": 1.1,
            "obstacles": 1.3,
            "fight_stronger": 1.4,
            "guardians": 1.0,
            "medium_size": 0.7,
            "small_size": 0.7,
            "beautiful_breasts": 0.6,
            "small_breasts": 0.6,
        }

    def _combo_key(self, combo):
        normalized = [normalize_tag_id(t) for t in combo]
        return "|".join(sorted(normalized))

    def _load_combo_scores(self):
        if not self.combo_score_path.exists():
            return {}

        data = json.loads(self.combo_score_path.read_text(encoding="utf-8"))
        normalized_data = {}

        for key, value in data.items():
            parts = [normalize_tag_id(x) for x in key.split("|") if x.strip()]
            norm_key = "|".join(sorted(parts))
            normalized_data[norm_key] = value

        return normalized_data

    def score_combo(self, combo):
        key = self._combo_key(combo)
        entry = self.combo_scores.get(key)

        if entry is not None:
            if isinstance(entry, (int, float)):
                return float(entry)

            if isinstance(entry, dict):
                if "score" in entry:
                    return float(entry["score"])

                ssr = float(entry.get("SSR", 0.0))
                sr = float(entry.get("SR", 0.0))
                r = float(entry.get("R", 0.0))
                return ssr * 100.0 + sr * 10.0 + r

        # fallback：讓整條流程可先測通
        score = 0.0
        for t in combo:
            score += self.fallback_tag_priority.get(normalize_tag_id(t), 0.1)

        # 稍微鼓勵多選到 3 個
        score += 0.05 * len(combo)
        return score

    def pick_best_combo(self, available_tags, max_select: int = 3):
        available = sorted({normalize_tag_id(t) for t in available_tags})
        if not available:
            return [], -1.0

        best_combo = []
        best_score = -1.0

        n = min(max_select, len(available))
        for r in range(1, n + 1):
            for combo in combinations(available, r):
                score = self.score_combo(combo)
                if score > best_score:
                    best_combo = list(combo)
                    best_score = score

        return best_combo, best_score