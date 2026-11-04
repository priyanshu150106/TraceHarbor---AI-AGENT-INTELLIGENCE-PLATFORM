"""
TraceHarbor API — Application Settings

Loads configuration from environment variables using Pydantic Settings.
See .env.example at the project root for all available variables.
"""

from pydantic import field_validator
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
    db_pool_size: int = 5
    db_max_overflow: int = 5
    db_pool_timeout: float = 30.0
    db_pool_recycle: int = 300

    # ---------- Redis ----------
    redis_url: str = "redis://localhost:6379/0"

    # ---------- JWT ----------
    jwt_secret: str = "change_me_generate_a_random_secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # ---------- Server & CORS ----------
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    log_level: str = "INFO"
    cors_origins: list[str] = []

    # ---------- Public Demo Mode & Abuse Protections ----------
    demo_mode: bool = False
    demo_project_id: str | None = None
    rate_limit_enabled: bool = True
    rate_limit_demo_per_minute: int = 60
    rate_limit_auth_per_minute: int = 300
    max_request_body_bytes: int = 10 * 1024 * 1024  # 10 MB

    # ---------- Reverse Proxy & Trusted Forwarding ----------
    trusted_proxies: list[str] = ["127.0.0.1", "::1", "testclient"]
    proxy_headers_enabled: bool = False

    # ---------- App ----------
    app_name: str = "TraceHarbor"
    app_version: str = "0.1.0"
    debug: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> list[str]:
        """Parse comma-separated string or list of origins into list[str]."""
        if isinstance(v, str):
            v_clean = v.strip()
            if not v_clean:
                return []
            if v_clean.startswith("[") and v_clean.endswith("]"):
                import json
                try:
                    parsed = json.loads(v_clean)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass
            return [origin.strip() for origin in v_clean.split(",") if origin.strip()]
        if isinstance(v, (list, tuple)):
            return [str(origin).strip() for origin in v if str(origin).strip()]
        return []

    @field_validator("trusted_proxies", mode="before")
    @classmethod
    def parse_trusted_proxies(cls, v: object) -> list[str]:
        """Parse comma-separated string or list of trusted proxies."""
        if isinstance(v, str):
            v_clean = v.strip()
            if not v_clean:
                return []
            if v_clean.startswith("[") and v_clean.endswith("]"):
                import json
                try:
                    parsed = json.loads(v_clean)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass
            return [ip.strip() for ip in v_clean.split(",") if ip.strip()]
        if isinstance(v, (list, tuple)):
            return [str(ip).strip() for ip in v if str(ip).strip()]
        return ["127.0.0.1", "::1", "testclient"]

    # ---------- Evaluation & Datasets ----------
    max_dataset_upload_size_bytes: int = 5 * 1024 * 1024  # 5 MB
    max_dataset_cases: int = 500
    max_concurrent_experiments: int = 2

    # ---------- LLM-as-Judge (Optional) ----------
    llm_judge_provider: str = "openai"
    llm_judge_model: str = "gpt-4o-mini"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    # ---------- Phase 6: Failure Intelligence & Embedding ----------
    embedding_provider: str = ""  # 'fake', 'openai', or empty (disabled)
    embedding_dimensions: int = 64
    embedding_batch_size: int = 50
    clustering_similarity_threshold: float = 0.85
    clustering_min_cluster_size: int = 2
    clustering_max_candidates: int = 1000


settings = Settings()
