"""
Documents route — PDF upload → async Qdrant indexing via RQ.
POST /api/documents/upload
GET  /api/documents/list
"""
import logging
import re
import time
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

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def _safe_filename(filename: str) -> str:
    """Sanitize filename and prepend timestamp to avoid collisions."""
    # Keep only safe characters
    name = re.sub(r"[^\w\-. ]", "_", Path(filename).stem)
    name = name.strip().replace(" ", "_") or "document"
    ts = int(time.time())
    return f"{ts}_{name}.pdf"


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    collection: str = Form(default="documind"),
):
    """Accept a PDF, save it, and enqueue an async indexing job."""
    # Validate file type
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported. Please upload a .pdf file.",
        )

    # Read contents (limit size)
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {MAX_FILE_SIZE // (1024*1024)} MB.",
        )

    safe_name = _safe_filename(file.filename)
    save_path = UPLOADS_DIR / safe_name

    try:
        with open(save_path, "wb") as f:
            f.write(contents)
        logger.info("Saved upload: %s (%d bytes)", save_path, len(contents))
    except OSError as e:
        logger.error("Failed to save uploaded file: %s", e)
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")

    try:
        job_id = queue_service.enqueue_indexing(
            file_path=str(save_path),
            collection_name=collection,
        )
    except Exception as e:
        logger.error("Failed to enqueue indexing job: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to start indexing: {e}")

    return DocumentUploadResponse(
        job_id=job_id,
        filename=file.filename,
        status="queued",
        collection=collection,
    )


@router.get("/list")
async def list_documents():
    """Return filenames of all uploaded PDFs."""
    try:
        files = [f.name for f in UPLOADS_DIR.glob("*.pdf")]
        return {"documents": files, "count": len(files)}
    except Exception as e:
        logger.error("Failed to list documents: %s", e)
        return {"documents": [], "count": 0, "error": str(e)}
