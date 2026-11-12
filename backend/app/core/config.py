from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator


class Settings(BaseSettings):
    PROJECT_NAME: str = "GovJob Matcher API"
    GROQ_API_KEY: str
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/govjobs_db"
    TELEGRAM_BOT_TOKEN: str = ""
    # Only used to render the "message @bot" instruction; no secret here.
    TELEGRAM_BOT_USERNAME: str = ""
    # Telegram echoes this value in X-Telegram-Bot-Api-Secret-Token.
    TELEGRAM_WEBHOOK_SECRET: str = ""
    TELEGRAM_LINK_CODE_TTL_MINUTES: int = 10
    ENVIRONMENT: str = "development"

    # --- Auth / session config (all env-driven, no hardcoded secrets) ---
    COOKIE_NAME: str = "session_id"
    # Development/test can keep HTTP cookies; production MUST send HTTPS-only
    # session cookies. Unset (None) means "derive from ENVIRONMENT".
    COOKIE_SECURE: bool | None = None
    # "lax" (default, same-site deployments) or "none" (cross-origin frontend).
    COOKIE_SAMESITE: str = "lax"
    SESSION_TTL_DAYS: int = 7
    # Comma-separated list of exact frontend origins. Never "*" with credentials.
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:8080"
    # "memory://" works single-process; point at redis://<host> in multi-worker prod.
    RATE_LIMIT_STORAGE_URL: str = "memory://"

    @model_validator(mode="after")
    def derive_cookie_security(self) -> "Settings":
        samesite = self.COOKIE_SAMESITE.strip().lower()
        if samesite not in ("lax", "none", "strict"):
            raise ValueError("COOKIE_SAMESITE must be one of 'lax', 'none' or 'strict'")
        self.COOKIE_SAMESITE = samesite

        if self.COOKIE_SECURE is None:
            self.COOKIE_SECURE = self.ENVIRONMENT == "production"
        elif self.ENVIRONMENT == "production" and not self.COOKIE_SECURE:
            raise ValueError("COOKIE_SECURE must be true in production (HTTPS)")

        if self.ENVIRONMENT == "production":
            if self.RATE_LIMIT_STORAGE_URL.startswith("memory://"):
                raise ValueError(
                    "RATE_LIMIT_STORAGE_URL must be shared storage (e.g. redis://...) in production"
                )
            if samesite == "none" and not self.COOKIE_SECURE:
                raise ValueError("COOKIE_SAMESITE=none requires COOKIE_SECURE=true")
        return self

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def force_asyncpg_driver(cls, v: str) -> str:
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql+psycopg://"):
            return v.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
        return v

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
