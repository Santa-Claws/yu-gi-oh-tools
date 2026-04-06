"""Embedding task — generates pgvector embeddings for all cards without them."""
import asyncio

from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.card import Card, CardEmbedding
from app.services.embed.ollama import OllamaClient
from app.worker.celery_app import celery_app

logger = get_logger(__name__)

BATCH_SIZE = 50


def _build_chunks(card: Card) -> list[tuple[str, str]]:
    """Returns list of (chunk_type, chunk_text) pairs for a card."""
    chunks = []

    # Name chunk
    chunks.append(("name", card.name_en))

    # Effect chunk
    if card.effect_text:
        chunks.append(("effect", card.effect_text))

    # Full chunk (name + type + subtype + race + effect)
    parts = [card.name_en]
    if card.archetype:
        parts.append(f"Archetype: {card.archetype}")
    if card.card_type:
        parts.append(f"Type: {card.card_type}")
    if card.race:
        # For monsters: race = creature type (Zombie, Dragon, etc.)
        # For spells/traps: race = subtype (Field, Counter, Quick-Play, etc.)
        label = "Subtype" if card.card_type in ("spell", "trap") else "Race"
        parts.append(f"{label}: {card.race}")
    if card.attribute:
        parts.append(f"Attribute: {card.attribute}")
    if card.monster_type:
        parts.append(f"Monster type: {card.monster_type}")
    if card.effect_text:
        parts.append(card.effect_text)
    chunks.append(("full", " | ".join(parts)))

    return chunks


async def _run_embed():
    ollama = OllamaClient()

    if not await ollama.health_check():
        logger.error("embed_ollama_unreachable")
        return {"error": "Ollama unreachable"}

    async with AsyncSessionLocal() as db:
        # Cards that are missing the "full" chunk (re-embed all if chunk format changed)
        full_embedded_ids = select(CardEmbedding.card_id).where(
            CardEmbedding.chunk_type == "full"
        )
        result = await db.execute(
            select(Card).where(Card.id.notin_(full_embedded_ids))
        )
        cards = list(result.scalars().all())
        logger.info("embed_cards_start", count=len(cards))

        total_embedded = 0
        for i in range(0, len(cards), BATCH_SIZE):
            batch = cards[i:i + BATCH_SIZE]
            for card in batch:
                try:
                    chunks = _build_chunks(card)
                    texts = [t for _, t in chunks]
                    embeddings = await ollama.embed_batch(texts)

                    for (chunk_type, chunk_text), embedding in zip(chunks, embeddings):
                        await db.execute(
                            pg_insert(CardEmbedding).values(
                                card_id=card.id,
                                chunk_type=chunk_type,
                                chunk_text=chunk_text,
                                embedding=embedding,
                                source="ollama_nomic",
                            ).on_conflict_do_update(
                                constraint="uq_card_embeddings_card_chunk",
                                set_={"chunk_text": chunk_text, "embedding": embedding},
                            )
                        )
                    total_embedded += 1
                except Exception as e:
                    logger.error("embed_card_failed", card_id=str(card.id), error=str(e))

            await db.commit()
            logger.info("embed_cards_progress", done=i + len(batch), total=len(cards))

    logger.info("embed_cards_complete", total=total_embedded)
    return {"embedded": total_embedded}


@celery_app.task(name="app.worker.tasks.embed_tasks.embed_cards_task", bind=True)
def embed_cards_task(self):
    return asyncio.run(_run_embed())
