from pathlib import Path
from typing import Optional, Tuple, List

import cv2
import numpy as np


def load_image_unicode(path: Path, flags=cv2.IMREAD_COLOR):
    data = np.fromfile(str(path), dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, flags)


def _iou(box1, box2) -> float:
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2

    xa = max(x1, x2)
    ya = max(y1, y2)
    xb = min(x1 + w1, x2 + w2)
    yb = min(y1 + h1, y2 + h2)

    inter_w = max(0, xb - xa)
    inter_h = max(0, yb - ya)
    inter = inter_w * inter_h
    if inter == 0:
        return 0.0

    union = w1 * h1 + w2 * h2 - inter
    return inter / union if union > 0 else 0.0


class TemplateMatcher:
    def __init__(self, template_dir: str = "assets/templates/buttons"):
        self.template_dir = Path(template_dir).resolve()
        self.templates = self._load_templates()

    def _load_templates(self):
        templates = {}
        if not self.template_dir.exists():
            print(f"[WARN] template dir not found: {self.template_dir}")
            return templates

        for p in sorted(self.template_dir.glob("*.png")):
            img = load_image_unicode(p, cv2.IMREAD_COLOR)
            if img is None:
                print(f"[WARN] failed to load template: {p}")
                continue
            templates[p.stem] = img

        print("[INFO] loaded button templates:", list(templates.keys()))
        return templates

    def find(
        self,
        full_img: np.ndarray,
        template_name: str,
        threshold: float = 0.95,
        search_region: Optional[Tuple[int, int, int, int]] = None,
    ):
        template = self.templates.get(template_name)
        if template is None:
            raise ValueError(f"Template not found: {template_name}")

        if search_region is None:
            region = full_img
            rx1, ry1 = 0, 0
        else:
            rx1, ry1, rx2, ry2 = search_region
            region = full_img[ry1:ry2, rx1:rx2].copy()

        res = cv2.matchTemplate(region, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if max_val < threshold:
            return None

        th, tw = template.shape[:2]
        cx = rx1 + max_loc[0] + tw // 2
        cy = ry1 + max_loc[1] + th // 2

        return {
            "center": (cx, cy),
            "score": float(max_val),
            "bbox": (rx1 + max_loc[0], ry1 + max_loc[1], tw, th),
        }

    def find_all(
        self,
        full_img: np.ndarray,
        template_name: str,
        threshold: float = 0.92,
        search_region: Optional[Tuple[int, int, int, int]] = None,
        max_results: int = 10,
        nms_iou_threshold: float = 0.3,
    ) -> List[dict]:
        template = self.templates.get(template_name)
        if template is None:
            raise ValueError(f"Template not found: {template_name}")

        if search_region is None:
            region = full_img
            rx1, ry1 = 0, 0
        else:
            rx1, ry1, rx2, ry2 = search_region
            region = full_img[ry1:ry2, rx1:rx2].copy()

        res = cv2.matchTemplate(region, template, cv2.TM_CCOEFF_NORMED)
        ys, xs = np.where(res >= threshold)

        th, tw = template.shape[:2]
        candidates = []
        for y, x in zip(ys, xs):
            score = float(res[y, x])
            candidates.append({
                "center": (rx1 + x + tw // 2, ry1 + y + th // 2),
                "score": score,
                "bbox": (rx1 + x, ry1 + y, tw, th),
            })

        candidates.sort(key=lambda d: d["score"], reverse=True)

        kept = []
        for cand in candidates:
            ok = True
            for prev in kept:
                if _iou(cand["bbox"], prev["bbox"]) > nms_iou_threshold:
                    ok = False
                    break
            if ok:
                kept.append(cand)
            if len(kept) >= max_results:
                break

        return kept