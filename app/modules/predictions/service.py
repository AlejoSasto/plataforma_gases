"""Inferencia sobre lecturas de gas (sklearn / xgboost / PyTorch)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import mlflow
import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.alerts.recommendations import probability_to_risk_level
from app.modules.ml_training import repository as ml_repo
from app.modules.predictions.models import Prediction
from app.modules.sensors_ingestion.models import GasReading, Sensor
from app.shared.exceptions import NotFoundError, ValidationError
from ml_core.features.build_features import (
    FEATURE_COLUMNS,
    ROLLING_WINDOW,
    _add_sensor_features,
)


def _torch():
    import torch

    return torch


def _build_sequence_model(*args, **kwargs):
    from ml_core.models.architectures import build_sequence_model

    return build_sequence_model(*args, **kwargs)


def _artifact_dir(uri: str) -> Path:
    """Resuelve artifact_uri a Path usable (host Windows o contenedor Linux)."""
    raw = uri
    if uri.startswith("file:"):
        # Normalizar file:C:/... y file:///C:/... y file:///app/...
        stripped = uri[5:]  # quita "file:"
        if stripped.startswith("///"):
            stripped = stripped[2:]  # ///C:/ → /C:/  ó ///app → /app
        elif stripped.startswith("//"):
            stripped = stripped[1:]
        # file:/C:/Users → /C:/Users
        if len(stripped) >= 3 and stripped[0] == "/" and stripped[2] == ":":
            stripped = stripped[1:]
        raw = stripped

    candidate = Path(raw)
    if candidate.exists():
        return candidate

    # Remapear .../mlruns/<rest> → /app/mlruns (volumen Docker)
    norm = str(raw).replace("\\", "/")
    marker = "/mlruns/"
    idx = norm.lower().find(marker)
    if idx >= 0:
        rest = norm[idx + len(marker) :]
        mapped = Path("/app/mlruns") / rest
        if mapped.exists() or not candidate.exists():
            return mapped
    return candidate


def _load_torch_model(registry) -> Any:
    params = registry.params or {}
    algo = registry.algorithm
    task = params.get("task") or "both"
    n_features = int(params.get("n_features") or len(FEATURE_COLUMNS))
    lookback = int(params.get("lookback_steps") or settings.ml_lookback_steps)
    model = _build_sequence_model(algo, n_features=n_features, task=task)
    root = _artifact_dir(registry.artifact_uri)
    pt = root / "model.pt"
    if not pt.exists():
        candidates = list(root.glob("**/model.pt"))
        if not candidates:
            raise ValidationError(f"No se encontró model.pt en {registry.artifact_uri}")
        pt = candidates[0]
    torch = _torch()
    blob = torch.load(pt, map_location="cpu", weights_only=False)
    state = blob["state_dict"] if isinstance(blob, dict) and "state_dict" in blob else blob
    model.load_state_dict(state)
    model.eval()
    model._pg_lookback = lookback  # type: ignore[attr-defined]
    model._pg_horizon = float(params.get("horizon_minutes") or 7.5)  # type: ignore[attr-defined]
    model._pg_task = str(task)  # type: ignore[attr-defined]
    if isinstance(blob, dict):
        model._pg_norm_mean = blob.get("norm_mean")  # type: ignore[attr-defined]
        model._pg_norm_std = blob.get("norm_std")  # type: ignore[attr-defined]
        model._pg_reg_mean = blob.get("reg_mean")  # type: ignore[attr-defined]
        model._pg_reg_std = blob.get("reg_std")  # type: ignore[attr-defined]
        model._pg_cls_threshold = float(blob.get("cls_threshold") or 0.5)  # type: ignore[attr-defined]
        if blob.get("lookback_steps"):
            model._pg_lookback = int(blob["lookback_steps"])  # type: ignore[attr-defined]
    return model


def _load_production_model(db: Session, scope: str = "global"):
    registry = ml_repo.get_production_model(db, scope=scope, task=None)
    if registry is None or not registry.artifact_uri:
        raise NotFoundError("No hay modelo production disponible")
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    uri = registry.artifact_uri
    framework = ((registry.params or {}).get("framework") or "").lower()
    algo = (registry.algorithm or "").lower()
    family = ((registry.params or {}).get("family") or "").lower()

    if framework == "torch" or family == "sequence" or algo in (
        "lstm",
        "gru",
        "transformer",
        "cnn1d",
    ):
        return registry, _load_torch_model(registry)

    try:
        if "xgboost" in algo or framework == "xgboost":
            model = mlflow.xgboost.load_model(uri)
        else:
            model = mlflow.sklearn.load_model(uri)
    except Exception:  # noqa: BLE001
        model = mlflow.pyfunc.load_model(uri)
    return registry, model


def has_sequence_production(db: Session, scope: str = "global") -> bool:
    registry = ml_repo.get_production_model(db, scope=scope, task=None)
    if registry is None:
        return False
    family = ((registry.params or {}).get("family") or "").lower()
    algo = (registry.algorithm or "").lower()
    framework = ((registry.params or {}).get("framework") or "").lower()
    return (
        family == "sequence"
        or framework == "torch"
        or algo in ("lstm", "gru", "transformer", "cnn1d")
    )


def _load_sensor_window(db: Session, reading: GasReading, *, limit: int) -> pd.DataFrame:
    sql = text(
        """
        SELECT
            gr.id,
            gr.sensor_id,
            gr.leyendo AS "Leyendo",
            gr.temperatura AS "Temperatura",
            gr.tiempo_inicio AS "Tiempo de Inicio"
        FROM gas_readings gr
        WHERE gr.sensor_id = :sensor_id
          AND gr.tiempo_inicio <= :t0
        ORDER BY gr.tiempo_inicio DESC
        LIMIT :lim
        """
    )
    df = pd.read_sql(
        sql,
        db.get_bind(),
        params={
            "sensor_id": reading.sensor_id,
            "t0": reading.tiempo_inicio,
            "lim": limit,
        },
    )
    if df.empty:
        return df
    df["Tiempo de Inicio"] = pd.to_datetime(df["Tiempo de Inicio"], utc=True)
    return df.sort_values("Tiempo de Inicio")


def build_feature_vector(db: Session, reading: GasReading) -> np.ndarray:
    window = _load_sensor_window(db, reading, limit=ROLLING_WINDOW + 5)
    if window.empty:
        row = {
            "Leyendo": float(reading.leyendo),
            "Media_Movil": float(reading.leyendo),
            "Cambio": 0.0,
            "Cambio_Brusco": 0,
            "Temperatura": float(reading.temperatura or 0.0),
        }
        return np.array([[row[c] for c in FEATURE_COLUMNS]], dtype=float)

    featured = _add_sensor_features(window)
    featured["Temperatura"] = pd.to_numeric(featured["Temperatura"], errors="coerce").fillna(0.0)
    featured["Leyendo"] = pd.to_numeric(featured["Leyendo"], errors="coerce")
    target = featured[featured["id"] == reading.id]
    if target.empty:
        target = featured.tail(1)
    vals = target[FEATURE_COLUMNS].iloc[0].to_numpy(dtype=float)
    return np.nan_to_num(vals.reshape(1, -1), nan=0.0)


def build_sequence_tensor(db: Session, reading: GasReading, *, lookback: int) -> np.ndarray:
    window = _load_sensor_window(db, reading, limit=lookback + 5)
    if window.empty:
        base = np.zeros((1, lookback, len(FEATURE_COLUMNS)), dtype=np.float32)
        base[0, -1, 0] = float(reading.leyendo)
        base[0, -1, 4] = float(reading.temperatura or 0.0)
        return base
    featured = _add_sensor_features(window)
    featured["Temperatura"] = pd.to_numeric(featured["Temperatura"], errors="coerce").fillna(0.0)
    featured["Leyendo"] = pd.to_numeric(featured["Leyendo"], errors="coerce").fillna(0.0)
    feats = featured[FEATURE_COLUMNS].to_numpy(dtype=float)
    if len(feats) < lookback:
        pad = np.zeros((lookback - len(feats), len(FEATURE_COLUMNS)))
        feats = np.vstack([pad, feats])
    else:
        feats = feats[-lookback:]
    return np.nan_to_num(feats.reshape(1, lookback, -1), nan=0.0).astype(np.float32)


def _predict_torch(model: Any, x: np.ndarray) -> tuple[float, Optional[float]]:
    """Devuelve (probability, predicted_concentration)."""
    torch = _torch()
    if not isinstance(x, np.ndarray) or x.ndim != 3:
        raise ValidationError("Modelo torch requiere tensor 3D")
    mean = getattr(model, "_pg_norm_mean", None)
    std = getattr(model, "_pg_norm_std", None)
    xn = x.astype(np.float32)
    if mean is not None and std is not None:
        xn = (xn - mean) / np.where(np.asarray(std) < 1e-6, 1.0, std)
    thr = float(getattr(model, "_pg_cls_threshold", 0.5) or 0.5)
    concentration: Optional[float] = None
    probability = 0.0
    with torch.no_grad():
        out = model(torch.tensor(xn, dtype=torch.float32))
        if "logits" in out:
            probability = float(torch.sigmoid(out["logits"])[0].item())
            probability = max(0.0, min(1.0, probability))
        if "reg" in out:
            yhat_n = float(out["reg"][0].item())
            reg_mean = getattr(model, "_pg_reg_mean", None)
            reg_std = getattr(model, "_pg_reg_std", None)
            if reg_mean is not None and reg_std is not None:
                concentration = float(yhat_n * float(reg_std) + float(reg_mean))
            else:
                concentration = yhat_n
        if "logits" not in out and concentration is not None:
            # Solo regresión: mapear magnitud a probabilidad suave
            probability = max(0.0, min(1.0, abs(concentration) / (abs(concentration) + 1.0)))
    # Ajuste umbral entrenado → etiqueta se decide fuera; devolvemos proba cruda
    _ = thr
    return probability, concentration


def _predict_proba(model: Any, x: Any) -> float:
    torch = _torch()
    if isinstance(model, torch.nn.Module):
        prob, _ = _predict_torch(model, x)
        return prob

    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(x)
        if proba.shape[1] >= 2:
            return float(proba[0][1])
        return float(proba[0][0])
    if hasattr(model, "predict"):
        out = model.predict(x)
        arr = np.asarray(out).reshape(-1)
        val = float(arr[0])
        if 0.0 <= val <= 1.0:
            return val
        return float(val >= 0.5)
    raise ValidationError("El modelo activo no soporta predict/predict_proba")


def predict_for_reading(
    db: Session,
    reading: GasReading,
    *,
    scope: str = "global",
    model_bundle: tuple[Any, Any] | None = None,
) -> Prediction:
    existing = (
        db.query(Prediction).filter(Prediction.gas_reading_id == reading.id).first()
    )
    if existing is not None:
        return existing

    if model_bundle is None:
        registry, model = _load_production_model(db, scope=scope)
    else:
        registry, model = model_bundle

    params = registry.params or {}
    horizon = float(params.get("horizon_minutes") or 7.5)
    predicted_concentration: Optional[float] = None

    torch = _torch()
    if isinstance(model, torch.nn.Module):
        lookback = int(getattr(model, "_pg_lookback", settings.ml_lookback_steps))
        x = build_sequence_tensor(db, reading, lookback=lookback)
        probability, predicted_concentration = _predict_torch(model, x)
        thr = float(getattr(model, "_pg_cls_threshold", 0.5) or 0.5)
        predicted_label = 1 if probability >= thr else 0
        horizon = float(getattr(model, "_pg_horizon", horizon) or horizon)
    else:
        x = build_feature_vector(db, reading)
        x_df = pd.DataFrame(x, columns=FEATURE_COLUMNS)
        try:
            probability = _predict_proba(model, x_df)
        except Exception:  # noqa: BLE001
            probability = _predict_proba(model, x)
        predicted_label = 1 if probability >= 0.5 else 0

    probability = max(0.0, min(1.0, float(probability)))
    risk_level = probability_to_risk_level(probability)

    pred = Prediction(
        gas_reading_id=reading.id,
        model_registry_id=registry.id,
        probability=probability,
        predicted_label=predicted_label,
        risk_level=risk_level,
        predicted_concentration=predicted_concentration,
        horizon_minutes=horizon if predicted_concentration is not None else None,
    )
    db.add(pred)
    db.flush()
    return pred


def run_predictions_for_etl_run(
    db: Session,
    etl_run_id: int,
    *,
    limit: int | None = None,
) -> dict[str, int]:
    from app.modules.alerts.service import evaluate_and_create_alert

    registry = ml_repo.get_production_model(db, scope="global", task=None)
    if registry is None or not registry.artifact_uri:
        return {"skipped": 1, "predictions": 0, "alerts": 0}

    try:
        bundle = _load_production_model(db, scope="global")
    except Exception:  # noqa: BLE001
        return {"skipped": 1, "predictions": 0, "alerts": 0}

    q = (
        db.query(GasReading)
        .filter(
            GasReading.etl_run_id == etl_run_id,
            GasReading.is_synthetic.is_(False),
        )
        .order_by(GasReading.id)
    )
    max_n = limit if limit is not None else settings.prediction_post_etl_limit
    if max_n and max_n > 0:
        q = q.limit(max_n)

    readings = q.all()
    n_pred = 0
    n_alert = 0
    for reading in readings:
        try:
            pred = predict_for_reading(db, reading, model_bundle=bundle)
            n_pred += 1
            alert = evaluate_and_create_alert(db, pred, reading)
            if alert is not None:
                n_alert += 1
        except Exception:  # noqa: BLE001
            continue
    db.commit()
    return {"skipped": 0, "predictions": n_pred, "alerts": n_alert}


def list_predictions(
    db: Session,
    *,
    offset: int,
    limit: int,
    sensor_id: int | None = None,
    site_id: int | None = None,
) -> tuple[list[Prediction], int]:
    q = db.query(Prediction).join(
        GasReading, GasReading.id == Prediction.gas_reading_id
    )
    if sensor_id is not None:
        q = q.filter(GasReading.sensor_id == sensor_id)
    if site_id is not None:
        q = q.join(Sensor, Sensor.id == GasReading.sensor_id).filter(
            Sensor.site_id == site_id
        )
    total = q.count()
    items = q.order_by(Prediction.id.desc()).offset(offset).limit(limit).all()
    return items, total


def get_prediction(db: Session, prediction_id: int) -> Optional[Prediction]:
    return db.query(Prediction).filter(Prediction.id == prediction_id).first()


def forecast_concentration_for_reading(
    db: Session,
    reading: GasReading,
    *,
    model_bundle: tuple[Any, Any] | None = None,
) -> Optional[float]:
    """Inferencia on-the-fly de concentración (sin persistir)."""
    if model_bundle is None:
        try:
            registry, model = _load_production_model(db, scope="global")
        except Exception:  # noqa: BLE001
            return None
    else:
        registry, model = model_bundle
    torch = _torch()
    if not isinstance(model, torch.nn.Module):
        return None
    lookback = int(getattr(model, "_pg_lookback", settings.ml_lookback_steps))
    x = build_sequence_tensor(db, reading, lookback=lookback)
    _, conc = _predict_torch(model, x)
    return conc
