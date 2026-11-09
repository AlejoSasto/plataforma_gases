from functools import lru_cache
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/proyecto_gases"
    )
    jwt_secret: str = "cambiame-en-produccion"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 1
    refresh_token_expire_hours: int = 8
    login_max_attempts: int = 5
    login_lock_minutes: int = 15
    login_rate_limit: int = 20
    login_rate_window_seconds: int = 60
    environment: Literal["local", "prod"] = "local"
    mlflow_tracking_uri: str = "http://localhost:5000"
    gcs_bucket: Optional[str] = None
    db_password: Optional[str] = None
    etl_inbox_enabled: bool = False
    etl_inbox_interval_seconds: int = 60
    etl_inbox_dir: str = "data/inbox"
    # Tras ETL: máximo de lecturas reales a inferir en síncrono (0 = todas)
    prediction_post_etl_limit: int = 500
    prediction_job_enabled: bool = False
    prediction_job_interval_seconds: int = 120
    # Notificaciones (Plan 06)
    notifications_dry_run: bool = True
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None
    whatsapp_api_token: Optional[str] = None
    # Reportes (Plan 08)
    reports_dir: str = "storage/reports"
    # Metas thesis: `app_settings.thesis_targets` (Plan 16/23). Lookback/horizontes: ProblemSpec / G0.
    # Asistente (Plan 26). La clave no se escribe en documentos ni en el navegador.
    assistant_provider: Literal["gemini", "ollama", "off"] = "off"
    gemini_api_key: Optional[str] = None
    assistant_gemini_models: str = "gemini-2.5-flash,gemini-2.5-pro,gemini-2.0-flash"
    assistant_ollama_url: str = "http://127.0.0.1:11434"
    assistant_ollama_model: str = "qwen2.5:7b-instruct"
    assistant_call_timeout_s: int = 30
    assistant_turn_timeout_s: int = 60
    assistant_database_url: Optional[str] = None
    assistant_retention_days: int = 90


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
