from uuid import UUID
from pydantic import BaseModel, Field
from app.schemas.card import CardOut


class RecommendCardsRequest(BaseModel):
    deck_id: UUID | None = None
    archetype: str | None = None
    format: str = "tcg"
    playstyle: str | None = None
    exclude_card_ids: list[UUID] = []
    limit: int = Field(default=10, ge=1, le=30)
    explain: bool = False


class CardRecommendation(BaseModel):
    card: CardOut
    score: float
    synergy_reason: str
    meta_relevance: str | None = None
    role: str | None = None  # 'starter', 'extender', 'hand trap', 'engine', etc.
    full_explanation: str | None = None


class RecommendCardsResponse(BaseModel):
    recommendations: list[CardRecommendation]
    meta_context: str | None = None
    deck_analysis: str | None = None


class RecommendDeckRequest(BaseModel):
    archetype: str
    format: str = "tcg"
    playstyle: str | None = None
    limit: int = Field(default=40, ge=20, le=60)


class MetaRecommendRequest(BaseModel):
    format: str = "tcg"
    limit: int = Field(default=5, ge=1, le=20)


class ExplainRequest(BaseModel):
    card_id: UUID
    deck_id: UUID | None = None
    archetype: str | None = None
    format: str = "tcg"
