# Yu-Gi-Oh Tools

AI-powered Yu-Gi-Oh card identification, deck builder, and recommendation engine.

## Stack

| Service | Technology |
|---------|-----------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS, TanStack Query |
| Backend API | FastAPI, SQLAlchemy, Pydantic v2 |
| Task queue | Celery (worker + beat) |
| Database | PostgreSQL 16 + pgvector |
| Cache / broker | Redis 7 |
| AI models | Ollama (llava:7b vision, qwen2.5:14b text, nomic-embed-text embeddings) |

## Prerequisites

- Docker + Docker Compose (v2)
- Git
- Ollama running on the host machine with the required models pulled:
  ```
  ollama pull llava:7b
  ollama pull qwen2.5:14b
  ollama pull nomic-embed-text
  ```

## Production Deployment

### 1. Clone the repo

```bash
git clone https://github.com/Santa-Claws/yu-gi-oh-tools.git
cd yu-gi-oh-tools
```

### 2. Create `.env`

Copy and fill in all required values:

```bash
cp .env.example .env   # or create from scratch
```

Minimum required `.env`:

```env
# Database
DATABASE_URL=postgresql+asyncpg://yugioh:yugioh_secret@db:5432/yugioh
POSTGRES_USER=yugioh
POSTGRES_PASSWORD=yugioh_secret
POSTGRES_DB=yugioh

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# Auth (change this!)
JWT_SECRET=change_this_to_a_random_secret

# Ollama — host machine accessible from containers
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_VISION_MODEL=llava:7b
OLLAMA_TEXT_MODEL=qwen2.5:14b
OLLAMA_EMBED_MODEL=nomic-embed-text

# Frontend URL (set to server IP or domain)
NEXT_PUBLIC_API_URL=http://192.168.1.100:8000
AI_SERVICE_URL=http://ai:8000
```

### 3. Start all services

```bash
docker compose up -d --build
```

All 6 services will start: `db`, `redis`, `ai`, `worker`, `beat`, `web`.

Check health:

```bash
docker compose ps
curl http://localhost:8000/health   # {"status":"ok","service":"ai"}
curl http://localhost:3000/api/health
```

### 4. Populate the card database

The database starts empty. Run the card import to pull ~12k cards from YGOProDeck:

```bash
docker compose exec ai python scripts/import/import_cards.py --sync
```

This takes 1–3 minutes. When complete you'll see `Import complete: {"imported": 12000}`.

Verify:

```bash
curl "http://localhost:8000/cards?q=Dark+Magician" | jq '.total'
```

### 5. Download card images locally

After import, download all card images to local storage (so the API serves them without CDN dependency):

```bash
# Create an admin user first (see Admin Setup below), then:
curl -X POST http://localhost:8000/admin/download/images \
  -H "Authorization: Bearer <admin_token>"
```

This runs as a background Celery task. Images are saved to `./storage/card_images/` and served at `http://localhost:8000/card-images/{ygoprodeck_id}.jpg`.

### 6. Generate card embeddings (for semantic search + recommendations)

```bash
curl -X POST http://localhost:8000/admin/index/embed \
  -H "Authorization: Bearer <admin_token>"
```

---

## Admin Setup

### Create the first admin user

1. Register a user via the API:
   ```bash
   curl -X POST http://localhost:8000/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@example.com","password":"yourpassword","display_name":"Admin"}'
   ```

2. Promote to admin directly in the database:
   ```bash
   docker compose exec db psql -U yugioh -d yugioh -c \
     "UPDATE users SET role='admin' WHERE email='admin@example.com';"
   ```

3. Get a JWT token:
   ```bash
   curl -X POST http://localhost:8000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@example.com","password":"yourpassword"}'
   ```
   Copy the `access_token` from the response.

---

## Updating the Deployment

When new code is pushed to `main`:

```bash
git pull
docker compose up -d --build
```

If the database schema changed (new columns added to `packages/db/init/`), you must reset the DB:

```bash
docker compose down --volumes
docker compose up -d --build
# Then re-run the card import (step 4 above)
```

---

## Service URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API docs (dev only) | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

---

## Storage

All persistent data lives in:

| Path | Contents |
|------|----------|
| `./storage/card_images/` | Downloaded card images (served at `/card-images/`) |
| `./storage/uploads/` | User-uploaded images for card identification |
| `./storage/exports/` | Exported deck files |
| `./storage/scraped/` | Scraped meta content |
| Docker volume `postgres_data` | PostgreSQL data |
| Docker volume `redis_data` | Redis AOF data |

---

## Architecture Overview

```
Browser → Next.js (3000) → FastAPI AI service (8000) → PostgreSQL + Redis
                                     ↓
                               Celery Worker
                                     ↓
                        Ollama (host:11434) / YGOProDeck API
```

See `docs/ARCHITECTURE.md` for full system design and `docs/API.md` for the complete API reference.
