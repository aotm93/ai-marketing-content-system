from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # AI Provider Configuration
    primary_ai_provider: str = "openai"
    primary_ai_base_url: str = "https://api.openai.com/v1"
    primary_ai_api_key: str
    primary_ai_text_model: str = "gpt-4o"
    primary_ai_image_model: str = "dall-e-3"

    # Fallback AI Provider
    fallback_ai_provider: Optional[str] = None
    fallback_ai_base_url: Optional[str] = None
    fallback_ai_api_key: Optional[str] = None
    fallback_ai_text_model: Optional[str] = None
    fallback_ai_image_model: Optional[str] = None

    # Database
    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 50

    # WordPress
    wordpress_url: str
    wordpress_username: str
    wordpress_password: str
    wordpress_api_enabled: bool = True

    # SEO Plugin
    seo_plugin: str = "yoast"
    seo_api_key: Optional[str] = None

    # Keyword Research
    keyword_api_provider: Optional[str] = None
    keyword_api_key: Optional[str] = None
    keyword_api_base_url: Optional[str] = None

    # System
    environment: str = "development"
    log_level: str = "INFO"
    max_concurrent_agents: int = 5
    content_generation_timeout: int = 600

    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090

    # Admin Authentication
    admin_password: str
    admin_session_secret: str
    admin_session_expire_minutes: int = 1440  # 24 hours


settings = Settings()
