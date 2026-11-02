import pandas as pd
import pytest
from sqlalchemy.orm import Session

from app.modules.sensors_ingestion.models import GasReading
from ml_core.data.loader import SyntheticDataError, assert_no_synthetic

pytestmark = pytest.mark.plan(15)


def test_no_synthetic_in_training() -> None:
    frame = pd.DataFrame({"leyendo": [1.0], "is_synthetic": [True]})
    with pytest.raises(SyntheticDataError):
        assert_no_synthetic(frame)


def test_db_has_no_synthetic_rows(db: Session) -> None:
    n = db.query(GasReading).filter(GasReading.is_synthetic.is_(True)).count()
    assert n == 0
