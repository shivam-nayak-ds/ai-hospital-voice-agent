from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Asha-AI-Hospital-Agent"
    DEBUG: bool = True
    
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
    DATABASE_URL: str = "sqlite+aiosqlite:///./hospital.db"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    ENABLE_PII_MASKING: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# Singleton instance
settings = Settings()
