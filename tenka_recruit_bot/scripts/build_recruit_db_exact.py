# -*- coding: utf-8 -*-
"""
Created on Fri Apr  3 10:36:11 2026

@author: User
"""
from __future__ import annotations

import json
import re
import sys
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Iterable

# 以這支檔案的位置反推專案根目錄
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 讓 from data... / from src... 可以正常 import
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data.tag_aliases import normalize_tag_id

# 這裡放網站 33 個 tag（韓文），順序照頁面
WEBSITE_TAGS_KO = [
    "화속성", "수속성", "풍속성", "광속성", "암속성",
    "딜러", "힐러", "탱커", "서포터", "디스럽터",
    "인간", "마족", "야인",
    "작은체형", "표준체형",
    "빈유", "미유", "거유",
    "병사", "정예", "리더",
    "방어", "방해", "데미지", "보호", "회복", "지원", "쇠약",
    "폭발력", "생존력", "전투", "범위공격", "반격",
]

LEADER_ID = normalize_tag_id("리더")


def parse_recruit_js(js_text: str) -> List[dict]:
    """
    從 recruit.js 文字中抽出 recruitJson.data。
    """
    pattern = re.compile(
        r'\{id:(\d+),\s*cur:"[^"]*",\s*per:[^,]*,\s*name:"([^"]+)",\s*rarity:"([^"]+)",\s*tags:"([^"]*)"\}',
        re.UNICODE,
    )

    chars: List[dict] = []
    for m in pattern.finditer(js_text):
        ch_id = int(m.group(1))
        name_ko = m.group(2)
        rarity = m.group(3)
        tags_ko = [x for x in m.group(4).split(" ") if x.strip()]
        tags = [normalize_tag_id(t) for t in tags_ko]

        chars.append(
            {
                "id": ch_id,
                "name_ko": name_ko,
                "rarity": rarity,
                "tags_ko": tags_ko,
                "tags": tags,
            }
        )
    return chars


def combo_key(tags: Iterable[str]) -> str:
    return "|".join(sorted(tags))


def matches_all_tags(ch: dict, combo: Iterable[str]) -> bool:
    tagset = set(ch["tags"])
    return all(tag in tagset for tag in combo)


def build_nonleader_exact_db(characters: List[dict]) -> Dict[str, dict]:
    """
    完全照網站 non-leader 邏輯：
    - 只看非 SSR
    - 對 1,2,3 tag combo 計算
    - per = SR / (SR + 10*R + 30*N)
    """
    all_tags = [normalize_tag_id(t) for t in WEBSITE_TAGS_KO]
    all_tags = sorted(set(t for t in all_tags if t and t != LEADER_ID))

    db: Dict[str, dict] = {}

    for k in (1, 2, 3):
        for combo in combinations(all_tags, k):
            matched = [
                ch for ch in characters
                if ch["rarity"] != "SSR" and matches_all_tags(ch, combo)
            ]
            if not matched:
                continue

            sr_count = sum(1 for ch in matched if ch["rarity"] == "SR")
            r_count = sum(1 for ch in matched if ch["rarity"] == "R")
            n_count = sum(1 for ch in matched if ch["rarity"] == "N")

            weighted_total = sr_count + 10 * r_count + 30 * n_count
            per = (sr_count / weighted_total) if weighted_total > 0 else 0.0

            key = combo_key(combo)
            db[key] = {
                "combo": list(combo),
                "mode": "nonleader",
                "sr_percent_exact": per,
                "sr_count": sr_count,
                "r_count": r_count,
                "n_count": n_count,
                "weighted_total": weighted_total,
                "candidate_ids": [ch["id"] for ch in matched],
            }

    return db


def build_leader_exact_db(characters: List[dict]) -> Dict[str, dict]:
    """
    完全照網站 leader 邏輯的 combo-level 快取：
    - leader 自身不放進 combo key
    - 只對 1,2 tag combo 建表
    - 只看 SSR
    - 每個 combo 內的每位 SSR 角色 per = 1 / len(matched)
    """
    all_tags = [normalize_tag_id(t) for t in WEBSITE_TAGS_KO]
    all_tags = sorted(set(t for t in all_tags if t and t != LEADER_ID))

    db: Dict[str, dict] = {}

    for k in (1, 2):
        for combo in combinations(all_tags, k):
            matched = [
                ch for ch in characters
                if ch["rarity"] == "SSR" and matches_all_tags(ch, combo)
            ]
            if not matched:
                continue

            pool_size = len(matched)
            per_each = 1.0 / pool_size

            key = combo_key(combo)
            db[key] = {
                "combo": list(combo),
                "mode": "leader",
                "pool_size": pool_size,
                "per_each": per_each,
                "candidate_ids": [ch["id"] for ch in matched],
            }

    return db


def main():
    src_path = PROJECT_ROOT / "data" / "raw" / "recruit_site_source.txt"
    out_dir = PROJECT_ROOT / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    js_text = src_path.read_text(encoding="utf-8")
    characters = parse_recruit_js(js_text)

    (out_dir / "master_characters.json").write_text(
        json.dumps(characters, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    nonleader_db = build_nonleader_exact_db(characters)
    leader_db = build_leader_exact_db(characters)

    (out_dir / "recruit_db_nonleader_exact.json").write_text(
        json.dumps(nonleader_db, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "recruit_db_leader_exact.json").write_text(
        json.dumps(leader_db, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"characters = {len(characters)}")
    print(f"nonleader combos = {len(nonleader_db)}")
    print(f"leader combos = {len(leader_db)}")
    print("done.")


if __name__ == "__main__":
    main()
