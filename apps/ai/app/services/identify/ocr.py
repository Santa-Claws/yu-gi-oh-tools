"""OCR stage: detect card in image, deskew, then extract card name with pytesseract."""
from __future__ import annotations

import re
from dataclasses import dataclass

import cv2
import numpy as np

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class OCRResult:
    raw_text: str
    lines: list[str]
    confidence: float
    card_name: str | None = None
    card_number: str | None = None
    effect_text: str | None = None


# ─── Card detection ───────────────────────────────────────────────────────────

def _order_points(pts: np.ndarray) -> np.ndarray:
    """Order 4 points as [top-left, top-right, bottom-right, bottom-left]."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]    # top-left: smallest sum
    rect[2] = pts[np.argmax(s)]    # bottom-right: largest sum
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)] # top-right: smallest diff
    rect[3] = pts[np.argmax(diff)] # bottom-left: largest diff
    return rect


def _perspective_transform(img: np.ndarray, pts: np.ndarray) -> np.ndarray:
    rect = _order_points(pts.reshape(4, 2).astype("float32"))
    tl, tr, br, bl = rect
    w = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    h = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(img, M, (w, h))


def _detect_and_crop_card(img: np.ndarray) -> np.ndarray | None:
    """
    Find the largest quadrilateral matching Yu-Gi-Oh card aspect ratio (~0.69).
    Returns a perspective-corrected crop, or None if not found.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 40, 120)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=2)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    img_area = img.shape[0] * img.shape[1]

    best, best_area = None, 0
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < img_area * 0.05:  # must cover at least 5% of image
            continue
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.03 * peri, True)
        if len(approx) != 4:
            continue
        _, _, w, h = cv2.boundingRect(approx)
        if h == 0:
            continue
        aspect = w / h
        # Yu-Gi-Oh card: 59mm/86mm ≈ 0.686; allow ±20% for angle/perspective
        if 0.50 < aspect < 0.85 and area > best_area:
            best_area = area
            best = approx

    if best is None:
        return None
    return _perspective_transform(img, best)


# ─── Preprocessing ────────────────────────────────────────────────────────────

def _preprocess_for_ocr(img: np.ndarray) -> np.ndarray:
    """Resize to standard width, denoise, and sharpen."""
    h, w = img.shape[:2]
    target_w = 600
    if w != target_w:
        scale = target_w / w
        img = cv2.resize(img, (target_w, int(h * scale)), interpolation=cv2.INTER_LANCZOS4)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(denoised, -1, kernel)
    return cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)


def _crop_name_strip(img: np.ndarray) -> np.ndarray:
    """Crop to the card name banner: top 3–13% height, 5–95% width."""
    h, w = img.shape[:2]
    return img[int(h * 0.03): int(h * 0.13), int(w * 0.05): int(w * 0.95)]


# ─── Text extraction helpers ──────────────────────────────────────────────────

def _extract_card_name(lines: list[str]) -> str | None:
    """Heuristic: card name is the first non-empty, non-numeric line at the top."""
    for line in lines[:3]:
        stripped = line.strip()
        if stripped and len(stripped) > 1 and not re.match(r"^\d", stripped):
            return stripped
    return None


def _extract_card_number(lines: list[str]) -> str | None:
    """Match patterns like DUNE-EN001, LOB-001, etc."""
    pattern = re.compile(r"\b([A-Z]{2,6}-[A-Z]{0,2}\d{3})\b")
    for line in lines:
        m = pattern.search(line.upper())
        if m:
            return m.group(1)
    return None


# ─── OCR engine ───────────────────────────────────────────────────────────────

class OCREngine:
    def run(self, image_bytes: bytes) -> OCRResult:
        try:
            import pytesseract
        except ImportError:
            logger.warning("pytesseract_not_installed")
            return OCRResult(raw_text="", lines=[], confidence=0.0)

        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            logger.warning("image_decode_failed")
            return OCRResult(raw_text="", lines=[], confidence=0.0)

        # Try to isolate card from background (handles angled/non-cropped photos)
        card_img = _detect_and_crop_card(img)
        if card_img is not None:
            logger.info("card_detected_and_cropped")
            source = card_img
        else:
            logger.info("card_detection_failed_using_full_image")
            source = img

        processed = _preprocess_for_ocr(source)

        # Name strip: single-line OCR on the name banner (psm 7)
        name_strip = _crop_name_strip(processed)
        name_text = pytesseract.image_to_string(name_strip, config="--psm 7").strip()

        # Full card: block OCR for card number, effect text (psm 6)
        full_text = pytesseract.image_to_string(processed, config="--psm 6")
        full_lines = [l.strip() for l in full_text.splitlines() if l.strip()]

        # Per-word confidence from full card
        data = pytesseract.image_to_data(
            processed, output_type=pytesseract.Output.DICT, config="--psm 6"
        )
        confs = [
            c / 100.0
            for c, w in zip(data["conf"], data["text"])
            if w.strip() and c >= 0
        ]
        avg_conf = sum(confs) / len(confs) if confs else 0.0

        # Prefer name-strip result; fall back to first-line heuristic
        card_name = name_text if len(name_text) > 1 else _extract_card_name(full_lines)
        card_number = _extract_card_number(full_lines)

        logger.info(
            "ocr_complete",
            card_name=card_name,
            card_number=card_number,
            confidence=round(avg_conf, 2),
            used_crop=card_img is not None,
        )

        return OCRResult(
            raw_text=full_text,
            lines=full_lines,
            confidence=avg_conf,
            card_name=card_name,
            card_number=card_number,
            effect_text="\n".join(full_lines[3:]) if len(full_lines) > 3 else None,
        )
