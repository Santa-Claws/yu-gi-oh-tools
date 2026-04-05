# Getting Started

## Prerequisites

- Docker & Docker Compose
- 16 GB RAM recommended (Llama 3.2 Vision 11B needs ~8–10 GB VRAM or will run on CPU)

## First-time setup

```bash
# 1. Copy environment config
cp .env.example .env
# Edit .env if needed (defaults work for local dev)

# 2. Start all services
docker compose up -d

# 3. Wait for Ollama to be ready, then pull the models
docker compose exec ollama ollama pull llama3.2-vision:11b
docker compose exec ollama ollama pull llama3.2:3b
docker compose exec ollama ollama pull nomic-embed-text

# 4. Import the card database (~13k cards from YGOProDeck)
docker compose exec ai python scripts/import/import_cards.py --sync
# Or trigger via the Admin UI at http://localhost:3000/admin

# 5. Generate embeddings (requires Ollama running + cards imported)
#    Trigger via Admin UI → "Rebuild Embeddings"
```

## Access

| Service | URL |
|---------|-----|
| Web app | http://localhost:3000 |
| FastAPI docs | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |
| Ollama | http://localhost:11434 |

## Development workflow

```bash
# FastAPI hot-reload is enabled by default in dev mode
# Edit files in apps/ai/ and the server reloads automatically

# For Next.js dev server outside Docker:
cd apps/web
npm install
npm run dev

# Run backend tests
docker compose exec ai pytest

# Run frontend unit tests
cd apps/web && npm test

# Run e2e tests (requires running app)
cd apps/web && npm run e2e
```

## Home server deployment

```bash
# Use .env with production secrets
cp .env.example .env.production
# Set JWT_SECRET, POSTGRES_PASSWORD, APP_ENV=production

docker compose --env-file .env.production up -d --build
```

## Build phases

The app is built in phases — see the plan doc. After first-time setup:

1. **Phase 1** (complete): infrastructure, schema, auth
2. **Phase 2**: card browser + search (import cards first)
3. **Phase 3**: deck builder
4. **Phase 4**: embeddings + recommendations (pull Ollama models first)
5. **Phase 5**: OCR/image identification
6. **Phase 6**: meta scraping
7. **Phase 7**: analytics, polish
