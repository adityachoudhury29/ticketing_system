from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str
    
    # Redis
    redis_url: str
    
    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Environment
    environment: str = "development"
    
    # Celery
    celery_broker_url: str
    celery_result_backend: str

    smtp_enabled: bool = False           # set True in production/.env to enable real emails
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_use_tls: bool = True
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str 

    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
