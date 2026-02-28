import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    
    # OpenAI
    OPENAI_API_KEY: str
    
    # Jira
    JIRA_DOMAIN: str
    JIRA_USER_EMAIL: str
    JIRA_API_TOKEN: str
    JIRA_PROJECT_KEY: str
    
    # DB
    DATABASE_URL: str = "sqlite:///./incidentes.db"
    
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()
