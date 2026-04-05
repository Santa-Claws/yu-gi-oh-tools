import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
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
    logger.info("startup", env=settings.app_env)
    yield
    await close_redis()
    logger.info("shutdown")


settings = get_settings()

# Parse CORS origins — "*" means allow all (alpha/dev), otherwise comma-separated list
_raw_origins = settings.cors_origins.strip()
_allow_all = _raw_origins == "*"
_cors_origins = [] if _allow_all else [o.strip() for o in _raw_origins.split(",")]

app = FastAPI(
    title="Yu-Gi-Oh Tools API",
    description="AI-powered Yu-Gi-Oh card identification, deck building, and recommendation engine.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    # allow_origins=["*"] + allow_credentials=True is invalid; use allow_origin_regex instead
    allow_origins=_cors_origins,
    allow_origin_regex=r".*" if _allow_all else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = (time.monotonic() - start) * 1000
    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round(duration_ms, 1),
        client=request.client.host if request.client else None,
    )
    return response


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

os.makedirs(settings.card_images_dir, exist_ok=True)
app.mount(
    "/card-images",
    StaticFiles(directory=settings.card_images_dir),
    name="card-images",
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ai"}
