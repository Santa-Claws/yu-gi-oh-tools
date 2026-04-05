import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.redis import close_redis

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    os.makedirs(settings.card_images_dir, exist_ok=True)
    logger.info("startup", env=settings.app_env)
    yield
    await close_redis()
    logger.info("shutdown")


settings = get_settings()

app = FastAPI(
    title="Yu-Gi-Oh Tools API",
    description="AI-powered Yu-Gi-Oh card identification, deck building, and recommendation engine.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://web:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ───────────────────────────────────────────────────────────────────
from app.api.routes.auth import router as auth_router
from app.api.routes.cards import router as cards_router
from app.api.routes.decks import router as decks_router
from app.api.routes.recommendations import router as recommend_router
from app.api.routes.meta import router as meta_router
from app.api.routes.admin import router as admin_router

app.include_router(auth_router)
app.include_router(cards_router)
app.include_router(decks_router)
app.include_router(recommend_router)
app.include_router(meta_router)
app.include_router(admin_router)

app.mount(
    "/card-images",
    StaticFiles(directory=settings.card_images_dir),
    name="card-images",
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ai"}
