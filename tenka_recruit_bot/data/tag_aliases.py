# -*- coding: utf-8 -*-
"""
Tag aliases / normalization / zh-TW display names.

新版規則
--------
1. 內部 canonical tag id 一律使用新版命名。
2. TAG_ALIASES 不再保留舊英文 alias，只保留 canonical self alias。
3. normalize_tag_id() 只接受：
   - canonical tag id
   - 韓文 tag（若有使用 KO_TAG_TO_ID）
   - 大小寫 / 空白 / 連字號的輕量格式正規化
4. leader 為特殊阻擋詞條：若偵測到 leader，應由流程上層直接停止自動招募。

注意
----
這版已正式使用：
- aoe            （舊版可能是 AoE）
- interference   （舊版可能是 interfence）

若其他模組、資料庫、測試腳本仍使用舊 key，請一併更新。
"""

from typing import Iterable, List


# ----------------------------------------------------------------------
# 1) Canonical tag id -> 繁體中文
#    以新版命名為準。
# ----------------------------------------------------------------------
TAG_ID_TO_ZH = {
    # 屬性（5）
    "fire_attribute": "火屬性",
    "water_attribute": "水屬性",
    "wind_attribute": "風屬性",
    "light_attribute": "光屬性",
    "dark_attribute": "闇屬性",

    # 職能（5）
    "attacker": "攻擊者",
    "healer": "治療者",
    "protector": "守護者",
    "supporter": "輔助者",
    "obstructer": "妨礙者",

    # 種族（3）
    "human": "人類",
    "demon": "魔族",
    "demihuman": "亞人",

    # 體型（2）
    "small_size": "小體型",
    "medium_size": "中體型",

    # 胸型（3）
    "flat_tits": "貧乳",
    "hot_tits": "美乳",
    "giant_tits": "巨乳",

    # 階級（3）
    "soldier": "士兵",
    "elite": "菁英",
    "leader": "領袖",

    # 功能（7）
    "defense": "防禦",
    "interference": "干擾",
    "damage_output": "輸出",
    "protection": "保護",
    "recovery": "回復",
    "support": "支援",
    "weaken": "削弱",

    # 戰鬥特性（5）
    "explosiveness": "爆發力",
    "survivability": "生存力",
    "fight_stronger": "越戰越強",
    "aoe": "群體攻擊",
    "counterstrike": "回擊",
}


# ----------------------------------------------------------------------
# 2) Canonical tag id -> 類別
# ----------------------------------------------------------------------
TAG_ID_TO_CATEGORY = {
    # 屬性
    "fire_attribute": "attribute",
    "water_attribute": "attribute",
    "wind_attribute": "attribute",
    "light_attribute": "attribute",
    "dark_attribute": "attribute",

    # 職能
    "attacker": "role",
    "healer": "role",
    "protector": "role",
    "supporter": "role",
    "obstructer": "role",

    # 種族
    "human": "race",
    "demon": "race",
    "demihuman": "race",

    # 體型
    "small_size": "body",
    "medium_size": "body",

    # 胸型
    "flat_tits": "chest",
    "hot_tits": "chest",
    "giant_tits": "chest",

    # 階級
    "soldier": "rank",
    "elite": "rank",
    "leader": "rank",

    # 功能
    "defense": "function",
    "interference": "function",
    "damage_output": "function",
    "protection": "function",
    "recovery": "function",
    "support": "function",
    "weaken": "function",

    # 戰鬥特性
    "explosiveness": "combat",
    "survivability": "combat",
    "fight_stronger": "combat",
    "aoe": "combat",
    "counterstrike": "combat",
}


# ----------------------------------------------------------------------
# 3) 韓文 -> canonical id
#    若你仍需接 tenkaassist 或其他韓文來源，可保留。
#    這不是舊英文 alias；只是外部資料對照。
# ----------------------------------------------------------------------
KO_TAG_TO_ID = {
    # 屬性
    "화속성": "fire_attribute",
    "수속성": "water_attribute",
    "풍속성": "wind_attribute",
    "광속성": "light_attribute",
    "암속성": "dark_attribute",

    # 職能
    "딜러": "attacker",
    "힐러": "healer",
    "탱커": "protector",
    "서포터": "supporter",
    "디스럽터": "obstructer",

    # 種族
    "인간": "human",
    "마족": "demon",
    "야인": "demihuman",

    # 體型
    "작은체형": "small_size",
    "표준체형": "medium_size",

    # 胸型
    "빈유": "flat_tits",
    "미유": "hot_tits",
    "거유": "giant_tits",

    # 階級
    "병사": "soldier",
    "정예": "elite",
    "리더": "leader",

    # 功能
    "방어": "defense",
    "방해": "interference",
    "데미지": "damage_output",
    "보호": "protection",
    "회복": "recovery",
    "지원": "support",
    "쇠약": "weaken",

    # 戰鬥特性
    "폭발력": "explosiveness",
    "생존력": "survivability",
    "전투": "fight_stronger",
    "범위공격": "aoe",
    "반격": "counterstrike",
}


# ----------------------------------------------------------------------
# 4) TAG_ALIASES
#    不再保留任何舊英文命名，只保留 canonical self alias。
# ----------------------------------------------------------------------
TAG_ALIASES = {
    **{k: k for k in TAG_ID_TO_ZH.keys()},
}


ZH_TO_TAG_ID = {v: k for k, v in TAG_ID_TO_ZH.items()}

# 自動流程遇到這些 tag 時應停止
AUTO_BLOCK_TAGS = {"leader"}


def normalize_tag_id(tag_id: str) -> str:
    """
    把輸入字串正規化成 canonical tag id。

    支援：
    - canonical key
    - 韓文 tag（透過 KO_TAG_TO_ID）
    - 大小寫 / 空白 / 連字號 / 底線的輕量格式正規化

    不再支援：
    - 舊英文 alias（例如 fire / guardian / damage / AoE / interfence 等）
    """
    if tag_id is None:
        return ""

    t = str(tag_id).strip()
    if not t:
        return ""

    # 1) canonical 精確匹配
    if t in TAG_ID_TO_ZH:
        return t

    # 2) 韓文精確匹配
    if t in KO_TAG_TO_ID:
        return KO_TAG_TO_ID[t]

    # 3) 輕量格式正規化
    t2 = t.lower().replace("-", "_").replace(" ", "_")

    if t2 in TAG_ID_TO_ZH:
        return t2

    # 注意：這裡不再查舊英文 alias
    return t2


def to_zh(tag_id: str) -> str:
    """tag id -> 繁中名稱；若查不到就回傳正規化後的 id。"""
    t = normalize_tag_id(tag_id)
    return TAG_ID_TO_ZH.get(t, t)


def tags_to_zh(tag_ids: Iterable[str]) -> List[str]:
    """批次轉成繁中。"""
    return [to_zh(t) for t in tag_ids]


def is_known_tag(tag_id: str) -> bool:
    """是否為已知 tag。"""
    t = normalize_tag_id(tag_id)
    return t in TAG_ID_TO_ZH


def get_tag_category(tag_id: str) -> str:
    """取得 tag 類別；未知則回空字串。"""
    t = normalize_tag_id(tag_id)
    return TAG_ID_TO_CATEGORY.get(t, "")


def has_auto_block_tag(tag_ids: Iterable[str]) -> bool:
    """是否包含需要停止自動流程的詞條（目前為 leader）。"""
    normalized = {normalize_tag_id(t) for t in tag_ids}
    return any(t in AUTO_BLOCK_TAGS for t in normalized)


def has_duplicate_category(tag_ids: Iterable[str]) -> bool:
    """
    檢查一組 tags 是否有重複類別。
    同一類通常不應重複取。
    """
    seen = set()
    for t in tag_ids:
        cat = get_tag_category(t)
        if not cat:
            continue
        if cat in seen:
            return True
        seen.add(cat)
    return False