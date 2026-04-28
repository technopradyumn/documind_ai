"""
DocuMind AI — FastAPI application entrypoint.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.api.routes import chat, documents, jobs, voice
from app.models.schemas import HealthResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    Path(settings.uploads_dir).mkdir(parents=True, exist_ok=True)
    logger.info("DocuMind AI started. Uploads dir: %s", settings.uploads_dir)
    yield
    logger.info("DocuMind AI shutting down.")


app = FastAPI(
    title="DocuMind AI",
    description=(
        "Production-grade agentic document intelligence platform. "
        "Upload PDFs, ask questions, get step-by-step reasoned answers with memory."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(jobs.router)
app.include_router(voice.router)


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health():
    from app.services.voice_service import voice_service
    return HealthResponse(
        status="ok",
        services={
            "qdrant": settings.qdrant_url,
            "mongodb": settings.mongodb_uri,
            "redis": settings.redis_url,
            "voice": voice_service.capabilities,
        },
    )


@app.get("/", tags=["Root"])
async def root():
    return {
        "app": "DocuMind AI",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/api/health",
    }
