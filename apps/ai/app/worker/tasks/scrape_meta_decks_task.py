"""Celery task to build meta deck tier list from card popularity data.

Sources:
  1. Own DB — top archetypes ranked by total card views (always available)
  2. masterduelmeta.com — Playwright scraper for Master Duel tier list (best-effort)
  3. limitlesstcg.com — Playwright scraper for TCG tournament data (best-effort)

After running, recalculates popularity_score for all cards.
"""
from __future__ import annotations

import asyncio
import re

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal as async_session
from app.models.card import Card
from app.models.meta import MetaDeck
from app.worker.celery_app import celery_app

logger = get_logger(__name__)


# ─── Source 1: DB-derived archetypes ─────────────────────────────────────────

async def _archetypes_from_db(format: str = "tcg") -> list[dict]:
    """
    Rank archetypes by total card views in our own DB.
    Assigns S/A/B/C tiers by percentile of the top-50 results.
    Works for all formats since archetype presence is format-agnostic.
    """
    async with async_session() as db:
        result = await db.execute(
            select(
                Card.archetype,
                func.sum(Card.views).label("total_views"),
                func.count(Card.id).label("card_count"),
            )
            .where(Card.archetype.isnot(None))
            .group_by(Card.archetype)
            .having(func.count(Card.id) >= 3)
            .order_by(func.sum(Card.views).desc())
            .limit(60)
        )
        rows = result.all()

    if not rows:
        return []

    total = len(rows)
    decks = []
    for i, row in enumerate(rows):
        pct = i / total
        if pct < 0.10:
            tier = "S"
        elif pct < 0.30:
            tier = "A"
        elif pct < 0.60:
            tier = "B"
        else:
            tier = "C"

        decks.append({
            "name": f"{row.archetype} (Meta)",
            "archetype": row.archetype,
            "format": format,
            "tier": tier,
            "source_name": "card_popularity",
            "source_url": None,
            "win_rate": None,
            "tournament_appearances": 0,
            "description": None,
            "extra_data": {"card_count": row.card_count, "total_views": int(row.total_views or 0)},
        })
    return decks


# ─── Source 2: masterduelmeta.com (Playwright, best-effort) ──────────────────

MASTERDUELMETA_TIER_URL = "https://www.masterduelmeta.com/tier-list"
_MDM_TIER_MAP = {"S Tier": "S", "A Tier": "A", "B Tier": "B", "C Tier": "C"}


async def _scrape_masterduelmeta() -> list[dict]:
    try:
        from playwright.async_api import async_playwright  # type: ignore
    except ImportError:
        logger.warning("playwright_not_installed", source="masterduelmeta")
        return []

    results = []
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(MASTERDUELMETA_TIER_URL, wait_until="networkidle", timeout=30000)

            for tier_label, tier_code in _MDM_TIER_MAP.items():
                try:
                    sections = await page.query_selector_all(f"text={tier_label}")
                    for section in sections:
                        parent = await section.evaluate_handle(
                            "el => el.closest('section') || el.parentElement"
                        )
                        deck_els = await parent.query_selector_all(
                            "[class*='deck-name'], [class*='archetype'], h3, h4"
                        )
                        for el in deck_els:
                            name = (await el.inner_text()).strip()
                            if name and name not in _MDM_TIER_MAP:
                                results.append({
                                    "name": name,
                                    "archetype": _infer_archetype(name),
                                    "format": "master_duel",
                                    "tier": tier_code,
                                    "source_name": "masterduelmeta.com",
                                    "source_url": MASTERDUELMETA_TIER_URL,
                                    "win_rate": None,
                                    "tournament_appearances": 0,
                                    "description": None,
                                    "extra_data": {},
                                })
                except Exception as e:
                    logger.warning("mdm_tier_parse_error", tier=tier_label, error=str(e))

            await browser.close()
        logger.info("masterduelmeta_scraped", count=len(results))
    except Exception as e:
        logger.warning("masterduelmeta_scrape_error", error=str(e))
    return results


# ─── Source 3: limitlesstcg.com (Playwright, best-effort) ────────────────────

LIMITLESS_URL = "https://limitlesstcg.com/tournaments?game=YUGIOH"


async def _scrape_limitlesstcg() -> list[dict]:
    try:
        from playwright.async_api import async_playwright  # type: ignore
    except ImportError:
        logger.warning("playwright_not_installed", source="limitlesstcg")
        return []

    archetype_counts: dict[str, int] = {}
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(LIMITLESS_URL, wait_until="networkidle", timeout=30000)

            rows = await page.query_selector_all("table tbody tr, [class*='tournament-row']")
            for row in rows[:200]:
                try:
                    text_content = await row.inner_text()
                    for token in re.split(r"\n|\t|\|", text_content):
                        token = token.strip()
                        if 3 <= len(token) <= 50 and re.match(r"^[A-Z][a-zA-Z\s\-']+$", token):
                            archetype_counts[token] = archetype_counts.get(token, 0) + 1
                except Exception:
                    pass

            await browser.close()
        logger.info("limitlesstcg_scraped", unique_archetypes=len(archetype_counts))
    except Exception as e:
        logger.warning("limitlesstcg_scrape_error", error=str(e))

    results = []
    for archetype, count in archetype_counts.items():
        results.append({
            "name": archetype,
            "archetype": _infer_archetype(archetype),
            "format": "tcg",
            "tier": None,
            "source_name": "limitlesstcg.com",
            "source_url": LIMITLESS_URL,
            "win_rate": None,
            "tournament_appearances": count,
            "description": None,
            "extra_data": {},
        })
    return results


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _infer_archetype(name: str) -> str:
    cleaned = re.sub(
        r"\b(Deck|Build|Strategy|Guide|OTK|FTK|Control|Combo|Turbo|Pendulum|Meta)\b",
        "",
        name,
        flags=re.IGNORECASE,
    ).strip(" -–")
    return cleaned or name


async def _resolve_key_cards(db, archetype: str | None) -> list:
    if not archetype:
        return []
    result = await db.execute(
        select(Card.id)
        .where(Card.archetype.ilike(f"%{archetype}%"))
        .order_by(Card.views.desc())
        .limit(5)
    )
    return [row[0] for row in result.all()]


async def _upsert_meta_decks(db, decks: list[dict]) -> int:
    if not decks:
        return 0

    count = 0
    for deck in decks:
        key_card_ids = await _resolve_key_cards(db, deck.get("archetype"))

        existing = await db.execute(
            select(MetaDeck).where(
                MetaDeck.name == deck["name"],
                MetaDeck.format == deck["format"],
                MetaDeck.source_name == deck.get("source_name"),
            )
        )
        existing_row = existing.scalar_one_or_none()

        if existing_row:
            existing_row.tier = deck.get("tier") or existing_row.tier
            existing_row.tournament_appearances += deck.get("tournament_appearances", 0)
            existing_row.key_card_ids = key_card_ids or existing_row.key_card_ids
            if deck.get("win_rate") is not None:
                existing_row.win_rate = deck["win_rate"]
        else:
            db.add(MetaDeck(
                name=deck["name"],
                archetype=deck.get("archetype"),
                format=deck["format"],
                tier=deck.get("tier"),
                source_name=deck.get("source_name"),
                source_url=deck.get("source_url"),
                win_rate=deck.get("win_rate"),
                tournament_appearances=deck.get("tournament_appearances", 0),
                key_card_ids=key_card_ids or None,
                description=deck.get("description"),
                extra_data=deck.get("extra_data") or {},
            ))
        count += 1

    await db.commit()
    return count


async def _recalculate_popularity_scores(db) -> None:
    """
    popularity_score = 0.6 * log_norm(views) + 0.4 * (meta_deck_presence / max_presence)
    """
    await db.execute(text("""
        WITH
        log_views AS (
            SELECT id, LN(1 + views) AS lv FROM cards
        ),
        max_lv AS (
            SELECT GREATEST(MAX(lv), 1) AS val FROM log_views
        ),
        meta_presence AS (
            SELECT
                c.id,
                COUNT(md.id)::FLOAT AS presence
            FROM cards c
            LEFT JOIN meta_decks md
                ON c.archetype IS NOT NULL
               AND md.archetype ILIKE '%' || c.archetype || '%'
            GROUP BY c.id
        ),
        max_presence AS (
            SELECT GREATEST(MAX(presence), 1) AS val FROM meta_presence
        )
        UPDATE cards
        SET popularity_score =
            ROUND(CAST(
                0.6 * (lv.lv / mlv.val) +
                0.4 * (mp.presence / mmp.val)
            AS NUMERIC), 6)
        FROM log_views lv, max_lv mlv, meta_presence mp, max_presence mmp
        WHERE cards.id = lv.id
          AND cards.id = mp.id
    """))
    await db.commit()
    logger.info("popularity_scores_recalculated")


# ─── Celery Task ─────────────────────────────────────────────────────────────
# Scraping phases each run in their own asyncio.run() so that Playwright
# teardown cannot corrupt the event loop used by asyncpg in the DB phase.

async def _save_meta_decks(all_decks: list[dict]) -> dict:
    async with async_session() as db:
        upserted = await _upsert_meta_decks(db, all_decks)
        await _recalculate_popularity_scores(db)
        return {"total_upserted": upserted}


@celery_app.task(name="scrape_meta_decks_task")
def scrape_meta_decks_task() -> dict:
    # Phase 1: DB-derived archetypes (TCG + OCG + Master Duel)
    tcg_decks = asyncio.run(_archetypes_from_db("tcg"))
    ocg_decks = asyncio.run(_archetypes_from_db("ocg"))
    md_decks = asyncio.run(_archetypes_from_db("master_duel"))
    db_decks = tcg_decks + ocg_decks + md_decks
    logger.info("db_archetypes_derived", count=len(db_decks))

    # Phase 2: best-effort external scrapers (each in own loop to isolate Playwright)
    mdm_decks = asyncio.run(_scrape_masterduelmeta())
    limitless_decks = asyncio.run(_scrape_limitlesstcg())

    all_decks = db_decks + mdm_decks + limitless_decks
    logger.info("meta_decks_total", count=len(all_decks))

    # Phase 3: DB upsert + popularity recalculation in a fresh event loop
    result = asyncio.run(_save_meta_decks(all_decks))
    return {
        "db_archetypes": len(db_decks),
        "masterduelmeta": len(mdm_decks),
        "limitlesstcg": len(limitless_decks),
        **result,
    }
