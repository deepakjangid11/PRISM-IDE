from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration for PRISM IDE"""
    app_name: str = "PRISM IDE"
    environment: str = "development"
    debug: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
          env_file_encoding="utf-8",
          extra = "ignore"
        )

settings = Settings()
