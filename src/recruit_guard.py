# -*- coding: utf-8 -*-
"""
自動招募流程的 guard / gatekeeper。

規格
----
1. SSR 只會在 leader 詞條出現。
2. 只要偵測到 leader，就不得自動繼續，必須停止。
3. 只有在「5 個詞條都成功判定，且不含 leader」時，才允許自動選 tag 並往下招募。
4. 若有未知詞條、數量不是 5、或含 leader，皆回傳 ok=False。
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, List, Dict, Any

# 允許直接執行 src/recruit_guard.py 時，自動把專案根目錄加進 sys.path
try:
    from data.tag_aliases import (
        normalize_tag_id,
        to_zh,
        tags_to_zh,
        is_known_tag,
        has_auto_block_tag,
    )
except ModuleNotFoundError:
    import sys
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from data.tag_aliases import (
        normalize_tag_id,
        to_zh,
        tags_to_zh,
        is_known_tag,
        has_auto_block_tag,
    )


# 停止原因常數
REASON_OK = "ok"
REASON_NO_TAGS = "no_tags_detected"
REASON_UNKNOWN_TAGS = "unknown_tags_detected"
REASON_TAG_COUNT_NOT_5 = "tag_count_not_5"
REASON_LEADER_DETECTED = "leader_detected"


class GuardStopError(RuntimeError):
    """Guard 判定要求停止自動流程。"""


@dataclass
class GuardResult:
    ok: bool
    reason: str

    expected_count: int
    raw_tags: List[str]
    normalized_tags: List[str]
    zh_tags: List[str]

    unknown_raw_tags: List[str]
    unknown_normalized_tags: List[str]
    block_tags: List[str]

    recognized_count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _clean_raw_tags(raw_tags: Iterable[str]) -> List[str]:
    cleaned: List[str] = []
    for t in raw_tags or []:
        if t is None:
            continue
        s = str(t).strip()
        if not s:
            continue
        cleaned.append(s)
    return cleaned


def evaluate_auto_recruit_guard(
    raw_tags: Iterable[str],
    expected_count: int = 5,
) -> Dict[str, Any]:
    raw_clean = _clean_raw_tags(raw_tags)

    if not raw_clean:
        result = GuardResult(
            ok=False,
            reason=REASON_NO_TAGS,
            expected_count=expected_count,
            raw_tags=[],
            normalized_tags=[],
            zh_tags=[],
            unknown_raw_tags=[],
            unknown_normalized_tags=[],
            block_tags=[],
            recognized_count=0,
        )
        return result.to_dict()

    normalized_known: List[str] = []
    unknown_raw: List[str] = []
    unknown_norm: List[str] = []

    for raw in raw_clean:
        norm = normalize_tag_id(raw)
        if is_known_tag(norm):
            normalized_known.append(norm)
        else:
            unknown_raw.append(raw)
            unknown_norm.append(norm)

    if unknown_raw:
        result = GuardResult(
            ok=False,
            reason=REASON_UNKNOWN_TAGS,
            expected_count=expected_count,
            raw_tags=raw_clean,
            normalized_tags=normalized_known,
            zh_tags=tags_to_zh(normalized_known),
            unknown_raw_tags=unknown_raw,
            unknown_normalized_tags=unknown_norm,
            block_tags=[],
            recognized_count=len(normalized_known),
        )
        return result.to_dict()

    if len(normalized_known) != expected_count:
        result = GuardResult(
            ok=False,
            reason=REASON_TAG_COUNT_NOT_5,
            expected_count=expected_count,
            raw_tags=raw_clean,
            normalized_tags=normalized_known,
            zh_tags=tags_to_zh(normalized_known),
            unknown_raw_tags=[],
            unknown_normalized_tags=[],
            block_tags=[],
            recognized_count=len(normalized_known),
        )
        return result.to_dict()

    block_tags = sorted(
        {normalize_tag_id(t) for t in normalized_known if has_auto_block_tag([t])}
    )

    if block_tags:
        result = GuardResult(
            ok=False,
            reason=REASON_LEADER_DETECTED,
            expected_count=expected_count,
            raw_tags=raw_clean,
            normalized_tags=normalized_known,
            zh_tags=tags_to_zh(normalized_known),
            unknown_raw_tags=[],
            unknown_normalized_tags=[],
            block_tags=block_tags,
            recognized_count=len(normalized_known),
        )
        return result.to_dict()

    result = GuardResult(
        ok=True,
        reason=REASON_OK,
        expected_count=expected_count,
        raw_tags=raw_clean,
        normalized_tags=normalized_known,
        zh_tags=tags_to_zh(normalized_known),
        unknown_raw_tags=[],
        unknown_normalized_tags=[],
        block_tags=[],
        recognized_count=len(normalized_known),
    )
    return result.to_dict()


def format_guard_report(result: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("[RecruitGuard]")
    lines.append(f"ok = {result.get('ok')}")
    lines.append(f"reason = {result.get('reason')}")
    lines.append(
        f"recognized = {result.get('recognized_count', 0)}/{result.get('expected_count', 5)}"
    )

    raw_tags = result.get("raw_tags", []) or []
    normalized_tags = result.get("normalized_tags", []) or []
    zh_tags = result.get("zh_tags", []) or []
    unknown_raw = result.get("unknown_raw_tags", []) or []
    unknown_norm = result.get("unknown_normalized_tags", []) or []
    block_tags = result.get("block_tags", []) or []

    if raw_tags:
        lines.append(f"raw_tags = {raw_tags}")
    if normalized_tags:
        lines.append(f"normalized_tags = {normalized_tags}")
    if zh_tags:
        lines.append(f"zh_tags = {zh_tags}")
    if unknown_raw:
        lines.append(f"unknown_raw_tags = {unknown_raw}")
    if unknown_norm:
        lines.append(f"unknown_normalized_tags = {unknown_norm}")
    if block_tags:
        lines.append(f"block_tags = {block_tags} -> {[to_zh(t) for t in block_tags]}")

    return "\n".join(lines)


def assert_auto_recruit_allowed(
    raw_tags: Iterable[str],
    expected_count: int = 5,
) -> Dict[str, Any]:
    result = evaluate_auto_recruit_guard(raw_tags, expected_count=expected_count)
    if not result["ok"]:
        raise GuardStopError(format_guard_report(result))
    return result


if __name__ == "__main__":
    samples = [
        ["fire_attribute", "human", "small_size", "defense", "survivability"],
        ["fire_attribute", "human", "small_size", "leader", "survivability"],
        ["fire_attribute", "human", "small_size", "UNKNOWN_TAG", "survivability"],
        ["fire_attribute", "human", "small_size"],
        ["화속성", "인간", "작은체형", "방어", "생존력"],
    ]

    for i, sample in enumerate(samples, 1):
        print("=" * 60)
        print(f"sample #{i}: {sample}")
        res = evaluate_auto_recruit_guard(sample)
        print(format_guard_report(res))