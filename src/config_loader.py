# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def load_config(path: str | Path | None = None):
    """
    載入 YAML 設定檔。

    規則：
    1. 若 path 為 None，預設讀取專案根目錄下的 config.yaml
    2. 若 path 是相對路徑，則相對於專案根目錄解析
    3. 若 path 是絕對路徑，則直接使用
    """
    if path is None:
        config_path = DEFAULT_CONFIG_PATH
    else:
        config_path = Path(path)
        if not config_path.is_absolute():
            config_path = PROJECT_ROOT / config_path

    if not config_path.exists():
        raise FileNotFoundError(f"找不到 config 檔案：{config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)