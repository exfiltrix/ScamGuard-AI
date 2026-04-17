from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List
import os


class Settings(BaseSettings):
    """Application settings"""

    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True

    # API Keys
    openai_api_key: str = ""
    # Primary key (legacy single-key support)
    google_api_key: str = ""
    # Multiple keys: GOOGLE_API_KEYS=key1,key2,key3
    google_api_keys: str = ""
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

    def get_google_api_keys(self) -> List[str]:
        """Return all configured Google API keys."""
        keys: List[str] = []

        # Multi-key list from GOOGLE_API_KEYS
        if self.google_api_keys:
            for k in self.google_api_keys.split(","):
                k = k.strip()
                if k:
                    keys.append(k)

        # Also support GOOGLE_API_KEY_1, GOOGLE_API_KEY_2, ...
        for i in range(1, 20):
            env_key = os.environ.get(f"GOOGLE_API_KEY_{i}", "").strip()
            if env_key and env_key not in keys:
                keys.append(env_key)

        # Fall back to legacy single key
        if self.google_api_key and self.google_api_key not in keys:
            keys.append(self.google_api_key)

        return [k for k in keys if k]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
