from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Loads all configuration from environment variables or the .env file.

    Pydantic-settings automatically reads the .env file at startup.
    You never need to call dotenv.load() anywhere else in the project.

    Usage in any file:
        from config import settings
        print(settings.GEMINI_API_KEY)
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

    # Single Agent System.
    GEMINI_API_KEY: str

    # Tools API Keys
    TAVILY_API_KEY: str
    NEWS_API_KEY: str

    # System Settings.
    UPLOAD_DIR: str = "uploads"
    SESSION_TTL_SECONDS: int = 3600

    # System Settings.
    UPLOAD_DIR: str = "uploads"
    SESSION_TTL_SECONDS: int = 3600

    # Authentication and Database.
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_HOURS: int
    DATABASE_URL: str = "sqlite:///./artha.db"


# Instantiate settings as a module-level singleton.
# Every other file imports this 'settings' object — never re-instantiate it.
settings = Settings()
