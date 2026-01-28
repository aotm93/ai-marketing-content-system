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
    primary_ai_api_key: Optional[str] = None
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
    wordpress_url: Optional[str] = None
    wordpress_username: Optional[str] = None
    wordpress_password: Optional[str] = None
    wordpress_api_enabled: bool = True

    # SEO Plugin (P0-12: rank_math support added)
    seo_plugin: str = "rank_math"  # Options: rank_math, yoast, aioseo
    seo_api_key: Optional[str] = None

    # Keyword Research
    keyword_api_provider: Optional[str] = None
    keyword_api_key: Optional[str] = None
    keyword_api_username: Optional[str] = None  # Added for DataForSEO (Email)
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

    # ==================== Autopilot Settings (P0-13) ====================
    
    # Core Autopilot Toggle
    autopilot_enabled: bool = False
    autopilot_mode: str = "standard"  # conservative, standard, aggressive
    
    # Frequency Controls
    publish_interval_minutes: int = 60  # Minutes between publications
    max_posts_per_day: int = 5          # Daily publication limit
    
    # Concurrency
    max_concurrent_jobs: int = 2        # Parallel job execution limit
    job_timeout_seconds: int = 600      # Single job timeout
    
    # Retry Configuration
    max_job_retries: int = 3
    retry_base_delay_seconds: int = 30
    
    # Publishing Behavior
    auto_publish: bool = False          # True=直发, False=草稿
    default_post_status: str = "draft"  # draft, pending, publish
    
    # Quality Gates
    require_seo_score: int = 60         # Minimum SEO score (0-100)
    require_word_count: int = 500       # Minimum content length
    duplication_threshold: float = 0.85 # Max similarity for duplicate detection
    
    # Cost Protection
    max_tokens_per_day: Optional[int] = 100000  # Daily token limit
    pause_on_consecutive_errors: int = 3        # Auto-pause threshold
    
    # Active Hours
    active_hours_start: int = 8         # Start hour (0-23)
    active_hours_end: int = 22          # End hour (0-23)

    # ==================== Google Search Console (P1) ====================
    
    # GSC Site URL
    gsc_site_url: Optional[str] = None
    
    # Authentication
    gsc_auth_method: str = "service_account"  # service_account or oauth
    gsc_credentials_path: Optional[str] = None
    gsc_credentials_json: Optional[str] = None
    
    # Data Sync
    gsc_sync_days_back: int = 28
    gsc_sync_interval_hours: int = 24
    gsc_enabled: bool = False


settings = Settings()
