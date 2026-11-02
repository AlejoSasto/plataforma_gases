"""Walk-forward por bloques con purga y embargo (Plan 15 F5)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Fold:
    name: str
    train_idx: tuple[int, ...]
    calib_idx: tuple[int, ...]
    val_idx: tuple[int, ...]
    is_final_test: bool = False

    def as_dict(self) -> dict:
        return asdict(self)


def _block_ids(index: pd.DatetimeIndex) -> np.ndarray:
    naive = index.tz_convert("UTC").tz_localize(None) if index.tz is not None else index
    periods = naive.to_period("M")
    codes, _ = pd.factorize(periods, sort=True)
    return np.asarray(codes, dtype=int)


def walk_forward_folds(
    timestamps: Sequence,
    *,
    lookback: int,
    k_max: int,
    min_val_steps: int = 500,
    calib_frac: float = 0.2,
    block_freq: str = "ME",
) -> list[Fold]:
    """Pliegues expansivos sobre timestamps ya ordenados.

    Los índices que se devuelven son posiciones 0..n-1 sobre la serie **ordenada**.
    Purga: el train termina al menos `lookback + k_max` pasos antes del inicio de val.
    El último bloque calendario es prueba final intocable.
    """
    del block_freq  # los bloques son meses civiles; se mantiene el arg por compatibilidad
    idx = pd.DatetimeIndex(pd.to_datetime(list(timestamps), utc=True)).sort_values()
    n = len(idx)
    if n < lookback + k_max + 4:
        return []

    blocks = _block_ids(idx)
    unique_blocks = [int(b) for b in np.unique(blocks)]
    gap = int(lookback + k_max)

    def _positions(block_list: list[int]) -> np.ndarray:
        return np.where(np.isin(blocks, block_list))[0]

    if len(unique_blocks) < 2:
        cut_val = int(n * 0.8)
        usable_end = max(2, cut_val - gap)
        cut_cal = max(1, int(usable_end * (1 - calib_frac)))
        return [
            Fold(
                "fold-0",
                tuple(range(0, cut_cal)),
                tuple(range(cut_cal, usable_end)),
                tuple(range(cut_val, n)),
                False,
            ),
            Fold("final-test", tuple(), tuple(), tuple(range(cut_val, n)), True),
        ]

    last = unique_blocks[-1]
    cv_blocks = unique_blocks[:-1]
    merged: list[list[int]] = []
    acc: list[int] = []
    for b in cv_blocks:
        acc.append(b)
        if int(np.isin(blocks, acc).sum()) >= min_val_steps or b == cv_blocks[-1]:
            merged.append(acc)
            acc = []
    if acc:
        if merged:
            merged[-1].extend(acc)
        else:
            merged.append(acc)

    folds: list[Fold] = []
    for i, val_blocks in enumerate(merged):
        val_pos = _positions(val_blocks)
        if len(val_pos) == 0:
            continue
        val_start = int(val_pos.min())
        train_blocks = [b for b in unique_blocks if b < min(val_blocks)]
        train_pos = _positions(train_blocks)
        train_pos = train_pos[train_pos <= (val_start - gap - 1)] if val_start > gap else np.array([], dtype=int)
        if len(train_pos) < 4:
            continue
        cut_cal = int(len(train_pos) * (1 - calib_frac))
        folds.append(
            Fold(
                f"fold-{i}",
                tuple(int(x) for x in train_pos[:cut_cal]),
                tuple(int(x) for x in train_pos[cut_cal:]),
                tuple(int(x) for x in val_pos),
                False,
            )
        )

    folds.append(
        Fold(
            "final-test",
            tuple(),
            tuple(),
            tuple(int(x) for x in _positions([last])),
            True,
        )
    )
    return folds


def assert_no_overlap(fold: Fold, *, lookback: int, k_max: int) -> None:
    if fold.is_final_test:
        return
    train = set(fold.train_idx) | set(fold.calib_idx)
    val = set(fold.val_idx)
    if train & val:
        raise AssertionError(f"solape train/val: {len(train & val)} índices")
    if not train or not val:
        return
    gap = lookback + k_max
    if min(val) - max(train) < gap:
        raise AssertionError(f"brecha {min(val) - max(train)} < lookback+k_max={gap}")
