"""
Session Service — Manages chat session metadata in MongoDB.
"""
import logging
from datetime import datetime
from typing import List, Optional
from pymongo import MongoClient
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class SessionService:
    def __init__(self):
        self._client = None
        self._db = None
        self._collection = None

    def _get_collection(self):
        if self._collection is not None:
            return self._collection
        try:
            self._client = MongoClient(settings.mongodb_uri)
            self._db = self._client.get_database("documind")
            self._collection = self._db.get_collection("sessions")
            # Create index on user_id
            self._collection.create_index("user_id")
            logger.info("Session service initialised with MongoDB.")
        except Exception as e:
            logger.error("Failed to init MongoDB for sessions: %s", e)
        return self._collection

    def list_sessions(self, user_id: str) -> List[dict]:
        col = self._get_collection()
        if col is None: return []
        try:
            cursor = col.find({"user_id": user_id}).sort("last_updated", -1)
            sessions = []
            for doc in cursor:
                doc["id"] = doc.pop("_id") # Use MongoDB ID as session ID string if needed, or custom ID
                sessions.append(doc)
            return sessions
        except Exception as e:
            logger.error("Failed to list sessions: %s", e)
            return []

    def save_session(self, session_id: str, user_id: str, title: str) -> bool:
        col = self._get_collection()
        if col is None: return False
        try:
            col.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "session_id": session_id,
                        "user_id": user_id,
                        "title": title,
                        "last_updated": datetime.utcnow()
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error("Failed to save session: %s", e)
            return False

    def delete_session(self, session_id: str) -> bool:
        col = self._get_collection()
        if col is None: return False
        try:
            col.delete_one({"session_id": session_id})
            return True
        except Exception as e:
            logger.error("Failed to delete session metadata: %s", e)
            return False

session_service = SessionService()
