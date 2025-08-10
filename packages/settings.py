"""Central settings using Pydantic BaseSettings"""
from pydantic import BaseSettings
from functools import lru_cache
from typing import List

class Settings(BaseSettings):
    openai_api_key: str | None = None
    openai_chat_model: str = 'gpt-4o'
    openai_embed_model: str = 'text-embedding-3-large'
    database_url: str = 'postgresql+psycopg://postgres:postgres@localhost:5432/ai_irule'
    object_store: str = 'local'
    object_store_path: str = './storage'
    vector_db: str = 'pgvector'
    embed_batch_size: int = 64
    max_context_tokens: int = 120000
    langfuse_enabled: bool = False
    allowlist_web_search: bool = False
    tenancy_mode: str = 'single'
    max_file_size_mb: int = 5
    parser_timeout_seconds: int = 10
    enable_reranker: bool = False
    reranker_model: str | None = None
    enable_test_generation: bool = False
    max_retrieval_chunks: int = 24
    guarded_output_schema_enforce: bool = True
    fallback_models: List[str] = ['gpt-4o-mini','gpt-4o']
    embed_dim: int = 3072
    rate_limit_per_min: int = 120
    rate_limit_burst: int = 40

    class Config:
        env_file = '.env'
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
