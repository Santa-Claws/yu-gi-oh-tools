"""Celery task to scrape meta deck tier lists and tournament results.

Sources:
  1. YGOProDeck top community decks API (JSON, no browser)
  2. masterduelmeta.com tier list (Playwright, Master Duel format)
  3. limitlesstcg.com tournament results (Playwright, TCG format)

After scraping, recalculates popularity_score for all cards.
"""
from __future__ import annotations

import asyncio
import math
import re
from typing import Any

import httpx
from sqlalchemy import select, text, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal as async_session
from app.models.card import Card
from app.models.meta import MetaDeck
from app.worker.celery_app import celery_app

logger = get_logger(__name__)

# ─── YGOProDeck API ──────────────────────────────────────────────────────────

YGOPRODECK_TOP_DECKS_URL = (
    "https://ygoprodeck.com/api/deck/getDeckList.php?num=20&sort=topDecks&format={fmt}"
)
YGOPRODECK_FORMATS = [
    ("tcg", "tcg"),
    ("ocg", "ocg"),
    ("master_duel", "master_duel"),
]


async def _scrape_ygoprodeck(client: httpx.AsyncClient) -> list[dict]:
    results = []
    for fmt_label, fmt_param in YGOPRODECK_FORMATS:
        try:
            url = YGOPRODECK_TOP_DECKS_URL.format(fmt=fmt_param)
            resp = await client.get(url, timeout=15)
            if resp.status_code != 200:
                logger.warning("ygoprodeck_top_decks_failed", format=fmt_label, status=resp.status_code)
                continue
            data = resp.json()
            decks = data if isinstance(data, list) else data.get("data", [])
            for deck in decks:
                name = deck.get("deck_name") or deck.get("name") or "Unknown"
                archetype = deck.get("archetype") or deck.get("main_archetype") or _infer_archetype(name)
                results.append({
                    "name": name,
                    "archetype": archetype,
                    "format": fmt_label,
                    "tier": None,
                    "source_name": "ygoprodeck.com",
                    "source_url": f"https://ygoprodeck.com/decks/?format={fmt_param}",
                    "win_rate": None,
                    "tournament_appearances": 0,
                    "description": None,
                    "extra_data": {"raw": deck},
                })
            logger.info("ygoprodeck_scraped", format=fmt_label, count=len(decks))
        except Exception as e:
            logger.error("ygoprodeck_scrape_error", format=fmt_label, error=str(e))
    return results


# ─── masterduelmeta.com (Playwright) ─────────────────────────────────────────

MASTERDUELMETA_TIER_URL = "https://www.masterduelmeta.com/tier-list"
# tier section headings map to tier labels
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

            # Each tier section has a heading like "S Tier" and cards beneath it
            for tier_label, tier_code in _MDM_TIER_MAP.items():
                try:
                    sections = await page.query_selector_all(f"text={tier_label}")
                    for section in sections:
                        # Walk up to the section container, find sibling deck names
                        parent = await section.evaluate_handle("el => el.closest('section') || el.parentElement")
                        deck_els = await parent.query_selector_all("[class*='deck-name'], [class*='archetype'], h3, h4")
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
        logger.error("masterduelmeta_scrape_error", error=str(e))
    return results


# ─── limitlesstcg.com (Playwright) ───────────────────────────────────────────

LIMITLESS_URL = "https://limitlesstcg.com/tournaments?game=YUGIOH"


async def _scrape_limitlesstcg() -> list[dict]:
    """Returns a dict of archetype → tournament_appearances count (TCG format)."""
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

            # Grab top-8 deck archetype entries from tournament result rows
            rows = await page.query_selector_all("table tbody tr, [class*='tournament-row']")
            for row in rows[:200]:
                try:
                    text_content = await row.inner_text()
                    # Heuristic: lines that look like archetype names (Title Case, 3+ chars)
                    for token in re.split(r"\n|\t|\|", text_content):
                        token = token.strip()
                        if 3 <= len(token) <= 50 and re.match(r"^[A-Z][a-zA-Z\s\-']+$", token):
                            archetype_counts[token] = archetype_counts.get(token, 0) + 1
                except Exception:
                    pass

            await browser.close()
        logger.info("limitlesstcg_scraped", unique_archetypes=len(archetype_counts))
    except Exception as e:
        logger.error("limitlesstcg_scrape_error", error=str(e))

    # Convert to MetaDeck dicts
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
    """Best-effort archetype extraction from a deck name string."""
    # Strip common suffixes: "Deck", "OTK", "FTK", "Control", etc.
    cleaned = re.sub(
        r"\b(Deck|Build|Strategy|Guide|OTK|FTK|Control|Combo|Turbo|Pendulum)\b",
        "",
        name,
        flags=re.IGNORECASE,
    ).strip(" -–")
    return cleaned or name


async def _resolve_key_cards(db, archetype: str | None) -> list:
    """Return up to 5 card UUIDs for cards matching the archetype, ordered by views."""
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
    """Merge deck list into meta_decks, incrementing tournament_appearances where applicable."""
    if not decks:
        return 0

    count = 0
    for deck in decks:
        key_card_ids = await _resolve_key_cards(db, deck.get("archetype"))

        # Check existing row by (name, format, source_name)
        existing = await db.execute(
            select(MetaDeck).where(
                and_(
                    MetaDeck.name == deck["name"],
                    MetaDeck.format == deck["format"],
                    MetaDeck.source_name == deck.get("source_name"),
                )
            )
        )
        row = existing.scalar_one_or_none()

        if row:
            row.tier = deck["tier"] or row.tier
            row.win_rate = deck["win_rate"] if deck["win_rate"] is not None else row.win_rate
            row.tournament_appearances += deck.get("tournament_appearances", 0)
            if key_card_ids:
                row.key_card_ids = key_card_ids
            row.extra_data = deck.get("extra_data") or row.extra_data
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

    Uses a single UPDATE with window functions via raw SQL.
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

async def _run_scrape_meta_decks() -> dict:
    async with async_session() as db:
        async with httpx.AsyncClient(headers={"User-Agent": "YGOTools/1.0"}) as client:
            ygoprodeck_decks = await _scrape_ygoprodeck(client)

        # Run Playwright scrapers sequentially (each launches its own browser)
        mdm_decks = await _scrape_masterduelmeta()
        limitless_decks = await _scrape_limitlesstcg()

        all_decks = ygoprodeck_decks + mdm_decks + limitless_decks
        logger.info("meta_decks_total_scraped", count=len(all_decks))

        upserted = await _upsert_meta_decks(db, all_decks)
        await _recalculate_popularity_scores(db)

        return {
            "ygoprodeck": len(ygoprodeck_decks),
            "masterduelmeta": len(mdm_decks),
            "limitlesstcg": len(limitless_decks),
            "total_upserted": upserted,
        }


@celery_app.task(name="scrape_meta_decks_task")
def scrape_meta_decks_task() -> dict:
    return asyncio.run(_run_scrape_meta_decks())
