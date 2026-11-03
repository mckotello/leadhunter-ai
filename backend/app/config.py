from pydantic_settings import BaseSettings, SettingsConfigDict


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

    postgres_user: str = "leadhunter"
    postgres_password: str = "leadhunter"
    postgres_db: str = "leadhunter"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    studio_name: str = "IT Studio"
    studio_services: str = "Разработка сайтов и веб-сервисов"

    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
