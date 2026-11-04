from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration for PRISM IDE."""

    app_name: str = "PRISM IDE"
    environment: str = "development"
    debug: bool = True

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
