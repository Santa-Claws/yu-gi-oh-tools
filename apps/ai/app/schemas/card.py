from __future__ import annotations
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CardPrintOut(BaseModel):
    id: UUID
    set_code: str | None
    set_name: str | None
    card_number: str | None
    rarity: str | None
    region: str | None
    language: str
    release_date: date | None
    image_url: str | None
    image_url_small: str | None
    image_url_cropped: str | None

    model_config = {"from_attributes": True}


class CardOut(BaseModel):
    id: UUID
    ygoprodeck_id: int | None
    name_en: str
    name_ja: str | None
    card_type: str
    monster_type: str | None
    race: str | None
    attribute: str | None
    level: int | None
    rank: int | None
    link_rating: int | None
    link_markers: list[str] | None
    pendulum_scale: int | None
    atk: int | None
    def_: int | None = Field(alias="def")
    effect_text: str | None
    pendulum_text: str | None
    flavor_text: str | None
    archetype: str | None
    tcg_ban_status: str
    ocg_ban_status: str
    is_extra_deck: bool
    prints: list[CardPrintOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class CardSearchParams(BaseModel):
    q: str | None = None
    card_type: str | None = None
    attribute: str | None = None
    monster_type: str | None = None
    race: str | None = None
    archetype: str | None = None
    level_min: int | None = None
    level_max: int | None = None
    atk_min: int | None = None
    atk_max: int | None = None
    def_min: int | None = None
    def_max: int | None = None
    tcg_ban_status: str | None = None
    ocg_ban_status: str | None = None
    format: Literal["tcg", "ocg"] | None = None
    set_code: str | None = None
    rarity: str | None = None
    language: str | None = None
    sort: str = "relevance"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=24, ge=1, le=100)


class CardIdentifyTextRequest(BaseModel):
    text: str
    language: str = "en"


class CardIdentifyResult(BaseModel):
    card: CardOut
    confidence: float
    match_type: str  # 'exact', 'fuzzy', 'vision', 'semantic'
    match_reason: str


class CardIdentifyResponse(BaseModel):
    candidates: list[CardIdentifyResult]
    ocr_text: str | None = None
    ocr_confidence: float | None = None
    used_vision_fallback: bool = False
