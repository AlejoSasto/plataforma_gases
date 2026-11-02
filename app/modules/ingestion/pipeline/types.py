from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class StageResult:
    name: str
    dataframe: pd.DataFrame
    rows_in: int
    rows_out: int
    rows_rejected: int = 0
    details: dict[str, Any] = field(default_factory=dict)
    issues: list[dict[str, Any]] = field(default_factory=list)
