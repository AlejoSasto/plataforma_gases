"""Tablas Markdown/LaTeX y figuras mínimas para la tesis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "thesis"


def _md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_Sin filas._\n"
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
    return "\n".join(lines) + "\n"


def _latex_table(df: pd.DataFrame, caption: str) -> str:
    if df.empty:
        return "% vacio\n"
    cols = list(df.columns)
    body = " \\\\\n".join(" & ".join(str(row[c]) for c in cols) for _, row in df.iterrows())
    header = " & ".join(cols)
    return (
        "\\begin{table}[ht]\\centering\\caption{"
        + caption
        + "}\\begin{tabular}{"
        + "l" * len(cols)
        + "}\\hline\n"
        + header
        + " \\\\\\hline\n"
        + body
        + " \\\\\\hline\\end{tabular}\\end{table}\n"
    )


def generate(rows: list[dict], out_dir: Path | None = None) -> Path:
    dest = out_dir or OUT
    dest.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    keep = [c for c in ("model", "family", "fold", "mae", "rmse", "mase", "coverage_10_90", "latency_ms") if c in df.columns]
    slim = df[keep].copy() if keep else df
    for col in slim.select_dtypes(include="number"):
        slim[col] = slim[col].map(lambda x: None if x != x else round(float(x), 4))
    (dest / "metricas.md").write_text("# Métricas de pronóstico\n\n" + _md_table(slim), encoding="utf-8")
    (dest / "metricas.tex").write_text(_latex_table(slim.fillna(""), "Métricas por modelo y pliegue"), encoding="utf-8")
    (dest / "ablaciones.md").write_text(
        "# Ablaciones\n\nDeclaradas en el Plan 17 (ventana, covariables, fundacional, alcance, pérdida).\n"
        "Esta corrida registra el backend realmente usado por cada adaptador.\n\n"
        + _md_table(df[["model", "backend"]].drop_duplicates() if "backend" in df.columns else pd.DataFrame()),
        encoding="utf-8",
    )
    if not df.empty and "mase" in df.columns:
        fig, ax = plt.subplots(figsize=(7, 3.5))
        g = df.groupby("model")["mase"].mean()
        ax.bar(g.index.astype(str), g.values, color="#1f6f4a")
        ax.axhline(1.0, color="#b45309", linestyle="--", label="MASE = 1 (persistencia)")
        ax.set_ylabel("MASE")
        ax.legend()
        fig.tight_layout()
        fig.savefig(dest / "mase_por_modelo.png", dpi=120)
        plt.close(fig)
    (dest / "benchmark.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return dest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(OUT / "benchmark.json"))
    args = parser.parse_args()
    path = Path(args.input)
    if not path.exists():
        from ml_core.experiments.run_benchmark import _default_frame, run_benchmark
        from ml_core.forecasting.problem import ProblemSpec

        spec = ProblemSpec(lookback=12, horizons=(6, 12, 18), grid_step_minutes=6)
        rows = run_benchmark(_default_frame(), spec, models=["persistencia", "ets"])
    else:
        rows = json.loads(path.read_text(encoding="utf-8"))
    dest = generate(rows)
    print(f"OK {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
