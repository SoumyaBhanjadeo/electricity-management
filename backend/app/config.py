from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str

    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    CORS_ALLOWED_ORIGINS: str = ""
    RATE_LIMIT_PER_MINUTE: int = 60

    OUTPUT_DIR: str = "outputs"
    LOG_FILE_PATH: str = "outputs/daily_import_audit.log"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]

settings = Settings()