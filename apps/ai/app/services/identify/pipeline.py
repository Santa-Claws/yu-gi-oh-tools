"""Card identification pipeline: preprocess → OCR → candidate search → vision fallback → rank."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.card import Card
from app.schemas.card import CardIdentifyResponse, CardIdentifyResult, CardOut
from app.services.card.search import CardSearchService
from app.services.embed.ollama import OllamaClient
from app.services.identify.ocr import OCREngine, OCRResult

logger = get_logger(__name__)

VISION_PROMPT = """You are an expert at identifying Yu-Gi-Oh trading cards.
Look at this card image and tell me:
1. The card name (exactly as printed on the card)
2. Any card number you can see (e.g. DUNE-EN001)
3. Whether this is a Monster, Spell, or Trap card

Respond in this exact format:
NAME: <card name>
NUMBER: <card number or UNKNOWN>
TYPE: <Monster|Spell|Trap>
"""

OCR_CONFIDENCE_THRESHOLD = 0.75


class IdentificationPipeline:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.search_svc = CardSearchService(db)
        self.ocr_engine = OCREngine()
        self.ollama = OllamaClient()

    async def identify_from_image(
        self, image_bytes: bytes, filename: str | None = None
    ) -> CardIdentifyResponse:
        # Stage 1 & 2: Preprocess + OCR
        ocr_result = self.ocr_engine.run(image_bytes)
        used_vision = False
        candidates: list[CardIdentifyResult] = []

        # Stage 3: Candidate search from OCR — always search if we have a name,
        # regardless of overall confidence (name strip OCR is targeted and reliable)
        if ocr_result.card_name:
            candidates = await self._search_candidates(ocr_result.card_name, match_type="ocr_name")
        if not candidates and ocr_result.card_number:
            candidates = await self._search_candidates_by_number(ocr_result.card_number)

        # Stage 4: Vision fallback — only if OCR produced no candidates
        if not candidates:
            used_vision = True
            vision_name = await self._vision_identify(image_bytes)
            if vision_name:
                vision_candidates = await self._search_candidates(vision_name, match_type="vision")
                # Merge, deduplicating by card id
                existing_ids = {c.card.id for c in candidates}
                for vc in vision_candidates:
                    if vc.card.id not in existing_ids:
                        candidates.append(vc)

        # Stage 5: Rank
        candidates = self._rank_candidates(candidates, ocr_result)[:5]

        return CardIdentifyResponse(
            candidates=candidates,
            ocr_text=ocr_result.raw_text or None,
            ocr_confidence=ocr_result.confidence if ocr_result.raw_text else None,
            used_vision_fallback=used_vision,
        )

    async def identify_from_text(self, text: str, language: str = "en") -> CardIdentifyResponse:
        candidates = await self._search_candidates(text, match_type="text_search")
        return CardIdentifyResponse(
            candidates=candidates[:5],
            ocr_text=None,
            ocr_confidence=None,
            used_vision_fallback=False,
        )

    async def _search_candidates(self, name: str, match_type: str) -> list[CardIdentifyResult]:
        cards = await self.search_svc.fuzzy_search_by_name(name, limit=5)
        results = []
        for i, card in enumerate(cards):
            score = max(0.9 - i * 0.1, 0.1)
            results.append(CardIdentifyResult(
                card=CardOut.model_validate(card),
                confidence=score,
                match_type=match_type,
                match_reason=f"Name similarity match for '{name}'",
            ))
        return results

    async def _search_candidates_by_number(self, card_number: str) -> list[CardIdentifyResult]:
        from sqlalchemy import select
        from app.models.card import CardPrint
        from sqlalchemy.orm import selectinload

        result = await self.db.execute(
            select(Card)
            .join(CardPrint, CardPrint.card_id == Card.id)
            .options(selectinload(Card.prints))
            .where(CardPrint.card_number == card_number)
            .limit(3)
        )
        cards = list(result.scalars().all())
        return [
            CardIdentifyResult(
                card=CardOut.model_validate(c),
                confidence=0.95,
                match_type="card_number",
                match_reason=f"Card number exact match: {card_number}",
            )
            for c in cards
        ]

    async def _vision_identify(self, image_bytes: bytes) -> str | None:
        try:
            response, _ = await self.ollama.vision_identify(image_bytes, VISION_PROMPT)
            for line in response.splitlines():
                if line.startswith("NAME:"):
                    name = line.split("NAME:", 1)[1].strip()
                    return name if name and name.upper() != "UNKNOWN" else None
        except Exception as e:
            logger.warning("vision_identify_failed", error=str(e))
        return None

    def _rank_candidates(
        self, candidates: list[CardIdentifyResult], ocr: OCRResult
    ) -> list[CardIdentifyResult]:
        # Boost exact-name-match candidates
        def _score(c: CardIdentifyResult) -> float:
            score = c.confidence
            if ocr.card_name and c.card.name_en.lower() == ocr.card_name.lower():
                score = min(score + 0.2, 1.0)
            if c.match_type == "card_number":
                score = min(score + 0.15, 1.0)
            return score

        return sorted(candidates, key=_score, reverse=True)
