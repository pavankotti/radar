from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Job Intelligence Engine"
    API_V1_STR: str = "/api/v1"
    
    # Database
    # Default to local SQLite database for easy development and quick starts
    DATABASE_URL: str = "sqlite:///./jobs.db"
    
    # Celery & Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
