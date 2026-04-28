"""
Documents route — PDF upload → async Qdrant indexing via RQ.
POST /api/documents/upload
GET  /api/documents/list
"""
import os
import logging
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models.schemas import DocumentUploadResponse
from app.services.queue_service import queue_service
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["Documents"])
settings = get_settings()

UPLOADS_DIR = Path(settings.uploads_dir)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    collection: str = Form(default="documind"),
):
    """Accept a PDF, save it, and enqueue an async indexing job."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    save_path = UPLOADS_DIR / file.filename
    contents = await file.read()
    with open(save_path, "wb") as f:
        f.write(contents)
    logger.info("Saved upload: %s (%d bytes)", save_path, len(contents))

    job_id = queue_service.enqueue_indexing(
        file_path=str(save_path),
        collection_name=collection,
    )

    return DocumentUploadResponse(
        job_id=job_id,
        filename=file.filename,
        status="queued",
        collection=collection,
    )


@router.get("/list")
async def list_documents():
    """Return filenames of all uploaded PDFs."""
    files = [f.name for f in UPLOADS_DIR.glob("*.pdf")]
    return {"documents": files, "count": len(files)}
