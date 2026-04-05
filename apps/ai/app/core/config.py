from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://yugioh:yugioh_secret@db:5432/yugioh"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Ollama
    ollama_base_url: str = "http://ollama:11434"
    ollama_vision_model: str = "llama3.2-vision:11b"
    ollama_text_model: str = "llama3.2:3b"
    ollama_embed_model: str = "nomic-embed-text"

    # Auth
    jwt_secret: str = "change_this_in_production_please"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080

    # Rate limiting
    rate_limit_ai_rpm: int = 30
    rate_limit_upload_rpm: int = 10

    # Storage
    upload_dir: str = "/storage/uploads"
    thumbnail_dir: str = "/storage/thumbnails"
    export_dir: str = "/storage/exports"
    scraped_dir: str = "/storage/scraped"
    card_images_dir: str = "/storage/card_images"

    # External APIs
    ygoprodeck_api_url: str = "https://db.ygoprodeck.com/api/v7"
    scrape_user_agent: str = "YuGiOhTools/1.0"

    # Celery
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # App
    app_env: str = "development"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
