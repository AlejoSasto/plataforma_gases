"""Reglas del Plan 25: ventana, pliegues, TWA, pruebas funcionales, sin fuga."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml_core.domain.bump import event_overlaps_bump, find_bump_intervals
from ml_core.domain.g1 import choose_lookback_steps, event_eval_mode, merge_monthly_blocks
from ml_core.domain.guards25 import (
    anticipatory_allowed,
    emission_allowed,
    historic_presented_as_open,
    lineage_complete,
    metrics_from_backtest,
    reliability_counts,
    should_email,
)
from ml_core.domain.rolling import causal_rolling_mean
from ml_core.domain.thresholds import THRESHOLD_SEED, levels_for_gas
from ml_core.experiments.real_benchmark import persistence_backtest
from app.modules.forecasting.replay import replay_alerts
from scripts.archive_legacy_models import is_legacy_production

pytestmark = pytest.mark.plan25

ROOT = Path(__file__).resolve().parents[2]


def test_lookback_steps_rule() -> None:
    assert choose_lookback_steps(80) == 60
    assert choose_lookback_steps(130) == 120
    assert choose_lookback_steps(20) == 17
    assert choose_lookback_steps(10) == 12


def test_monthly_blocks_merge_and_reserve_last() -> None:
    blocks = [
        {"month": "2024-09", "n_valid": 200},
        {"month": "2024-10", "n_valid": 200},
        {"month": "2024-11", "n_valid": 200},
        {"month": "2024-12", "n_valid": 40},
    ]
    merged = merge_monthly_blocks(blocks, min_valid=500)
    assert merged[-1]["role"] == "final_test"
    assert merged[-1]["months"] == ["2024-12"]
    assert merged[0]["n_valid"] >= 500
    assert event_eval_mode(10) == "por_episodio"
    assert event_eval_mode(9) == "solo_pronostico"


def test_twa_stel_rolling() -> None:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    times = [start + timedelta(minutes=6 * i) for i in range(4)]
    values = [10.0, 10.0, 10.0, 40.0]
    means = causal_rolling_mean(
        times,
        values,
        window=timedelta(minutes=18),
        step=timedelta(minutes=6),
    )
    assert np.isnan(means[1])
    assert means[2] == pytest.approx(10.0)
    assert means[3] == pytest.approx(20.0)


def test_events_exclude_bump_tests() -> None:
    start = datetime(2024, 6, 1, tzinfo=timezone.utc)
    rows = []
    for i, (o2, co, h2s) in enumerate(
        [(20.9, 1, 0), (20.9, 1, 0), (19.0, 20, 10), (20.8, 1, 0)]
    ):
        ts = start + timedelta(minutes=6 * i)
        for gas, value in (("O2", o2), ("CO", co), ("H2S", h2s)):
            rows.append({"instrument": "4521", "gas": gas, "ts": ts, "value": value})
    bumps = find_bump_intervals(pd.DataFrame(rows))
    assert bumps
    assert event_overlaps_bump("4521", start + timedelta(minutes=12), bumps)
    assert not event_overlaps_bump("4521", start, bumps)


def test_forecast_model_never_saw_target() -> None:
    start = datetime(2024, 3, 1, tzinfo=timezone.utc)
    frame = pd.DataFrame(
        {
            "sensor_code": ["S1"] * 12,
            "ts": [start + timedelta(minutes=6 * i) for i in range(12)],
            "value": [0.2 + 0.01 * i for i in range(12)],
        }
    )
    rows = persistence_backtest(frame, embargo_steps=3)
    assert rows
    embargo = timedelta(minutes=18)
    for row in rows:
        assert emission_allowed(row["train_end"], embargo, row["issued_at"])


def test_final_block_reserved() -> None:
    start = datetime(2024, 3, 1, tzinfo=timezone.utc)
    final = start + timedelta(minutes=30)
    assert not anticipatory_allowed(final, final, final_released=False)
    assert anticipatory_allowed(final, final, final_released=True)
    assert anticipatory_allowed(start, final, final_released=False)


def test_thresholds_have_article() -> None:
    for spec in THRESHOLD_SEED:
        assert spec.kind == "normativo"
        assert spec.article.strip()
    o2 = [t for t in levels_for_gas("O2") if t.direction == "below"][0]
    assert o2.value == 19.5
    assert not any(t.gas_code == "CH4" and t.level == "actuar" for t in THRESHOLD_SEED)


def test_historic_alerts_not_open_and_no_email() -> None:
    assert not should_email("historico")
    assert should_email("en_vivo")
    assert not historic_presented_as_open("historico", "resuelta")
    assert historic_presented_as_open("historico", "abierta")
    start = datetime(2024, 4, 1, tzinfo=timezone.utc)
    frame = pd.DataFrame(
        {
            "sensor_code": ["S1"] * 8,
            "ts": [start + timedelta(minutes=6 * i) for i in range(8)],
            "value": [0.1, 0.1, 2.0, 2.0, 2.0, 0.1, 0.1, 0.1],
        }
    )
    alerts = replay_alerts(persistence_backtest(frame, embargo_steps=1), threshold=1.0)
    assert alerts
    assert all(a["origin"] == "historico" and a["status"] != "abierta" and not a["notify"] for a in alerts)


def test_replay_idempotent() -> None:
    start = datetime(2024, 5, 1, tzinfo=timezone.utc)
    frame = pd.DataFrame(
        {
            "sensor_code": ["S1"] * 10,
            "ts": [start + timedelta(minutes=6 * i) for i in range(10)],
            "value": [0.3] * 10,
        }
    )
    assert len(persistence_backtest(frame)) == len(persistence_backtest(frame))


def test_every_alert_has_lineage() -> None:
    assert lineage_complete({"sensor_id": 1, "source_file": "dls_report.xlsx"})
    assert not lineage_complete({"sensor_id": 1, "source_file": ""})


def test_metrics_from_backtest() -> None:
    rows = [{"y_true": 1.0, "q50": 1.2}, {"y_true": 2.0, "q50": 2.0}]
    assert metrics_from_backtest(rows) == metrics_from_backtest(list(rows))
    assert metrics_from_backtest(rows)["mae"] == pytest.approx(0.1)


def test_reliability_counts_match_outcomes() -> None:
    outcomes = [
        {"outcome": "acertado"},
        {"outcome": "innecesario"},
        {"outcome": "no_avisado"},
    ]
    counts = reliability_counts(outcomes)
    assert counts == {"timely": 1, "missed": 1, "unnecessary": 1, "total": 3}


def test_no_legacy_model_in_production() -> None:
    assert is_legacy_production("random_forest", "production")
    assert not is_legacy_production("persistencia", "production")
    assert not is_legacy_production("random_forest", "archived")


def test_no_silent_fallback() -> None:
    root = ROOT / "ml_core" / "forecasting" / "adapters"
    banned = ("fallback-conformal", "torch-lite", "sklearn-gbr", "holt-native")
    for path in root.glob("*.py"):
        if path.name.startswith("_"):
            continue
        text = path.read_text(encoding="utf-8")
        for token in banned:
            assert token not in text, f"{path.name} contiene {token}"


def test_no_credentials_in_docs() -> None:
    files = list((ROOT / "planes").glob("*.md")) + [ROOT / "README.md"]
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "AdminPass123" not in text, path.name
        assert "SUPERADMIN_PASSWORD=" not in text, path.name


def test_context_doc_no_legacy_terms() -> None:
    text = (ROOT / "planes" / "CONTEXTO_SISTEMA.md").read_text(encoding="utf-8")
    for token in ("torch-lite", "fallback-conformal", "RISK_THRESHOLD_", "train_tabular.py"):
        assert token not in text
    assert "legacy/" in text


@pytest.mark.slow
def test_build_real_platform_idempotent() -> None:
    start = datetime(2024, 7, 1, tzinfo=timezone.utc)
    frame = pd.DataFrame(
        {
            "sensor_code": ["S1"] * 6,
            "ts": [start + timedelta(minutes=6 * i) for i in range(6)],
            "value": [0.4] * 6,
        }
    )
    assert len(persistence_backtest(frame)) == len(persistence_backtest(frame))
