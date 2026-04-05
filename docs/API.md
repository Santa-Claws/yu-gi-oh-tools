# Yu-Gi-Oh Tools — API Reference

Base URL: `http://<server>:8000`

All endpoints that require authentication expect a Bearer token in the `Authorization` header:
```
Authorization: Bearer <jwt_token>
```

---

## Authentication

### Register
```
POST /auth/register
```
Body:
```json
{
  "email": "user@example.com",
  "password": "secret",
  "display_name": "Player One"
}
```
Response:
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "display_name": "Player One",
  "role": "user"
}
```

### Login
```
POST /auth/login
```
Body:
```json
{ "email": "user@example.com", "password": "secret" }
```
Response:
```json
{ "access_token": "eyJ...", "token_type": "bearer" }
```

### Get current user
```
GET /auth/me
Authorization: required
```

---

## Cards

### Search cards
```
GET /cards
```
Query parameters:

| Param | Type | Description |
|-------|------|-------------|
| `q` | string | Full-text search (name EN/JA, effect text) |
| `card_type` | `monster\|spell\|trap` | Filter by type |
| `attribute` | `dark\|light\|earth\|water\|fire\|wind\|divine` | Monster attribute |
| `monster_type` | `normal\|effect\|ritual\|fusion\|synchro\|xyz\|link\|pendulum\|...` | Monster sub-type |
| `race` | string | Monster race (e.g. `Warrior`, `Dragon`) |
| `archetype` | string | Archetype name substring |
| `level_min` / `level_max` | int | Level/rank range |
| `atk_min` / `atk_max` | int | ATK range |
| `def_min` / `def_max` | int | DEF range |
| `tcg_ban_status` | `unlimited\|semi-limited\|limited\|forbidden` | TCG ban status |
| `ocg_ban_status` | same | OCG ban status |
| `set_code` | string | Filter by set code (e.g. `DUNE`) |
| `rarity` | string | Filter by rarity |
| `sort` | `name\|atk\|def\|level\|popularity\|relevance` | Sort order |
| `page` | int | Page number (default: 1) |
| `page_size` | int | Results per page (default: 24, max: 100) |

Response:
```json
{
  "cards": [<Card>],
  "total": 12000,
  "page": 1,
  "page_size": 24,
  "pages": 500
}
```

### Get card by UUID
```
GET /cards/{card_id}
```
Returns a single `Card` object or 404.

### Get card by YGOProDeck ID (with upstream fallback)
```
GET /cards/by-id/{ygoprodeck_id}
```
Looks up the card locally first. If not found, fetches from YGOProDeck API, auto-imports it into the local DB, and returns it. Returns 404 only if neither local nor upstream has the card.

### Identify card from image
```
POST /cards/identify/image
Content-Type: multipart/form-data
```
Form field: `file` (image upload — JPG, PNG, WebP)

Response:
```json
{
  "candidates": [
    {
      "card": <Card>,
      "confidence": 0.95,
      "match_type": "ocr_name",
      "match_reason": "Fuzzy name match: 'Dark Magician'"
    }
  ],
  "ocr_text": "Dark Magician",
  "ocr_confidence": 0.92,
  "used_vision_fallback": false
}
```
Returns up to 5 candidates ranked by confidence.

### Identify card from text
```
POST /cards/identify/text
```
Body:
```json
{ "text": "Dark Magicin", "language": "en" }
```
Response: same as image identification (without OCR fields).

---

## Card Object Schema

```json
{
  "id": "uuid",
  "ygoprodeck_id": 46986414,
  "name_en": "Dark Magician",
  "name_ja": "ブラック・マジシャン",
  "card_type": "monster",
  "monster_type": "normal",
  "race": "Spellcaster",
  "attribute": "dark",
  "level": 7,
  "rank": null,
  "link_rating": null,
  "link_markers": null,
  "pendulum_scale": null,
  "atk": 2500,
  "def": 2100,
  "effect_text": "The ultimate wizard in terms of attack and defense.",
  "pendulum_text": null,
  "flavor_text": null,
  "archetype": "Dark Magician",
  "tcg_ban_status": "unlimited",
  "ocg_ban_status": "unlimited",
  "is_extra_deck": false,
  "views": 9823,
  "prints": [<CardPrint>],
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

### CardPrint Object
```json
{
  "id": "uuid",
  "set_code": "LDK2",
  "set_name": "Legendary Decks II",
  "card_number": "LDK2-ENY01",
  "rarity": "Common",
  "region": "TCG",
  "language": "en",
  "release_date": "2016-10-07",
  "image_url": "/card-images/46986414.jpg",
  "image_url_small": "/card-images/46986414_small.jpg",
  "image_url_cropped": "/card-images/46986414_cropped.jpg"
}
```

> Image URLs switch from CDN URLs (`https://images.ygoprodeck.com/...`) to local paths (`/card-images/...`) after the image download task completes.

---

## Decks

### List user's decks
```
GET /decks
Authorization: required
```

### Create deck
```
POST /decks
Authorization: required
```
Body:
```json
{
  "name": "Dark Magician",
  "description": "Classic spellcaster build",
  "format": "tcg",
  "archetype": "Dark Magician"
}
```
`format` values: `tcg`, `ocg`, `goat`, `speed`

### Get deck
```
GET /decks/{deck_id}
Authorization: required
```

### Update deck
```
PUT /decks/{deck_id}
Authorization: required
```

### Delete deck
```
DELETE /decks/{deck_id}
Authorization: required
```

### Add cards to deck
```
POST /decks/{deck_id}/cards
Authorization: required
```
Body:
```json
[
  { "card_id": "uuid", "zone": "main", "quantity": 3 },
  { "card_id": "uuid", "zone": "extra", "quantity": 1 }
]
```
`zone` values: `main`, `extra`, `side`

### Remove card from deck
```
DELETE /decks/{deck_id}/cards/{card_entry_id}
Authorization: required
```

### Save deck version (snapshot)
```
POST /decks/{deck_id}/versions
Authorization: required
```

### List deck versions
```
GET /decks/{deck_id}/versions
Authorization: required
```

### Export deck
```
GET /decks/{deck_id}/export?format=json
Authorization: required
```
`format` values: `json`, `text`

---

## Recommendations

### Recommend cards for a deck
```
POST /recommendations/cards
```
Body:
```json
{
  "deck_id": "uuid",
  "archetype": "Dark Magician",
  "format": "tcg",
  "explain": true,
  "limit": 10,
  "exclude_card_ids": ["uuid", "uuid"]
}
```
All fields optional except `format`. Provide either `deck_id` or `archetype` (or both).

Response:
```json
{
  "recommendations": [
    {
      "card": <Card>,
      "score": 0.87,
      "synergy_reason": "Key searcher for the archetype",
      "role": "starter/extender",
      "meta_relevance": "Strong in current format",
      "full_explanation": "..."
    }
  ],
  "meta_context": "Dark Magician is a consistent rogue strategy...",
  "deck_analysis": "Your deck is missing a search engine..."
}
```

### Recommend a full deck list
```
POST /recommendations/deck
```
Body:
```json
{
  "archetype": "Blue-Eyes",
  "format": "tcg",
  "playstyle": "aggressive",
  "limit": 40
}
```

### Meta overview
```
POST /recommendations/meta
```
Body:
```json
{ "format": "tcg", "limit": 10 }
```

### Explain a card in context
```
POST /recommendations/explain
```
Body:
```json
{
  "card_id": "uuid",
  "deck_id": "uuid",
  "archetype": "Dark Magician",
  "format": "tcg"
}
```
Response:
```json
{
  "card": <Card>,
  "explanation": "Dark Magician serves as the boss monster...",
  "token_count": 312
}
```

---

## Meta

### Get archetypes by card count
```
GET /meta/archetypes
```

### Get popular decks (from scraped sources)
```
GET /meta/popular-decks
```

### Get trends
```
GET /meta/trends
```

### Trigger meta scrape
```
POST /meta/rebuild
```

---

## Admin

All admin endpoints require an admin-role JWT token.

### Import cards from YGOProDeck
```
POST /admin/import/cards?limit=<int>
Authorization: admin required
```
Queues a Celery task to fetch all cards (~12k) from YGOProDeck and upsert them into the local DB. `limit` is optional (import all if omitted).

Response: `{"task_id": "...", "status": "queued"}`

Alternatively, run synchronously inside the container:
```bash
docker compose exec ai python scripts/import/import_cards.py --sync
```

### Download card images locally
```
POST /admin/download/images
Authorization: admin required
```
Queues a Celery task to download all card images from CDN to `./storage/card_images/` and update DB URLs to local paths.

### Generate card embeddings
```
POST /admin/index/embed
Authorization: admin required
```
Queues a Celery task to generate nomic-embed-text (768-dim) vectors for all cards and store them in the `card_embeddings` table.

### Run meta scraper
```
POST /admin/scrape/run?source_id=<uuid>
Authorization: admin required
```
Scrapes all active meta sources (or a specific one).

### List background jobs
```
GET /admin/jobs?status=<status>&limit=50
Authorization: admin required
```
`status` values: `pending`, `running`, `completed`, `failed`, `cancelled`

### Analytics
```
GET /admin/analytics?days=30
Authorization: admin required
```
Returns event counts by type and total AI token usage for the last N days.

---

## Static Files

Card images are served directly by the API after the download task completes:

```
GET /card-images/{ygoprodeck_id}.jpg          # full resolution
GET /card-images/{ygoprodeck_id}_small.jpg    # thumbnail
GET /card-images/{ygoprodeck_id}_cropped.jpg  # artwork crop
```

---

## Health Check
```
GET /health
```
Response: `{"status": "ok", "service": "ai"}`
