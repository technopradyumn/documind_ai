"""
Indexing Worker — the RQ background job function.
Called by queue_service.enqueue_indexing().
"""
import logging
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)


def run_indexing_job(file_path: str, collection_name: str) -> dict:
    """RQ worker entry point: index a PDF into Qdrant."""
    logger.info("Worker: indexing '%s' → '%s'", file_path, collection_name)
    result = rag_service.index_pdf(file_path=file_path, collection_name=collection_name)
    logger.info("Worker: done — %s", result)
    return result
