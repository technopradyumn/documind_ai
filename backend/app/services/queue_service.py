"""
Queue Service — sourced from rag_queue/client + rag_queue/server.py.
Manages Redis RQ job submission for async PDF indexing tasks.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class QueueService:
    def __init__(self):
        self._queue = None

    def _get_queue(self):
        if self._queue is not None:
            return self._queue
        try:
            from redis import Redis
            from rq import Queue
            from app.config import get_settings
            settings = get_settings()
            redis_conn = Redis.from_url(settings.redis_url)
            self._queue = Queue("documind", connection=redis_conn)
            logger.info("RQ queue 'documind' connected.")
        except Exception as e:
            logger.warning("Redis/RQ unavailable (%s). Jobs will run synchronously.", e)
        return self._queue

    def enqueue_indexing(self, file_path: str, collection_name: str) -> str:
        """
        Submit a PDF indexing job.
        Returns a job_id if async, or 'sync-done' if Redis unavailable.
        """
        from app.workers.indexing_worker import run_indexing_job
        queue = self._get_queue()
        if queue:
            job = queue.enqueue(run_indexing_job, file_path, collection_name, job_timeout=300)
            return job.id
        else:
            # Synchronous fallback
            run_indexing_job(file_path, collection_name)
            return "sync-done"

    def get_job_status(self, job_id: str) -> dict:
        """Fetch job status and result from RQ."""
        if job_id == "sync-done":
            return {"status": "finished", "result": {"status": "success"}}
        queue = self._get_queue()
        if not queue:
            return {"status": "unknown", "error": "Queue not available"}
        try:
            job = queue.fetch_job(job_id)
            if not job:
                return {"status": "not_found"}
            status = job.get_status()
            result = job.result if status == "finished" else None
            error = str(job.exc_info) if job.exc_info else None
            return {"status": str(status), "result": result, "error": error}
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Singleton
queue_service = QueueService()
