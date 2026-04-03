# -*- coding: utf-8 -*-
"""
Created on Thu Apr  2 16:24:46 2026

@author: User
"""
from typing import Dict, Tuple
import numpy as np


def ratio_to_abs(img: np.ndarray, x_ratio: float, y_ratio: float) -> Tuple[int, int]:
    h, w = img.shape[:2]
    return int(w * x_ratio), int(h * y_ratio)


def region_from_ratio(img: np.ndarray, region_cfg: Dict[str, float]) -> np.ndarray:
    h, w = img.shape[:2]
    x1 = int(w * region_cfg["x1"])
    y1 = int(h * region_cfg["y1"])
    x2 = int(w * region_cfg["x2"])
    y2 = int(h * region_cfg["y2"])
    return img[y1:y2, x1:x2].copy()


def abs_region(img: np.ndarray, region_cfg: Dict[str, float]) -> Tuple[int, int, int, int]:
    h, w = img.shape[:2]
    x1 = int(w * region_cfg["x1"])
    y1 = int(h * region_cfg["y1"])
    x2 = int(w * region_cfg["x2"])
    y2 = int(h * region_cfg["y2"])
    return x1, y1, x2, y2

def centered_search_region(img: np.ndarray, button_cfg: Dict[str, float]) -> Tuple[int, int, int, int]:
    h, w = img.shape[:2]

    cx = int(w * button_cfg["x"])
    cy = int(h * button_cfg["y"])

    half_w = int(w * button_cfg.get("search_half_width", 0.15))
    half_h = int(h * button_cfg.get("search_half_height", 0.06))

    x1 = max(0, cx - half_w)
    y1 = max(0, cy - half_h)
    x2 = min(w, cx + half_w)
    y2 = min(h, cy + half_h)

    return x1, y1, x2, y2