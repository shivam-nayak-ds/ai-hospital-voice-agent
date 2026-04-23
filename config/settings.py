from pydantic_settings import BaseSettings , SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    
    # App Settings
    APP_NAME: str = "Asha-AI-Hospital-Agent"
    DEBUG: bool = True
    
    # LLM Settings (Groq default)
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.1-70b-versatile"
    
    # SMS Settings (Mock for now)
    SMS_API_KEY: Optional[str] = "MOCK_KEY"
    SMS_SENDER: str = "ASHA_AI"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./hospital.db"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    ENABLE_PII_MASKING: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# Singleton instance
settings = Settings()