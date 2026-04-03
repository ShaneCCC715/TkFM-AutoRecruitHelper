# -*- coding: utf-8 -*-
"""
Created on Thu Apr  2 16:23:57 2026

@author: User
"""
import subprocess
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np


class ADBController:
    def __init__(self, adb_executable: str = "adb", device: Optional[str] = None):
        self.adb = adb_executable
        self.device = device

    def _base_cmd(self):
        cmd = [self.adb]
        if self.device:
            cmd += ["-s", self.device]
        return cmd

    def connect(self):
        if self.device:
            subprocess.run([self.adb, "connect", self.device], check=False)

    def shell(self, command: str):
        full_cmd = self._base_cmd() + ["shell", command]
        return subprocess.run(full_cmd, check=True, capture_output=True)

    def tap(self, x: int, y: int):
        self.shell(f"input tap {x} {y}")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
        self.shell(f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")

    def keyevent(self, keycode: int):
        self.shell(f"input keyevent {keycode}")

    def back(self):
        self.keyevent(4)

    def screencap(self) -> np.ndarray:
        cmd = self._base_cmd() + ["exec-out", "screencap", "-p"]
        result = subprocess.run(cmd, check=True, capture_output=True)
        data = np.frombuffer(result.stdout, dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if img is None:
            raise RuntimeError("Failed to decode screenshot from adb.")
        return img

    def save_debug_screen(self, img: np.ndarray, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(path, img)

    def wait_until(self, condition_fn, timeout_sec: float = 10.0, poll_sec: float = 0.8):
        start = time.time()
        while time.time() - start < timeout_sec:
            img = self.screencap()
            if condition_fn(img):
                return True
            time.sleep(poll_sec)
        return False