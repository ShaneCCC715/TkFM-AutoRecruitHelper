# -*- coding: utf-8 -*-
# 注意：
# query_exact() 的輸入必須是英文 canonical tag id。
# 例如：
#   ["dark_attribute", "damage_output", "explosiveness"]
# 不可傳入繁中顯示名：
#   ["闇屬性", "輸出", "爆發力"]
# 繁中僅用於輸出顯示，不用於查詢。

from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, Iterable, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data.tag_aliases import normalize_tag_id, to_zh, tags_to_zh


DATA_DIR = PROJECT_ROOT / "data"
MASTER_CHAR_PATH = DATA_DIR / "master_characters.json"
NONLEADER_DB_PATH = DATA_DIR / "recruit_db_nonleader_exact.json"
LEADER_DB_PATH = DATA_DIR / "recruit_db_leader_exact.json"

LEADER_ID = normalize_tag_id("leader")


def _load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"找不到檔案：{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _unique_preserve_order(tags: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for t in tags:
        norm = normalize_tag_id(t)
        if not norm:
            continue
        if norm in seen:
            continue
        seen.add(norm)
        out.append(norm)
    return out


def _combo_key(combo: Iterable[str]) -> str:
    return "|".join(sorted(combo))


def decimal_percent(num: float) -> str:
    """
    完全照網站 decimalPercent()：
    - >= 100 -> 0 位小數
    - >= 10  -> 1 位小數
    - else   -> 2 位小數
    """
    if num >= 100:
        return f"{num:.0f}"
    elif num >= 10:
        return f"{num:.1f}"
    else:
        return f"{num:.2f}"

def _contains_cjk(text: str) -> bool:
    if not text:
        return False
    for ch in text:
        code = ord(ch)
        if (
            0x4E00 <= code <= 0x9FFF or   # CJK Unified Ideographs
            0x3400 <= code <= 0x4DBF or   # CJK Extension A
            0x3040 <= code <= 0x30FF or   # 日文
            0xAC00 <= code <= 0xD7AF      # 韓文
        ):
            return True
    return False

def _validate_query_input_tags(tags: Iterable[str]) -> None:
    bad_tags = []
    for t in tags:
        s = str(t).strip()
        if not s:
            continue
        if _contains_cjk(s):
            bad_tags.append(s)

    if bad_tags:
        raise ValueError(
            "q.query_exact() 只能使用英文 canonical tag id，不可使用中文/韓文顯示名。\n"
            f"收到的不合法 tags: {bad_tags}\n"
            "正確示例: ['dark_attribute', 'damage_output', 'explosiveness']"
        )

class RecruitQueryExact:
    def __init__(
        self,
        master_char_path: Path | str = MASTER_CHAR_PATH,
        nonleader_db_path: Path | str = NONLEADER_DB_PATH,
        leader_db_path: Path | str = LEADER_DB_PATH,
    ) -> None:
        self.master_char_path = Path(master_char_path)
        self.nonleader_db_path = Path(nonleader_db_path)
        self.leader_db_path = Path(leader_db_path)

        self.characters: List[Dict[str, Any]] = _load_json(self.master_char_path)
        self.nonleader_db: Dict[str, Dict[str, Any]] = _load_json(self.nonleader_db_path)
        self.leader_db: Dict[str, Dict[str, Any]] = _load_json(self.leader_db_path)

        self.char_by_id: Dict[int, Dict[str, Any]] = {int(ch["id"]): ch for ch in self.characters}

    # ------------------------------------------------------------------
    # 基本工具
    # ------------------------------------------------------------------
    def normalize_selected_tags(self, tags: Iterable[str], max_count: int = 5) -> List[str]:
        _validate_query_input_tags(tags)
        normalized = _unique_preserve_order(tags)
        return normalized[:max_count]

    def _tag1(self, tags: List[str]) -> List[List[str]]:
        return [[tags[i]] for i in range(len(tags))]

    def _tag2(self, tags: List[str]) -> List[List[str]]:
        return [[tags[i], tags[j]] for i in range(len(tags)) for j in range(i + 1, len(tags))]

    def _tag3(self, tags: List[str]) -> List[List[str]]:
        return [
            [tags[i], tags[j], tags[k]]
            for i in range(len(tags))
            for j in range(i + 1, len(tags))
            for k in range(j + 1, len(tags))
        ]

    def _character_brief(self, ch_id: int) -> Dict[str, Any]:
        ch = self.char_by_id[int(ch_id)]
        return {
            "id": ch["id"],
            "name_ko": ch.get("name_ko", ""),
            "rarity": ch.get("rarity", ""),
            "tags": ch.get("tags", []),
            "tags_zh": tags_to_zh(ch.get("tags", [])),
        }

    # ------------------------------------------------------------------
    # nonleader：完全照網站邏輯
    # ------------------------------------------------------------------
    def query_nonleader(self, tags: Iterable[str], top_n: int | None = None) -> List[Dict[str, Any]]:
        """
        完全照網站 nonleader 分支：
        - 不含 leader
        - 對目前所選 tag 做 1/2/3 tag 組合
        - 依 sr_percent_exact 由大到小排序
        """
        cur_tags = [t for t in self.normalize_selected_tags(tags) if t != LEADER_ID]

        results: List[Dict[str, Any]] = []

        for combo in self._tag1(cur_tags):
            item = self.nonleader_db.get(_combo_key(combo))
            if item:
                results.append(self._format_nonleader_item(combo, item))

        for combo in self._tag2(cur_tags):
            item = self.nonleader_db.get(_combo_key(combo))
            if item:
                results.append(self._format_nonleader_item(combo, item))

        for combo in self._tag3(cur_tags):
            item = self.nonleader_db.get(_combo_key(combo))
            if item:
                results.append(self._format_nonleader_item(combo, item))

        results.sort(key=lambda x: x["per"], reverse=True)

        if top_n is not None:
            return results[:top_n]
        return results

    def _format_nonleader_item(self, combo: List[str], item: Dict[str, Any]) -> Dict[str, Any]:
        per = float(item.get("sr_percent_exact", 0.0))
        candidate_ids = item.get("candidate_ids", [])

        return {
            "mode": "nonleader",
            "combo": combo,
            "combo_key": _combo_key(combo),
            "combo_zh": tags_to_zh(combo),
            "cur": " ".join(combo),
            "cur_zh": " ".join(tags_to_zh(combo)),
            "per": per,
            "percent_text": f"{decimal_percent(per * 100)}%",
            "sr_count": int(item.get("sr_count", 0)),
            "r_count": int(item.get("r_count", 0)),
            "n_count": int(item.get("n_count", 0)),
            "weighted_total": int(item.get("weighted_total", 0)),
            "pool_size": len(candidate_ids),
            "candidate_ids": candidate_ids,
            "candidates": [self._character_brief(cid) for cid in candidate_ids],
        }

    # ------------------------------------------------------------------
    # leader：完全照網站邏輯
    # ------------------------------------------------------------------
    def query_leader(self, tags: Iterable[str], top_n: int | None = None) -> List[Dict[str, Any]]:
        """
        完全照網站 leader 分支：
        - 若包含 leader，先把 leader 移除
        - 只對剩下 tag 做 1/2 tag 組合
        - 查 SSR
        - 同角色重複出現時，保留較大的 per
        """
        cur_tags = [t for t in self.normalize_selected_tags(tags) if t != LEADER_ID]

        best_by_id: Dict[int, Dict[str, Any]] = {}

        for combo in self._tag1(cur_tags):
            self._accumulate_leader_combo(best_by_id, combo)

        for combo in self._tag2(cur_tags):
            self._accumulate_leader_combo(best_by_id, combo)

        results = list(best_by_id.values())
        results.sort(key=lambda x: x["per"], reverse=True)

        if top_n is not None:
            return results[:top_n]
        return results

    def _accumulate_leader_combo(self, best_by_id: Dict[int, Dict[str, Any]], combo: List[str]) -> None:
        item = self.leader_db.get(_combo_key(combo))
        if not item:
            return

        per = float(item.get("per_each", 0.0))
        candidate_ids = item.get("candidate_ids", [])

        for cid in candidate_ids:
            cid = int(cid)
            current = best_by_id.get(cid)
            candidate = self._character_brief(cid)

            obj = {
                "mode": "leader",
                "id": cid,
                "name_ko": candidate["name_ko"],
                "rarity": candidate["rarity"],
                "tags": candidate["tags"],
                "tags_zh": candidate["tags_zh"],
                "per": per,
                "percent_text": f"{int(per * 100)}%",
                "best_combo": combo,
                "best_combo_key": _combo_key(combo),
                "best_combo_zh": tags_to_zh(combo),
                "cur": " ".join(combo),
                "cur_zh": " ".join(tags_to_zh(combo)),
            }

            if current is None or per > float(current["per"]):
                best_by_id[cid] = obj

    # ------------------------------------------------------------------
    # 自動分流
    # ------------------------------------------------------------------
    def query_exact(self, tags: Iterable[str], top_n: int | None = None) -> Dict[str, Any]:
        normalized = self.normalize_selected_tags(tags)

        if LEADER_ID in normalized:
            return {
                "mode": "leader",
                "selected_tags": normalized,
                "selected_tags_zh": tags_to_zh(normalized),
                "results": self.query_leader(normalized, top_n=top_n),
            }

        return {
            "mode": "nonleader",
            "selected_tags": normalized,
            "selected_tags_zh": tags_to_zh(normalized),
            "results": self.query_nonleader(normalized, top_n=top_n),
        }


def pretty_print_query_result(payload: Dict[str, Any], limit: int = 10) -> None:
    mode = payload["mode"]
    selected_tags = payload.get("selected_tags", [])
    selected_tags_zh = payload.get("selected_tags_zh", [])
    results = payload.get("results", [])

    print("=" * 72)
    print(f"mode = {mode}")
    print(f"selected_tags = {selected_tags}")
    print(f"selected_tags_zh = {selected_tags_zh}")
    print("-" * 72)

    if not results:
        print("No result.")
        return

    for i, item in enumerate(results[:limit], 1):
        if mode == "nonleader":
            print(
                f"[{i}] {item['percent_text']:>8}  "
                f"{item['combo']}  "
                f"(SR={item['sr_count']}, R={item['r_count']}, N={item['n_count']})"
            )
            print(f"     zh = {item['combo_zh']}")
        else:
            print(
                f"[{i}] {item['percent_text']:>8}  "
                f"{item['name_ko']}  "
                f"best_combo={item['best_combo']}"
            )
            print(f"     best_combo_zh = {item['best_combo_zh']}")


if __name__ == "__main__":
    q = RecruitQueryExact()

    # nonleader 範例
    payload = q.query_exact(
        ["암속성", "데미지", "폭발력", "인간", "작은체형"],
        top_n=10,
    )
    pretty_print_query_result(payload, limit=10)

    # leader 範例
    payload = q.query_exact(
        ["리더", "암속성", "폭발력", "데미지"],
        top_n=10,
    )
    pretty_print_query_result(payload, limit=10)