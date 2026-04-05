"""Shared helpers for mapping YGOProDeck API responses to our DB schema."""
from datetime import datetime, timezone

MONSTER_EXTRA_TYPES = {"fusion", "synchro", "xyz", "link"}


def is_extra_deck(card_data: dict) -> bool:
    frame = card_data.get("frameType", "").lower()
    return any(t in frame for t in MONSTER_EXTRA_TYPES)


def infer_monster_type(data: dict) -> str | None:
    frame = data.get("frameType", "").lower()
    if "monster" not in frame:
        return None
    for t in ["fusion", "synchro", "xyz", "link", "ritual", "pendulum"]:
        if t in frame:
            return t
    return "effect" if "effect" in (data.get("desc") or "").lower() else "normal"


def normalize_ban(status: str) -> str:
    return {
        "Banned": "forbidden",
        "Limited": "limited",
        "Semi-Limited": "semi-limited",
        "Unlimited": "unlimited",
    }.get(status, "unlimited")


def map_card(data: dict) -> dict:
    frame = data.get("frameType", "").lower()
    card_type = "monster" if "monster" in frame else ("spell" if frame == "spell" else "trap")

    banlist = data.get("banlist_info", {})
    misc = (data.get("misc_info") or [{}])[0]

    return {
        "ygoprodeck_id": data["id"],
        "konami_id": str(misc["konami_id"]) if misc.get("konami_id") is not None else None,
        "name_en": data.get("name", ""),
        "card_type": card_type,
        "monster_type": infer_monster_type(data),
        "race": data.get("race"),
        "attribute": (data.get("attribute") or "").lower() or None,
        "level": data.get("level"),
        "rank": data.get("level") if "xyz" in frame else None,
        "link_rating": data.get("linkval"),
        "link_markers": data.get("linkmarkers"),
        "pendulum_scale": data.get("scale"),
        "atk": data.get("atk"),
        "def": data.get("def"),
        "effect_text": data.get("desc"),
        "archetype": data.get("archetype"),
        "tcg_ban_status": normalize_ban(banlist.get("ban_tcg", "Unlimited")),
        "ocg_ban_status": normalize_ban(banlist.get("ban_ocg", "Unlimited")),
        "is_extra_deck": is_extra_deck(data),
        "views": misc.get("views", 0) or 0,
        "updated_at": datetime.now(timezone.utc),
    }


def map_print(card_db_id, card_image: dict, card_set: dict | None = None) -> dict:
    return {
        "card_id": card_db_id,
        "set_code": card_set.get("set_code") if card_set else None,
        "set_name": card_set.get("set_name") if card_set else None,
        "card_number": card_set.get("set_code") if card_set else None,
        "rarity": card_set.get("set_rarity") if card_set else None,
        "region": "TCG",
        "language": "en",
        "image_url": card_image.get("image_url"),
        "image_url_small": card_image.get("image_url_small"),
        "image_url_cropped": card_image.get("image_url_cropped"),
    }
