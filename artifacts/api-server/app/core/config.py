import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "")
    secret_key: str = os.getenv("SECRET_KEY", "mindpattern-secret-key-change-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
