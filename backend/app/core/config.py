from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="JobPilot AI", alias="APP_NAME")
    environment: str = Field(default="local", alias="ENVIRONMENT")
    secret_key: str = Field(default="change-this-secret", alias="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=1440, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(default="redis://localhost:6379/0", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/1", alias="CELERY_RESULT_BACKEND")

    upload_dir: str = Field(default="storage/uploads", alias="UPLOAD_DIR")
    backend_cors_origins: str = Field(default="http://localhost:3000", alias="BACKEND_CORS_ORIGINS")
    app_auto_create_tables: bool = Field(default=True, alias="APP_AUTO_CREATE_TABLES")
    run_tasks_inline: bool = Field(default=False, alias="RUN_TASKS_INLINE")
    seed_demo_data: bool = Field(default=False, alias="SEED_DEMO_DATA")
    playwright_headless: bool = Field(default=True, alias="PLAYWRIGHT_HEADLESS")
    enable_mock_jobs: bool = Field(default=False, alias="ENABLE_MOCK_JOBS")
    enable_arbeitnow_source: bool = Field(default=True, alias="ENABLE_ARBEITNOW_SOURCE")
    job_source_file: str | None = Field(default=None, alias="JOB_SOURCE_FILE")
    application_match_threshold: int = Field(default=55, alias="APPLICATION_MATCH_THRESHOLD")
    auto_apply_enabled: bool = Field(default=True, alias="AUTO_APPLY_ENABLED")
    auto_submit_applications: bool = Field(default=False, alias="AUTO_SUBMIT_APPLICATIONS")

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore", populate_by_name=True)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
