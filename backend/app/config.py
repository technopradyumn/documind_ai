from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path


def _find_env_file() -> str:
    """Search for .env in CWD and parent directories (up to 2 levels)."""
    for candidate in [
        Path(".env"),
        Path("../.env"),
        Path(__file__).parent.parent.parent / ".env",  # project root from backend/app/
    ]:
        if candidate.exists():
            return str(candidate)
    return ".env"  # fallback — let pydantic-settings raise if missing


class Settings(BaseSettings):
    # LLM
    gemini_api_key: str
    openai_api_key: str = ""
    deepseek_api_key: str = ""

    # Infra
    mongodb_uri: str = "mongodb://admin:admin@localhost:27017"
    qdrant_url: str = "http://localhost:6333"
    redis_url: str = "redis://localhost:6379"

    # Neo4j (optional for graph memory)
    neo4j_uri: str = ""
    neo4j_username: str = ""
    neo4j_password: str = ""

    # Models — use real, stable Gemini model identifiers
    gemini_model_flash: str = "gemini-2.0-flash"
    gemini_model_pro: str = "gemini-2.0-flash"
    # Embedding: models/text-embedding-004 is the stable GA endpoint
    gemini_embedding_model: str = "models/text-embedding-004"

    # App
    qdrant_collection: str = "documind"
    uploads_dir: str = "uploads"
    voice_enabled: bool = True
    max_agent_iterations: int = 10

    class Config:
        env_file = _find_env_file()
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
