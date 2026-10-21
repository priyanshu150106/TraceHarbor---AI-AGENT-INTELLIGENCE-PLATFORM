"""
TraceHarbor API — Application Settings

Loads configuration from environment variables using Pydantic Settings.
See .env.example at the project root for all available variables.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------- Database ----------
    database_url: str = (
        "postgresql+asyncpg://th:change_me_in_production@localhost:5432/traceharbor"
    )

    # ---------- Redis ----------
    redis_url: str = "redis://localhost:6379/0"

    # ---------- JWT ----------
    jwt_secret: str = "change_me_generate_a_random_secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # ---------- Server ----------
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    log_level: str = "INFO"

    # ---------- App ----------
    app_name: str = "TraceHarbor"
    app_version: str = "0.1.0"
    debug: bool = False

    # ---------- Evaluation & Datasets ----------
    max_dataset_upload_size_bytes: int = 5 * 1024 * 1024  # 5 MB
    max_dataset_cases: int = 500
    max_concurrent_experiments: int = 2

    # ---------- LLM-as-Judge (Optional) ----------
    llm_judge_provider: str = "openai"
    llm_judge_model: str = "gpt-4o-mini"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None


settings = Settings()
