from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "GovJob Matcher API"
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/govjobs_db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()