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
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    environment: Literal["local", "prod"] = "local"
    mlflow_tracking_uri: str = "http://localhost:5000"
    gcs_bucket: Optional[str] = None
    db_password: Optional[str] = None
    etl_inbox_enabled: bool = False
    etl_inbox_interval_seconds: int = 60
    etl_inbox_dir: str = "data/inbox"
    # Umbrales de riesgo (probabilidad del modelo) — Plan 05
    risk_threshold_precaution: float = 0.3
    risk_threshold_alert: float = 0.6
    risk_threshold_critical: float = 0.85
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
    # Model Zoo / series (Plan 12)
    ml_lookback_steps: int = 20
    ml_lead_minutes_min: int = 5
    ml_lead_minutes_max: int = 10
    thesis_recall_min: float = 0.95
    thesis_precision_min: float = 0.90
    thesis_f1_min: float = 0.92
    thesis_fn_max: float = 0.05
    thesis_rmse_max: float = 0.05


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
