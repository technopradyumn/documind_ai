from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from app.services.session_service import session_service

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])

class SessionSchema(BaseModel):
    session_id: str
    user_id: str
    title: str
    last_updated: datetime

class SessionCreate(BaseModel):
    session_id: str
    user_id: str
    title: str

@router.get("/{user_id}")
async def get_sessions(user_id: str):
    return {"sessions": session_service.list_sessions(user_id)}

@router.post("")
async def create_or_update_session(data: SessionCreate):
    success = session_service.save_session(data.session_id, data.user_id, data.title)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save session")
    return {"status": "success"}

@router.delete("/{session_id}")
async def delete_session(session_id: str):
    success = session_service.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete session")
    return {"status": "deleted"}
