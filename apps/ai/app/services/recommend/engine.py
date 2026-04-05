"""Recommendation engine: hybrid SQL + vector retrieval → Ollama generation."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.card import Card, CardEmbedding
from app.models.deck import Deck
from app.schemas.card import CardOut
from app.schemas.recommend import (
    CardRecommendation,
    ExplainRequest,
    MetaRecommendRequest,
    RecommendCardsRequest,
    RecommendCardsResponse,
    RecommendDeckRequest,
)
from app.services.embed.ollama import OllamaClient

logger = get_logger(__name__)

RECOMMEND_SYSTEM = """You are a Yu-Gi-Oh expert giving concise deck-building advice.
Always base your advice on the retrieved card data provided in the context.
Do not invent cards that are not in the context."""


class RecommendationEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ollama = OllamaClient()

    async def recommend_cards(self, req: RecommendCardsRequest) -> RecommendCardsResponse:
        deck_context = await self._load_deck_context(req.deck_id)
        archetype = req.archetype or (deck_context.get("archetype") if deck_context else None)

        candidates = await self._retrieve_candidates(
            archetype=archetype,
            format_=req.format,
            exclude_ids=req.exclude_card_ids,
            limit=req.limit * 3,
        )

        recommendations = await self._score_and_rank(candidates, deck_context, archetype, req.limit)

        meta_context: str | None = None
        if req.explain and recommendations:
            meta_context = await self._generate_meta_context(archetype, req.format)

        return RecommendCardsResponse(
            recommendations=recommendations,
            meta_context=meta_context,
            deck_analysis=deck_context.get("analysis") if deck_context else None,
        )

    async def recommend_deck(self, req: RecommendDeckRequest) -> RecommendCardsResponse:
        candidates = await self._retrieve_candidates(
            archetype=req.archetype,
            format_=req.format,
            limit=req.limit * 2,
        )
        recommendations = await self._score_and_rank(
            candidates,
            deck_context={"archetype": req.archetype},
            archetype=req.archetype,
            limit=req.limit,
        )
        return RecommendCardsResponse(recommendations=recommendations)

    async def meta_overview(self, req: MetaRecommendRequest) -> dict:
        from sqlalchemy import text
        result = await self.db.execute(
            select(Card)
            .where(Card.tcg_ban_status != "forbidden")
            .order_by(Card.name_en.asc())
            .limit(100)
        )
        sample_cards = list(result.scalars().all())
        # Return top archetypes with card counts
        archetype_counts: dict[str, int] = {}
        for card in sample_cards:
            if card.archetype:
                archetype_counts[card.archetype] = archetype_counts.get(card.archetype, 0) + 1
        top_archetypes = sorted(archetype_counts.items(), key=lambda x: x[1], reverse=True)[:req.limit]
        return {
            "format": req.format,
            "top_archetypes": [{"archetype": a, "card_count": c} for a, c in top_archetypes],
        }

    async def explain_card(self, req: ExplainRequest) -> dict:
        card_result = await self.db.execute(
            select(Card).options(selectinload(Card.prints)).where(Card.id == req.card_id)
        )
        card = card_result.scalar_one_or_none()
        if not card:
            return {"error": "Card not found"}

        deck_context = await self._load_deck_context(req.deck_id)
        archetype = req.archetype or (deck_context.get("archetype") if deck_context else None)

        prompt = f"""Card: {card.name_en}
Effect: {card.effect_text or 'N/A'}
Archetype: {card.archetype or 'N/A'}
Target deck archetype: {archetype or 'General'}
Format: {req.format}

Explain why this card is useful in this context, what role it plays,
and any relevant meta considerations. Be concise and factual."""

        explanation, token_count = await self.ollama.generate(prompt, system=RECOMMEND_SYSTEM)
        return {
            "card": CardOut.model_validate(card),
            "explanation": explanation,
            "token_count": token_count,
        }

    # ─── Private helpers ────────────────────────────────────────────────────────

    async def _load_deck_context(self, deck_id: UUID | None) -> dict | None:
        if not deck_id:
            return None
        result = await self.db.execute(
            select(Deck)
            .options(selectinload(Deck.cards))
            .where(Deck.id == deck_id)
        )
        deck = result.scalar_one_or_none()
        if not deck:
            return None
        return {
            "archetype": deck.archetype,
            "format": deck.format,
            "card_ids": [str(dc.card_id) for dc in deck.cards],
            "analysis": f"Deck '{deck.name}' — {len(deck.cards)} cards, archetype: {deck.archetype or 'unknown'}",
        }

    async def _retrieve_candidates(
        self,
        archetype: str | None,
        format_: str,
        exclude_ids: list[UUID] | None = None,
        limit: int = 30,
    ) -> list[Card]:
        ban_col = Card.tcg_ban_status if format_ == "tcg" else Card.ocg_ban_status

        query = (
            select(Card)
            .options(selectinload(Card.prints))
            .where(ban_col != "forbidden")
        )
        if archetype:
            query = query.where(Card.archetype.ilike(f"%{archetype}%"))
        if exclude_ids:
            query = query.where(Card.id.notin_(exclude_ids))

        result = await self.db.execute(query.limit(limit))
        return list(result.scalars().all())

    async def _score_and_rank(
        self,
        candidates: list[Card],
        deck_context: dict | None,
        archetype: str | None,
        limit: int,
    ) -> list[CardRecommendation]:
        recommendations: list[CardRecommendation] = []
        for card in candidates[:limit]:
            score = 0.5
            if archetype and card.archetype and archetype.lower() in card.archetype.lower():
                score += 0.3
            role = _infer_role(card)
            recommendations.append(CardRecommendation(
                card=CardOut.model_validate(card),
                score=round(score, 2),
                synergy_reason=f"Shares archetype with target deck" if score > 0.7 else "Potential synergy",
                role=role,
            ))
        recommendations.sort(key=lambda r: r.score, reverse=True)
        return recommendations

    async def _generate_meta_context(self, archetype: str | None, format_: str) -> str:
        prompt = f"Briefly describe the current {format_} meta relevance of the {archetype or 'general'} archetype in Yu-Gi-Oh."
        text, _ = await self.ollama.generate(prompt, system=RECOMMEND_SYSTEM)
        return text


def _infer_role(card: Card) -> str:
    text = (card.effect_text or "").lower()
    if "special summon" in text and ("hand" in text or "deck" in text):
        return "starter/extender"
    if "negate" in text and "destroy" in text:
        return "hand trap / negation"
    if "draw" in text:
        return "draw engine"
    if card.card_type == "spell":
        return "spell support"
    if card.card_type == "trap":
        return "trap"
    return "engine piece"
