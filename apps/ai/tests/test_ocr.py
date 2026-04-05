"""Tests for OCR utilities."""
import pytest
from app.services.identify.ocr import _extract_card_name, _extract_card_number


def test_extract_card_number_standard():
    lines = ["DUNE-EN001", "Blue-Eyes White Dragon"]
    assert _extract_card_number(lines) == "DUNE-EN001"


def test_extract_card_number_missing():
    lines = ["Blue-Eyes White Dragon", "Effect Monster"]
    assert _extract_card_number(lines) is None


def test_extract_card_name_first_line():
    lines = ["Blue-Eyes White Dragon", "Level 8 / LIGHT / Dragon"]
    assert _extract_card_name(lines) == "Blue-Eyes White Dragon"


def test_extract_card_name_skips_numeric():
    lines = ["123", "Dark Magician"]
    assert _extract_card_name(lines) == "Dark Magician"
