from enum import Enum
import urllib.parse
from typing import Optional, List
from pydantic import Field, model_validator, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppEnvironment(str, Enum):
    LOCAL = "local"
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = Field(default="Asha-AI-Hospital-Agent")
    APP_ENV: AppEnvironment = Field(default=AppEnvironment.LOCAL)
    DEBUG: bool = Field(default=True)
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:8000", "http://localhost:3000"])
    
    # LLM Settings
    GROQ_API_KEY: Optional[str] = Field(default=None)
    GROQ_MODEL: str = Field(default="llama-3.1-8b-instant")
    GOOGLE_API_KEY: Optional[str] = Field(default=None)
    GEMINI_MODEL: str = Field(default="gemini-1.5-pro")
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")
    EMBEDDING_MODEL_NAME: str = Field(default="BAAI/bge-base-en-v1.5")
    
    # Database Settings
    DATABASE_URL: Optional[str] = Field(default=None)
    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=5432, ge=1, le=65535)
    DB_USER: str = Field(default="asha")
    DB_PASSWORD: Optional[str] = Field(default=None)
    DB_NAME: str = Field(default="asha_hospital")
    DB_POOL_SIZE: int = Field(default=5, ge=1, le=100)
    DB_CONNECTION_TIMEOUT: int = Field(default=2, ge=1, le=30)
    
    # Cache / Redis Settings
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379, ge=1, le=65535)
    REDIS_PASSWORD: Optional[str] = Field(default=None)
    
    # Qdrant Vector DB Settings
    QDRANT_HOST: str = Field(default="localhost")
    QDRANT_PORT: int = Field(default=6333, ge=1, le=65535)
    QDRANT_URL: Optional[str] = Field(default=None)
    QDRANT_API_KEY: Optional[str] = Field(default=None)
    QDRANT_COLLECTION: str = Field(default="hospital_knowledge")
    
    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO")
    ENABLE_PII_MASKING: bool = Field(default=True)

    # SMTP Settings for Email Notifications
    SMTP_HOST: str = Field(default="smtp.gmail.com")
    SMTP_PORT: int = Field(default=587, ge=1, le=65535)
    SMTP_USER: Optional[str] = Field(default=None)
    SMTP_PASSWORD: Optional[str] = Field(default=None)
    SMTP_FROM: str = Field(default="lifeline-hospital@domain.com")

    # Runtime files
    TTS_TEMP_FILE: str = Field(default="static/temp_voice.mp3")

    # LiveKit: Browser-based voice calls
    LIVEKIT_URL: Optional[str] = Field(default=None)
    LIVEKIT_API_KEY: Optional[str] = Field(default=None)
    LIVEKIT_API_SECRET: Optional[str] = Field(default=None)

    # Authentication
    JWT_SECRET: str = Field(default="asha-dev-secret-change-in-production")

    # Twilio: Telephony + SMS OTP
    TWILIO_ACCOUNT_SID: Optional[str] = Field(default=None)
    TWILIO_AUTH_TOKEN: Optional[str] = Field(default=None)
    TWILIO_PHONE_NUMBER: Optional[str] = Field(default=None)
    TWILIO_WHATSAPP_NUMBER: Optional[str] = Field(default="whatsapp:+14155238886")

    # LangSmith: LLM Observability & Tracing
    LANGSMITH_API_KEY: Optional[str] = Field(default=None)
    LANGSMITH_PROJECT: str = Field(default="asha-hospital-agent")
    LANGSMITH_TRACING: bool = Field(default=False)

    # Hospital Branding (customizable per deployment)
    HOSPITAL_NAME: str = Field(default="Lifeline Multi-Speciality Hospital")
    HOSPITAL_CITY: str = Field(default="Bhopal")
    HOSPITAL_PHONE: str = Field(default="0755-4200-100")
    AGENT_NAME: str = Field(default="Ananya")


    @property
    def cors_origins_list(self) -> List[str]:
        return self.CORS_ORIGINS

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: any) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @model_validator(mode="after")
    def validate_secure_environment(self) -> "Settings":
        """Guarantees key validation in production."""
        if self.APP_ENV == AppEnvironment.PRODUCTION:
            self.DEBUG = False
            if not self.GROQ_API_KEY:
                raise ValueError("GROQ_API_KEY must be configured in production.")
            if not self.DATABASE_URL and not self.DB_PASSWORD:
                raise ValueError("Database credentials must be provided in production.")
            if self.JWT_SECRET == "asha-dev-secret-change-in-production":
                raise ValueError("JWT_SECRET must be changed from default in production.")
        
        # Build SQL URL dynamically if absent
        if not self.DATABASE_URL:
            password = urllib.parse.quote_plus(self.DB_PASSWORD) if self.DB_PASSWORD else ""
            pass_part = f":{password}" if password else ""
            self.DATABASE_URL = f"postgresql+psycopg://{self.DB_USER}{pass_part}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
