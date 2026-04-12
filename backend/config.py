from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True
    
    # API Keys
    openai_api_key: str = ""
    google_api_key: str = ""
    telegram_bot_token: str
    
    # AI Provider
    ai_provider: str = "gemini"  # openai, gemini, or fallback
    
    # Database
    database_url: str = "sqlite:///./scamguard.db"
    
    # AI Settings
    ai_model: str = "gpt-4-vision-preview"
    ai_temperature: float = 0.3
    ai_max_tokens: int = 1500
    
    # Rate Limiting
    rate_limit_per_minute: int = 10
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
