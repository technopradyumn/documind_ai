from pydantic_settings import BaseSettings
from functools import lru_cache


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

    # Models
    gemini_model_flash: str = "gemini-3.1-flash-lite-preview"
    gemini_model_pro: str = "gemini-3.1-flash-lite-preview"
    gemini_embedding_model: str = "text-embedding-004"

    # App
    qdrant_collection: str = "documind"
    uploads_dir: str = "uploads"
    voice_enabled: bool = True
    max_agent_iterations: int = 10

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
