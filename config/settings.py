from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Asha-AI-Hospital-Agent"
    APP_ENV: str = "local"
    DEBUG: bool = True
    CORS_ORIGINS: str = "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000"
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 100
    
    # LLM Settings
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-pro"
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    VECTOR_DB_PATH: str = "data/chroma_db"
    
    # SMS Settings (Mock for now)
    SMS_API_KEY: Optional[str] = "MOCK_KEY"
    SMS_SENDER: str = "ASHA_AI"
    
    # Database
    DATABASE_URL: Optional[str] = None
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "asha"
    DB_PASSWORD: Optional[str] = "asha_dev_password"
    DB_NAME: str = "asha_hospital"
    DB_POOL_SIZE: int = 5
    DB_CONNECTION_TIMEOUT: int = 2

    @model_validator(mode="after")
    def assemble_db_url(self) -> "Settings":
        if not self.DATABASE_URL:
            import urllib.parse
            quoted_password = urllib.parse.quote_plus(self.DB_PASSWORD) if self.DB_PASSWORD else ""
            password_part = f":{quoted_password}" if quoted_password else ""
            self.DATABASE_URL = f"postgresql+psycopg://{self.DB_USER}{password_part}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        return self

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None

    # Vector Database
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "hospital_knowledge"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    ENABLE_PII_MASKING: bool = True

    # Runtime files
    TTS_TEMP_FILE: str = "static/temp_voice.mp3"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# Singleton instance
settings = Settings()
