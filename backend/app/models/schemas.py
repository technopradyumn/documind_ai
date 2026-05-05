from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime


# ── Agent ─────────────────────────────────────────────────────────────────────
class AgentStep(BaseModel):
    step: Literal["START", "PLAN", "TOOL", "OBSERVE", "OUTPUT"]
    content: Optional[str] = None
    tool: Optional[str] = None
    input: Optional[str] = None


# ── Chat ──────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    user_id: str
    session_id: str = "session-1"
    collection: str = "documind"
    model: str = "gemini"  # Options: gemini, openai, deepseek


class StepDetail(BaseModel):
    step: str
    content: Optional[str] = None
    tool: Optional[str] = None
    input: Optional[str] = None
    result: Optional[str] = None


class ChatResponse(BaseModel):
    message: str
    steps: List[StepDetail] = []
    user_id: str
    session_id: str


# ── Documents ─────────────────────────────────────────────────────────────────
class DocumentUploadResponse(BaseModel):
    job_id: str
    filename: str
    status: str
    collection: str


class DocumentInfo(BaseModel):
    filename: str
    collection: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


# ── Jobs ──────────────────────────────────────────────────────────────────────
class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None


# ── Voice ─────────────────────────────────────────────────────────────────────
class VoiceSTTResponse(BaseModel):
    transcript: str


class VoiceTTSRequest(BaseModel):
    text: str
    voice: str = "nova"


# ── Health ────────────────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    services: dict = {}
