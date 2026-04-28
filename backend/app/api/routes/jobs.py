"""
Jobs route — poll async indexing job status.
GET /api/jobs/{job_id}
"""
from fastapi import APIRouter
from app.models.schemas import JobStatusResponse
from app.services.queue_service import queue_service

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Return current status and result of an RQ indexing job."""
    info = queue_service.get_job_status(job_id)
    return JobStatusResponse(
        job_id=job_id,
        status=info.get("status", "unknown"),
        result=info.get("result"),
        error=info.get("error"),
    )
