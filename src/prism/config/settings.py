from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration for PRISM IDE."""

    app_name: str = "PRISM IDE"
    environment: str = "development"
    debug: bool = True
    storage_backend: str = "mysql"  # Options: "mysql", "memory"

    # Security & Authentication Configuration
    secret_key: str = "prism_super_secret_jwt_key_change_in_production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # Developer Session Management Configuration
    session_timeout_minutes: int = 30
    session_heartbeat_interval_seconds: int = 60

    # Database Configuration (MySQL Server)
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "prism_app"
    db_password: str = ""
    db_name: str = "prism_ide"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_recycle: int = 1800
    db_echo: bool = False
    database_url_override: str | None = None

    # Dedicated Test Database Configuration
    test_db_host: str = "localhost"
    test_db_port: int = 3306
    test_db_user: str = "prism_app"
    test_db_password: str = ""
    test_db_name: str = "prism_test_db"
    test_database_url_override: str | None = None

    # LLM Provider Configuration (Phase 20)
    llm_provider: str = "mock"  # Options: "mock", "groq", "openai", "gemini"
    llm_model: str = ""  # If empty, provider default will be used
    llm_temperature: float = 0.2
    llm_max_tokens: int = 2048
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 3
    llm_retry_backoff_factor: float = 1.5

    # Provider API Keys (Never log or hardcode)
    groq_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""

    # RAG Configuration (Phase 20)
    rag_enabled: bool = True
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 100
    rag_top_k: int = 4
    rag_storage_path: str = ".prism/rag_store.json"

    @property
    def database_url(self) -> str:
        """Construct secure MySQL connection string using PyMySQL driver."""
        if self.database_url_override:
            return self.database_url_override
        encoded_password = quote_plus(self.db_password)
        return (
            f"mysql+pymysql://{self.db_user}:{encoded_password}@"
            f"{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )

    @property
    def test_database_url(self) -> str:
        """Construct isolated MySQL connection string for integration testing."""
        if self.test_database_url_override:
            return self.test_database_url_override
        encoded_password = quote_plus(self.test_db_password)
        return (
            f"mysql+pymysql://{self.test_db_user}:{encoded_password}@"
            f"{self.test_db_host}:{self.test_db_port}/{self.test_db_name}?charset=utf8mb4"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
