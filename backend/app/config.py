from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_async_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://") and "+asyncpg" not in url and "+psycopg2" not in url:
        return "postgresql+asyncpg://" + url.removeprefix("postgresql://")
    return url


def normalize_sync_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url.removeprefix("postgres://")
    if url.startswith("postgresql+asyncpg://"):
        return "postgresql+psycopg2://" + url.removeprefix("postgresql+asyncpg://")
    if url.startswith("postgresql://") and "+asyncpg" not in url and "+psycopg2" not in url:
        return "postgresql+psycopg2://" + url.removeprefix("postgresql://")
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "LeadHunter AI"
    debug: bool = False
    secret_key: str = "change-me"

    database_url: str = "postgresql+asyncpg://leadhunter:leadhunter@localhost:5432/leadhunter"
    database_url_sync: str = "postgresql+psycopg2://leadhunter:leadhunter@localhost:5432/leadhunter"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "llama3.2"
    llm_timeout: float = 120.0

    search_provider: str = "mock"
    serpapi_api_key: str = ""

    http_timeout: float = 30.0
    http_max_retries: int = 3
    http_max_redirects: int = 10
    http_rate_limit_per_domain: float = 1.0
    allowed_url_schemes: str = "http,https"
    block_private_networks: bool = True

    cors_origins: str = "http://localhost:8080,http://127.0.0.1:8080"
    cors_allow_credentials: bool = True

    serve_frontend: bool = False
    frontend_path: str = "/frontend"

    postgres_user: str = "leadhunter"
    postgres_password: str = "leadhunter"
    postgres_db: str = "leadhunter"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    studio_name: str = "IT Studio"
    studio_services: str = "Разработка сайтов и веб-сервисов"

    @model_validator(mode="after")
    def normalize_cloud_settings(self) -> "Settings":
        self.database_url = normalize_async_database_url(self.database_url)
        self.database_url_sync = normalize_sync_database_url(self.database_url_sync)

        if self.database_url and "localhost" not in self.database_url:
            self.database_url_sync = normalize_sync_database_url(self.database_url)

        if self.redis_url and not self.redis_url.endswith("localhost"):
            self.celery_broker_url = self.redis_url
            if self.redis_url.rstrip("/").endswith("/0"):
                self.celery_result_backend = self.redis_url.rsplit("/", 1)[0] + "/1"
            else:
                self.celery_result_backend = self.redis_url

        return self

    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
