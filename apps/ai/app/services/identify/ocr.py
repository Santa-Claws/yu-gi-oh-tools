"""OCR stage using PaddleOCR with OpenCV preprocessing."""
from __future__ import annotations
import io
import re
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image

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


def _preprocess(image_bytes: bytes) -> np.ndarray:
    """Resize, deskew, denoise, and sharpen card image for OCR."""
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image")

    # Resize to a workable width while maintaining aspect ratio
    h, w = img.shape[:2]
    target_width = 600
    if w != target_width:
        scale = target_width / w
        img = cv2.resize(img, (target_width, int(h * scale)), interpolation=cv2.INTER_LANCZOS4)

    # Convert to grayscale for deskew
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(gray, h=10)

    # Sharpen
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(denoised, -1, kernel)

    # Return color image with same dimensions (for PaddleOCR which prefers BGR)
    result = cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)
    return result


def _extract_card_name(lines: list[str]) -> str | None:
    """Heuristic: card name is typically the first non-empty line at the top."""
    for line in lines[:3]:
        stripped = line.strip()
        if stripped and len(stripped) > 1 and not re.match(r"^\d", stripped):
            return stripped
    return None


def _extract_card_number(lines: list[str]) -> str | None:
    """Card numbers match patterns like DUNE-EN001, LOB-001, etc."""
    pattern = re.compile(r"\b([A-Z]{2,6}-[A-Z]{0,2}\d{3})\b")
    for line in lines:
        m = pattern.search(line.upper())
        if m:
            return m.group(1)
    return None


class OCREngine:
    _ocr = None

    def _get_ocr(self):
        if OCREngine._ocr is None:
            try:
                from paddleocr import PaddleOCR
                OCREngine._ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
            except ImportError:
                logger.warning(
                    "paddleocr_not_installed",
                    hint="Install via: pip install paddleocr paddlepaddle",
                )
                OCREngine._ocr = None
        return OCREngine._ocr

    def run(self, image_bytes: bytes) -> OCRResult:
        try:
            preprocessed = _preprocess(image_bytes)
        except ValueError as e:
            logger.warning("image_preprocess_failed", error=str(e))
            return OCRResult(raw_text="", lines=[], confidence=0.0)

        ocr = self._get_ocr()
        if ocr is None:
            return OCRResult(raw_text="", lines=[], confidence=0.0)
        result = ocr.ocr(preprocessed, cls=True)

        if not result or not result[0]:
            return OCRResult(raw_text="", lines=[], confidence=0.0)

        lines: list[str] = []
        confidences: list[float] = []

        for block in result[0]:
            # block format: [[bbox_coords], (text, confidence)]
            text, confidence = block[1]
            if text.strip():
                lines.append(text)
                confidences.append(float(confidence))

        raw_text = "\n".join(lines)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return OCRResult(
            raw_text=raw_text,
            lines=lines,
            confidence=avg_confidence,
            card_name=_extract_card_name(lines),
            card_number=_extract_card_number(lines),
            effect_text="\n".join(lines[3:]) if len(lines) > 3 else None,
        )
