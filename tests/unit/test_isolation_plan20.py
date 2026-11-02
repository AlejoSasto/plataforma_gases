"""La DB de pruebas no es la de desarrollo y el rollback no deja filas."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.sensors_ingestion.models import Site
from tests.db_urls import load_urls
from tests.factories import site

pytestmark = pytest.mark.plan20


def test_settings_point_to_test_db() -> None:
    _dev, test = load_urls()
    assert "proyecto_gases_test" in settings.database_url
    assert "proyecto_gases_test" in test
    assert settings.database_url.split("?")[0] != _dev.split("?")[0]


def test_rollback_does_not_leak(db: Session) -> None:
    site(db, name="Zona rollback única P20")
    db.commit()
    assert db.query(Site).filter(Site.name == "Zona rollback única P20").first() is not None


def test_previous_site_was_rolled_back(db: Session) -> None:
    found = db.query(Site).filter(Site.name == "Zona rollback única P20").first()
    assert found is None
