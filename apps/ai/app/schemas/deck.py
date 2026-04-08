from __future__ import annotations
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.card import CardOut


class DeckCardIn(BaseModel):
    card_id: UUID
    zone: str = "main"
    quantity: int = Field(default=1, ge=1, le=3)
    ordering: int = 0
    notes: str | None = None


class DeckCardOut(BaseModel):
    id: UUID
    card_id: UUID
    zone: str
    quantity: int
    ordering: int
    notes: str | None
    card: CardOut | None = None

    model_config = {"from_attributes": True}


class DeckCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    format: str = "tcg"
    visibility: str = "private"
    archetype: str | None = None
    tags: list[str] = []


class DeckUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    format: str | None = None
    visibility: str | None = None
    archetype: str | None = None
    tags: list[str] | None = None


class DeckOut(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: str | None
    format: str
    visibility: str
    archetype: str | None
    tags: list[str] | None
    main_count: int = 0
    extra_count: int = 0
    side_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeckDetailOut(DeckOut):
    cards: list[DeckCardOut] = []


class DeckVersionOut(BaseModel):
    id: UUID
    deck_id: UUID
    version_number: int
    note: str | None
    deck_snapshot: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class DeckExportRequest(BaseModel):
    format: str = "json"  # 'json', 'text', 'image'
