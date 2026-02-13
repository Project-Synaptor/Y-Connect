"""Configuration management for Y-Connect WhatsApp Bot"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application Settings
    app_name: str = "y-connect-whatsapp-bot"
    app_env: str = "development"
    log_level: str = "INFO"
    
    # WhatsApp Business API
    whatsapp_api_url: str = "https://graph.facebook.com/v18.0"
    whatsapp_access_token: str
    whatsapp_phone_number_id: str
    whatsapp_verify_token: str
    whatsapp_app_secret: str
    
    # LLM API
    llm_provider: str = "openai"
    llm_api_key: str
    llm_model: str = "gpt-4"
    llm_api_url: str = "https://api.openai.com/v1"
    
    # Vector Database
    vector_db_provider: str = "qdrant"
    vector_db_url: str = "http://localhost:6333"
    vector_db_api_key: Optional[str] = None
    vector_db_index_name: str = "y-connect-schemes"
    vector_embedding_dimension: int = 384
    
    # PostgreSQL Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "y_connect"
    postgres_user: str = "postgres"
    postgres_password: str
    postgres_pool_size: int = 10
    postgres_max_overflow: int = 20
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_session_ttl: int = 86400  # 24 hours in seconds
    
    # Session Management
    session_expiry_hours: int = 24
    
    # Performance Settings
    max_concurrent_sessions: int = 100
    response_timeout_seconds: int = 10
    rag_top_k_results: int = 5
    rag_confidence_threshold: float = 0.7
    
    # Message Settings
    max_message_length: int = 1600
    chunk_size_tokens: int = 512
    chunk_overlap_tokens: int = 50
    
    @property
    def postgres_url(self) -> str:
        """Construct PostgreSQL connection URL"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    @property
    def redis_url(self) -> str:
        """Construct Redis connection URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.app_env.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.app_env.lower() == "development"


def get_settings() -> Settings:
    """Get settings instance - allows for lazy loading"""
    return Settings()
