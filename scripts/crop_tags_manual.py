# -*- coding: utf-8 -*-
"""
Created on Thu Apr  2 17:37:39 2026

@author: User
"""
from pathlib import Path
from datetime import datetime
import cv2

from src.config_loader import load_config
from src.adb_controller import ADBController


def fit_scale(width: int, height: int, max_width: int, max_height: int) -> float:
    scale_w = max_width / width
    scale_h = max_height / height
    return min(scale_w, scale_h, 1.0)


def main():
    cfg = load_config()

    adb = ADBController(
        adb_executable=cfg["adb"]["executable"],
        device=cfg["adb"]["device"],
    )
    adb.connect()

    # 1. 擷取當下模擬器畫面
    img = adb.screencap()
    if img is None:
        raise RuntimeError("Failed to capture current BlueStacks screen.")

    h, w = img.shape[:2]
    print(f"Captured current screen: {w}x{h}")

    # 可自行調整 GUI 顯示上限
    max_display_width = 500
    max_display_height = 900

    scale = fit_scale(w, h, max_display_width, max_display_height)
    disp_w = int(w * scale)
    disp_h = int(h * scale)

    if scale < 1.0:
        display_img = cv2.resize(img, (disp_w, disp_h), interpolation=cv2.INTER_AREA)
    else:
        display_img = img.copy()

    window_name = "Select ROI (Enter/Space=confirm, C/Esc=cancel)"

    Path("assets/templates/tags").mkdir(parents=True, exist_ok=True)
    Path("assets/debug").mkdir(parents=True, exist_ok=True)

    # 也順便存一張當下原圖，方便回頭核對
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = f"assets/debug/current_screen_{timestamp}.png"
    cv2.imwrite(raw_path, img)
    print(f"Saved raw screen to: {raw_path}")

    try:
        # 2. 建立可調整大小的視窗
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, disp_w, disp_h)

        # 3. 在縮放後的畫面上選 ROI
        roi_disp = cv2.selectROI(window_name, display_img, showCrosshair=True, fromCenter=False)
        x_d, y_d, w_d, h_d = roi_disp

        if w_d == 0 or h_d == 0:
            print("Selection canceled.")
            return

        # 4. 換回原始座標
        x = int(round(x_d / scale))
        y = int(round(y_d / scale))
        ww = int(round(w_d / scale))
        hh = int(round(h_d / scale))

        # 邊界保護
        x = max(0, min(x, w - 1))
        y = max(0, min(y, h - 1))
        ww = max(1, min(ww, w - x))
        hh = max(1, min(hh, h - y))

        crop = img[y:y + hh, x:x + ww]

        # 5. 輸出檔名
        name = input("請輸入詞條名稱（例如 闇屬性 ）；留空則用時間戳：").strip()
        if not name:
            name = f"tag_{timestamp}"

        out_path = Path("assets/templates/tags") / f"{name}.png"
        cv2.imwrite(str(out_path), crop)
        print(f"Saved cropped tag to: {out_path}")
        print(f"Original ROI = x:{x}, y:{y}, w:{ww}, h:{hh}")

    finally:
        # 6. 確保 GUI 正常關閉
        try:
            cv2.destroyWindow(window_name)
        except cv2.error:
            pass
        cv2.destroyAllWindows()
        cv2.waitKey(1)


if __name__ == "__main__":
    main()