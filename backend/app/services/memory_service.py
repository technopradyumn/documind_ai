"""
Memory Service — production refactor of mem_agent/mem.py.
Uses mem0 with Qdrant vector store for per-user persistent memory.
"""
import logging
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MemoryService:
    """Lazy-initialised mem0 memory with graceful degradation."""

    def __init__(self):
        self._memory = None

    def _get_memory(self):
        if self._memory is not None:
            return self._memory
        try:
            from mem0 import Memory
            config = {
                "version": "v1.1",
                "embedding": {
                    "provider": "gemini",
                    "config": {
                        "api_key": settings.gemini_api_key,
                        "model": "models/text-embedding-004",
                    },
                },
                "llm": {
                    "provider": "gemini",
                    "config": {
                        "api_key": settings.gemini_api_key,
                        "model": settings.gemini_model_flash,
                    },
                },
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "host": "localhost",
                        "port": 6333,
                        "collection_name": "documind_memory",
                    },
                },
            }
            self._memory = Memory.from_config(config)
            logger.info("mem0 memory initialised.")
        except Exception as e:
            logger.warning("mem0 init failed (memory disabled): %s", e)
        return self._memory

    def search(self, query: str, user_id: str) -> str:
        """Return formatted string of relevant past memories."""
        memory = self._get_memory()
        if not memory:
            return ""
        try:
            results = memory.search(query=query, user_id=user_id)
            items = results.get("results", [])
            if not items:
                return ""
            return "\n".join(f"- {m.get('memory', '')}" for m in items[:5])
        except Exception as e:
            logger.warning("Memory search error (non-fatal): %s", e)
            return ""

    def save(self, user_id: str, user_message: str, ai_response: str) -> None:
        """Persist a conversation turn to memory asynchronously."""
        memory = self._get_memory()
        if not memory:
            return
        try:
            memory.add(
                user_id=user_id,
                messages=[
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": ai_response},
                ],
            )
        except Exception as e:
            logger.warning("Memory save error (non-fatal): %s", e)


# Singleton
memory_service = MemoryService()
