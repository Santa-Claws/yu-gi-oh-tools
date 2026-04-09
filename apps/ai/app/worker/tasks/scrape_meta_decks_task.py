"""Celery task to build meta deck tier list from card popularity data.

Sources:
  1. Own DB — top archetypes ranked by total card views (always available)
  2. masterduelmeta.com — Playwright scraper for Master Duel tier list (best-effort)
  3. limitlesstcg.com — Playwright scraper for TCG tournament data (best-effort)

After running, recalculates popularity_score for all cards.
"""
from __future__ import annotations

import asyncio
import json
import re

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.card import Card
from app.models.meta import MetaDeck, MetaDeckCard
from app.worker.celery_app import celery_app

logger = get_logger(__name__)


def _make_task_session():
    """Create a fresh session factory with NullPool for each asyncio.run() call.
    NullPool avoids asyncpg connections being cached across different event loops."""
    settings = get_settings()
    url = settings.database_url
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(url, poolclass=NullPool)
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


# ─── Source 1: DB-derived archetypes ─────────────────────────────────────────

async def _archetypes_from_db(format: str = "tcg") -> list[dict]:
    """
    Rank archetypes by total card views in our own DB.
    Assigns S/A/B/C tiers by percentile of the top-50 results.
    Works for all formats since archetype presence is format-agnostic.
    """
    async with _make_task_session()() as db:
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
            browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            page = await browser.new_page()
            await page.goto(MASTERDUELMETA_TIER_URL, wait_until="load", timeout=30000)

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
            browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            page = await browser.new_page()
            await page.goto(LIMITLESS_URL, wait_until="load", timeout=30000)

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

# ─── Extra deck type detection ───────────────────────────────────────────────

_EXTRA_DECK_KEYWORDS = ("fusion", "synchro", "xyz", "link")

def _zone_for_card_type(card_type: str) -> str:
    lower = card_type.lower()
    if any(k in lower for k in _EXTRA_DECK_KEYWORDS):
        return "extra"
    return "main"


# ─── Full deck list scraping: LimitlessTCG ───────────────────────────────────

LIMITLESS_TOURNAMENTS_URL = "https://limitlesstcg.com/tournaments?game=YUGIOH"


def _parse_card_lines(text: str) -> list[tuple[str, int]]:
    """
    Parse lines like:
      '3 Dark Magician', '3x Dark Magician', 'Dark Magician x3', 'Dark Magician (3)'
    Returns list of (card_name, quantity).
    """
    results = []
    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) > 80:
            continue
        # Patterns: leading count
        m = re.match(r'^(\d)\s*[x×]?\s+(.+)$', line)
        if not m:
            m = re.match(r'^(.+?)\s*[x×]\s*(\d)$', line)
            if m:
                name, qty = m.group(1).strip(), int(m.group(2))
                results.append((name, qty))
                continue
        if m:
            qty, name = int(m.group(1)), m.group(2).strip()
            if 1 <= qty <= 3 and len(name) >= 2:
                results.append((name, qty))
    return results


async def _match_cards_by_name(db: AsyncSession, names: list[str]) -> dict[str, Card]:
    """Case-insensitive lookup of Card by name_en."""
    if not names:
        return {}
    lower_names = [n.lower() for n in names]
    result = await db.execute(
        select(Card).where(func.lower(Card.name_en).in_(lower_names))
    )
    return {c.name_en.lower(): c for c in result.scalars().all()}


def _count_card_ids(id_list: list) -> dict[int, int]:
    """Count repeated IDs — YGOPRODeck repeats card IDs for quantity."""
    counts: dict[int, int] = {}
    for raw_id in id_list:
        try:
            cid = int(raw_id)
        except (TypeError, ValueError):
            continue
        counts[cid] = counts.get(cid, 0) + 1
    return counts


async def _match_cards_by_ygoprodeck_id(db: AsyncSession, ids: list[int]) -> dict[int, Card]:
    if not ids:
        return {}
    result = await db.execute(select(Card).where(Card.ygoprodeck_id.in_(ids)))
    return {c.ygoprodeck_id: c for c in result.scalars().all()}


async def _save_full_deck(db: AsyncSession, meta_deck_id, entries: list[dict]) -> None:
    """Delete existing card list for deck and insert new one, set has_full_list=True."""
    await db.execute(
        text("DELETE FROM meta_deck_cards WHERE meta_deck_id = :id"),
        {"id": meta_deck_id},
    )
    for e in entries:
        db.add(MetaDeckCard(
            meta_deck_id=meta_deck_id,
            card_id=e["card_id"],
            zone=e["zone"],
            quantity=e["quantity"],
            ordering=e["ordering"],
        ))
    deck = await db.get(MetaDeck, meta_deck_id)
    if deck:
        deck.has_full_list = True
    await db.commit()


async def _find_or_create_meta_deck(db: AsyncSession, name: str, archetype: str | None, format: str, source_name: str, source_url: str | None) -> MetaDeck:
    result = await db.execute(
        select(MetaDeck).where(MetaDeck.name == name, MetaDeck.format == format)
    )
    deck = result.scalar_one_or_none()
    if not deck:
        deck = MetaDeck(
            name=name,
            archetype=archetype,
            format=format,
            source_name=source_name,
            source_url=source_url,
            key_card_ids=[],
        )
        db.add(deck)
        await db.flush()
    return deck


# ─── Full deck list scraping: masterduelmeta.com ─────────────────────────────

MASTERDUELMETA_DECKS_URL = "https://www.masterduelmeta.com/top-decks"

_RARITY_RE = re.compile(r"^(UR|SR|R|N|HR)\s*Rarity$", re.IGNORECASE)
_COPIES_RE = re.compile(r"^(\d+)\s+cop(?:y|ies)$", re.IGNORECASE)
_SKIP_ALTS = {"Yu-Gi-Oh! Master Duel Meta", "cp-ur", "cp-sr", "[object Object]"}
# Non-card alt texts that signal the end of the deck list
_DECK_END_TOKENS = {"Nice!", "Funny", "Love", "Woah", "Angry", "Sad", "JOIN THE COMMUNITY", "Login"}


def _parse_mdm_alts(alts: list[str]) -> list[tuple[str, int]]:
    """
    Parse img[alt] values from a masterduelmeta.com deck page into (card_name, quantity) pairs.
    Pattern: card names appear as alts; "X copies" alts indicate quantity > 1.
    """
    results: list[tuple[str, int]] = []
    for alt in alts:
        if alt in _SKIP_ALTS or _RARITY_RE.match(alt):
            continue
        m = _COPIES_RE.match(alt)
        if m:
            if results:
                name, _ = results[-1]
                results[-1] = (name, int(m.group(1)))
            continue
        # Stop at non-card footer tokens or pack/section names (all-caps multi-word)
        if alt in _DECK_END_TOKENS:
            break
        if "Breakdown" in alt or "Pack" in alt or "Rarity" in alt:
            continue
        results.append((alt, 1))
    return results


async def _scrape_masterduelmeta_full_decks() -> int:
    """
    Scrape full deck lists from masterduelmeta.com/top-decks.
    Card names are extracted from img[alt] attributes on each deck page.
    Returns number of decks saved.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("playwright_not_installed", source="masterduelmeta_full")
        return 0

    raw_decks: list[dict] = []

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            page = await browser.new_page()

            # Load top-decks listing
            await page.goto(MASTERDUELMETA_DECKS_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)

            deck_links = await page.eval_on_selector_all(
                "a[href*='/top-decks/']",
                "els => [...new Set(els.map(e => e.href).filter(h => h.split('/').length >= 8))].slice(0, 30)"
            )
            logger.info("masterduelmeta_deck_links_found", count=len(deck_links))

            for d_url in deck_links[:25]:
                try:
                    await page.goto(d_url, wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_timeout(4000)

                    # Get deck name from h1/h2
                    title_el = await page.query_selector("h1, h2")
                    deck_name_raw = (await title_el.inner_text()).strip() if title_el else ""
                    # Extract archetype from URL: /top-decks/{rank}/{date}/{archetype}/...
                    url_parts = d_url.rstrip("/").split("/")
                    url_archetype = url_parts[-3] if len(url_parts) >= 3 else ""
                    archetype = url_archetype.replace("-", " ").title() if url_archetype else _infer_archetype(deck_name_raw)
                    deck_name = f"{archetype} (Master Duel)"

                    alts = await page.eval_on_selector_all("img[alt]", "els => els.map(e => e.alt)")
                    cards = _parse_mdm_alts(alts)

                    if len(cards) >= 10:
                        raw_decks.append({
                            "name": deck_name,
                            "archetype": archetype,
                            "source_url": d_url,
                            "cards": cards,
                        })
                        logger.info("masterduelmeta_deck_parsed", name=deck_name, cards=len(cards), url=d_url)
                except Exception as e:
                    logger.debug("masterduelmeta_deck_parse_error", url=d_url, error=str(e))

            await browser.close()
    except Exception as e:
        logger.warning("masterduelmeta_full_scrape_error", error=str(e))

    if not raw_decks:
        logger.info("masterduelmeta_full_decks_none_found")
        return 0

    saved = 0
    async with _make_task_session()() as db:
        for raw in raw_decks:
            try:
                deck = await _find_or_create_meta_deck(
                    db, raw["name"], raw.get("archetype"), "master_duel",
                    "masterduelmeta.com", raw.get("source_url"),
                )
                card_map = await _match_cards_by_name(db, [name for name, _ in raw["cards"]])

                entries = []
                for i, (card_name, qty) in enumerate(raw["cards"]):
                    card = card_map.get(card_name.lower())
                    if not card:
                        continue
                    entries.append({
                        "card_id": card.id,
                        "zone": _zone_for_card_type(card.card_type),
                        "quantity": min(qty, 3),
                        "ordering": i,
                    })

                if len(entries) >= 10:
                    await _save_full_deck(db, deck.id, entries)
                    saved += 1
            except Exception as e:
                logger.warning("masterduelmeta_deck_save_error", name=raw.get("name"), error=str(e))

    logger.info("masterduelmeta_full_decks_saved", count=saved)
    return saved


# ─── Full deck list scraping: ygoprodeck.com (TCG) ───────────────────────────

YGOPRODECK_DECKS_URL = "https://ygoprodeck.com/api/decks/getDecks.php"


def _parse_ygoprodeck_zone(raw) -> list:
    """Zone fields are JSON-encoded strings; parse them into a list."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return []
    return []


async def _scrape_ygoprodeck_tcg_decks() -> int:
    """
    Fetch TCG tournament meta decks from the YGOPRODeck JSON API.
    No Playwright needed — plain httpx GET.
    Zone fields are JSON-encoded strings of repeated card IDs (repeated = higher quantity).
    Returns number of decks saved.
    """
    params = {
        "num": "50",
        "offset": "0",
        "format": "Tournament Meta Decks",
        "sort": "Popularity",
    }
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        async with httpx.AsyncClient(timeout=30, headers=headers) as client:
            resp = await client.get(YGOPRODECK_DECKS_URL, params=params)
            resp.raise_for_status()
            decks_json = resp.json()
    except Exception as e:
        logger.warning("ygoprodeck_fetch_error", error=str(e))
        return 0

    if not isinstance(decks_json, list):
        logger.warning("ygoprodeck_unexpected_response", type=type(decks_json).__name__)
        return 0

    logger.info("ygoprodeck_decks_fetched", count=len(decks_json))

    saved = 0
    async with _make_task_session()() as db:
        for deck_data in decks_json:
            try:
                deck_name = (deck_data.get("deck_name") or "").strip()
                if not deck_name:
                    continue

                zone_counts = {
                    "main":  _count_card_ids(_parse_ygoprodeck_zone(deck_data.get("main_deck"))),
                    "extra": _count_card_ids(_parse_ygoprodeck_zone(deck_data.get("extra_deck"))),
                    "side":  _count_card_ids(_parse_ygoprodeck_zone(deck_data.get("side_deck"))),
                }
                all_ids = list({id_ for counts in zone_counts.values() for id_ in counts})
                if not all_ids:
                    continue

                card_map = await _match_cards_by_ygoprodeck_id(db, all_ids)

                entries: list[dict] = []
                ordering = 0
                for zone in ("main", "extra", "side"):
                    for ygo_id, qty in zone_counts[zone].items():
                        card = card_map.get(ygo_id)
                        if card:
                            entries.append({
                                "card_id": card.id,
                                "zone": zone,
                                "quantity": min(qty, 3),
                                "ordering": ordering,
                            })
                            ordering += 1

                if len(entries) < 10:
                    continue

                pretty_url = deck_data.get("pretty_url") or ""
                source_url = f"https://ygoprodeck.com/deck/{pretty_url}" if pretty_url else None

                meta_deck = await _find_or_create_meta_deck(
                    db, deck_name, _infer_archetype(deck_name),
                    "tcg", "ygoprodeck.com", source_url,
                )
                await _save_full_deck(db, meta_deck.id, entries)
                saved += 1

            except Exception as e:
                logger.warning("ygoprodeck_deck_save_error", name=deck_data.get("deck_name"), error=str(e))

    logger.info("ygoprodeck_tcg_decks_saved", count=saved)
    return saved


async def _save_meta_decks(all_decks: list[dict]) -> dict:
    async with _make_task_session()() as db:
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

    # Phase 4: scrape full deck lists from masterduelmeta.com
    mdm_full = asyncio.run(_scrape_masterduelmeta_full_decks())

    # Phase 5: scrape full TCG deck lists from ygoprodeck.com
    ygoprodeck_full = asyncio.run(_scrape_ygoprodeck_tcg_decks())

    # Phase 6: bust the meta cache so next request gets fresh data
    async def _bust_cache():
        import redis.asyncio as aioredis
        async with aioredis.from_url(get_settings().redis_url, decode_responses=True) as r:
            keys = await r.keys("meta:*")
            if keys:
                await r.delete(*keys)
                logger.info("meta_cache_busted", keys=len(keys))

    asyncio.run(_bust_cache())

    return {
        "db_archetypes": len(db_decks),
        "masterduelmeta": len(mdm_decks),
        "limitlesstcg": len(limitless_decks),
        "full_decks_masterduelmeta": mdm_full,
        "full_decks_ygoprodeck": ygoprodeck_full,
        **result,
    }
