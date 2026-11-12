from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "GovJob Matcher API"
    GROQ_API_KEY: str
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/govjobs_db"
    TELEGRAM_BOT_TOKEN: str = ""

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def force_asyncpg_driver(cls, v: str) -> str:
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql+psycopg://"):
            return v.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
        return v

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()