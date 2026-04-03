# -*- coding: utf-8 -*-
"""
Created on Thu Apr  2 16:24:58 2026

@author: User
"""
from enum import Enum, auto
import cv2
import numpy as np


class ScreenState(Enum):
    MAIN_LIST = auto()
    RECRUIT_EDIT = auto()
    COUNTDOWN_ACTIVE = auto()
    UNKNOWN = auto()


def _has_large_white_slots(img: np.ndarray) -> bool:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY)
    white_ratio = th.mean() / 255.0
    return white_ratio > 0.25


def _has_purple_panels(img: np.ndarray) -> bool:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower = np.array([120, 40, 40])
    upper = np.array([165, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)
    ratio = mask.mean() / 255.0
    return ratio > 0.08


def _has_timer_like_layout(img: np.ndarray) -> bool:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # 粗糙判定，有大量白底與大號數字區
    return gray.mean() > 140


def detect_state(img: np.ndarray) -> ScreenState:
    if _has_large_white_slots(img) and not _has_purple_panels(img):
        return ScreenState.MAIN_LIST

    if _has_purple_panels(img):
        return ScreenState.RECRUIT_EDIT

    if _has_timer_like_layout(img):
        return ScreenState.COUNTDOWN_ACTIVE

    return ScreenState.UNKNOWN
