"""Dominio científico: umbrales, unidades, eventos de inicio."""

from ml_core.domain.events import count_onset_episodes, onset_mask
from ml_core.domain.thresholds import (
    THRESHOLD_SEED,
    ThresholdLevel,
    ThresholdSpec,
    levels_for_gas,
    seed_as_records,
)
from ml_core.domain.units import (
    CH4_LEL_PERCENT_VOL,
    CanonicalUnitError,
    to_canonical,
)

__all__ = [
    "THRESHOLD_SEED",
    "ThresholdLevel",
    "ThresholdSpec",
    "CH4_LEL_PERCENT_VOL",
    "CanonicalUnitError",
    "count_onset_episodes",
    "levels_for_gas",
    "onset_mask",
    "seed_as_records",
    "to_canonical",
]
