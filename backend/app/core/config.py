from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "GovJob Matcher API"
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/govjobs_db"
    TELEGRAM_BOT_TOKEN: str = ""
    ENVIRONMENT: str = "development"

    # --- Auth / session config (all env-driven, no hardcoded secrets) ---
    COOKIE_NAME: str = "session_id"
    # Must be true in production (HTTPS). Kept false for local http dev.
    COOKIE_SECURE: bool = False
    SESSION_TTL_DAYS: int = 7
    # Comma-separated list of exact frontend origins. Never "*" with credentials.
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:8080"
    # "memory://" works single-process; point at redis://<host> in multi-worker prod.
    RATE_LIMIT_STORAGE_URL: str = "memory://"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
