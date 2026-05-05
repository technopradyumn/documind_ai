"""
Documents route — PDF upload → async Qdrant indexing via RQ.
POST /api/documents/upload
GET  /api/documents/list
"""
import logging
import re
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models.schemas import DocumentUploadResponse
from app.services.queue_service import queue_service
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["Documents"])
settings = get_settings()

UPLOADS_DIR = Path(settings.uploads_dir)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


def _safe_filename(filename: str) -> str:
    """Sanitize filename and prepend timestamp to avoid collisions."""
    # Keep only safe characters
    name = re.sub(r"[^\w\-. ]", "_", Path(filename).stem)
    name = name.strip().replace(" ", "_") or "document"
    ts = int(time.time())
    return f"{ts}_{name}.pdf"


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    collection: str = Form(default="documind"),
    user_id: str = Form(...),
):
    """Accept a PDF, save it, and enqueue an async indexing job."""
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Read contents (limit size) to check
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large.")
    
    # Create collection-specific directory
    col_dir = UPLOADS_DIR / collection
    col_dir.mkdir(parents=True, exist_ok=True)

    timestamp = int(time.time())
    target_path = col_dir / f"{timestamp}_{file.filename}"
    
    try:
        with target_path.open("wb") as buffer:
            buffer.write(contents)
        logger.info("Saved file: %s (collection: %s)", target_path.name, collection)
    except Exception as e:
        logger.error("Failed to save upload: %s", e)
        raise HTTPException(status_code=500, detail="Could not save file")

    # Enqueue indexing job
    from app.services.rag_service import rag_service
    from app.services.queue_service import queue_service
    # We'll use the existing queue_service if available, or direct redis rq
    try:
        from app.api.routes.documents import documind_queue
    except:
        from app.services.queue_service import queue_service as documind_queue

    import uuid
    job_id = str(uuid.uuid4())
    
    # For now we use rag_service.index_pdf directly via RQ
    from app.main import settings # or config
    from redis import Redis
    from rq import Queue
    q = Queue("documind", connection=Redis.from_url(get_settings().redis_url))
    job = q.enqueue(
        rag_service.index_pdf,
        file_path=str(target_path),
        collection_name=collection,
        job_id=job_id,
        result_ttl=3600,
    )

    # Update session metadata
    try:
        from app.services.session_service import session_service
        session_service.save_session(collection, user_id, f"Docs: {file.filename}")
    except: pass

    return {"status": "queued", "job_id": job.get_id(), "filename": target_path.name}


@router.get("/list")
async def list_documents(collection: Optional[str] = None):
    """Return filenames of uploaded PDFs, optionally filtered by collection."""
    try:
        if collection:
            search_dir = UPLOADS_DIR / collection
            if not search_dir.exists():
                return {"documents": [], "count": 0}
            files = [f.name for f in search_dir.glob("*.pdf")]
        else:
            # Fallback: search all (for backward compatibility or global view)
            files = [f.name for f in UPLOADS_DIR.rglob("*.pdf")]
        
        return {"documents": files, "count": len(files)}
    except Exception as e:
        logger.error("Failed to list documents: %s", e)
        return {"documents": [], "count": 0, "error": str(e)}


@router.delete("/{filename}")
async def delete_document(filename: str, collection: str = "documind"):
    """Delete a PDF file and its corresponding vectors in Qdrant."""
    # Search in collection-specific directory
    col_dir = UPLOADS_DIR / collection
    target = col_dir / filename
    
    if not target.exists():
        # Try glob in case the filename provided is partial or missing prefix
        matches = list(col_dir.glob(f"*{filename}*"))
        if not matches:
            raise HTTPException(status_code=404, detail=f"File {filename} not found in collection {collection}")
        target = matches[0]

    try:
        from app.services.rag_service import rag_service
        # 1. Delete from Qdrant
        rag_service.delete_document(file_path=str(target), collection_name=collection)
        # 2. Delete from disk
        target.unlink()
        logger.info("Deleted document: %s from collection: %s", target.name, collection)
        return {"status": "deleted", "filename": target.name}
    except Exception as e:
        logger.error("Failed to delete document %s: %s", filename, e)
        raise HTTPException(status_code=500, detail=f"Deletion failed: {e}")


@router.delete("/clear/{collection}")
async def clear_collection(collection: str):
    """Delete all documents and the entire collection in Qdrant."""
    try:
        from app.services.rag_service import rag_service
        # 1. Delete Qdrant collection
        rag_service.delete_collection(collection_name=collection)
        # 2. Delete collection directory
        col_dir = UPLOADS_DIR / collection
        if col_dir.exists():
            import shutil
            shutil.rmtree(col_dir)
            logger.info("Deleted directory: %s", col_dir)
        
        return {"status": "cleared", "collection": collection}
    except Exception as e:
        logger.error("Failed to clear collection %s: %s", collection, e)
        raise HTTPException(status_code=500, detail=f"Clear failed: {e}")
