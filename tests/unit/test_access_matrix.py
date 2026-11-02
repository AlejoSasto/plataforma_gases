"""Matriz de permisos Plan 19: cada celda es una prueba."""

from __future__ import annotations

import pytest

from app.shared.access import (
    MATRIX,
    PERMISSIONS,
    ROLE_LABELS,
    canonical_role,
    filter_site_ids,
    grants_for,
    role_label,
    scoped_site_ids,
    site_allowed,
    user_has_permission,
)

CELLS = [(role, perm, perm in MATRIX[role]) for role in ROLE_LABELS for perm in PERMISSIONS]


@pytest.mark.plan19
@pytest.mark.parametrize("role,perm,allowed", CELLS)
def test_matrix_cell(role: str, perm: str, allowed: bool) -> None:
    assert (perm in MATRIX[role]) is allowed


@pytest.mark.plan19
def test_six_spanish_role_labels() -> None:
    assert set(ROLE_LABELS) == {
        "admin",
        "supervisor_seguridad",
        "operador",
        "gerencia",
        "analista",
        "auditor",
    }
    assert ROLE_LABELS["operador"] == "Operador de sala"
    assert ROLE_LABELS["analista"] == "Analista de datos"


@pytest.mark.plan19
def test_separation_of_duties() -> None:
    assert "models.train" in MATRIX["analista"]
    assert "thresholds.manage" not in MATRIX["analista"]
    assert "thresholds.manage" in MATRIX["supervisor_seguridad"]
    assert "models.train" not in MATRIX["supervisor_seguridad"]
    assert "models.train" in MATRIX["admin"] and "thresholds.manage" in MATRIX["admin"]


@pytest.mark.plan19
def test_grants_include_canonical() -> None:
    for role in ROLE_LABELS:
        assert MATRIX[role] <= grants_for(role)


class _User:
    def __init__(self, codes: list[str], roles: list[str] | None = None) -> None:
        self.id = 1
        self.permission_codes = codes
        self.role_names = roles or []


@pytest.mark.plan19
def test_permission_aliases_and_labels() -> None:
    assert role_label("operador") == "Operador de sala"
    assert canonical_role("ingeniero_datos") == "analista"
    assert canonical_role("admin") == "admin"
    user = _User(["status.view", "history.view"])
    assert user_has_permission(user, "status.view")
    assert user_has_permission(user, "predictions.view")
    assert user_has_permission(_User(["history.view"]), "status.view")
    assert not user_has_permission(user, "users.manage")
    admin_grants = grants_for("admin")
    assert "predictions.view" in admin_grants
    assert "sensors.manage" in admin_grants


@pytest.mark.plan19
def test_site_filter_without_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.shared import access as access_mod

    class _Db:
        def query(self, *_a, **_k):  # noqa: ANN002
            class _Q:
                def filter(self, *_f, **_kw):  # noqa: ANN002
                    return self

                def all(self):
                    return []

            return _Q()

    user = _User(["status.view"], ["gerencia"])
    db = _Db()
    monkeypatch.setattr(access_mod, "scoped_site_ids", lambda *_a, **_k: None)
    assert site_allowed(db, user, 3) is True
    assert filter_site_ids(db, user, [1, 2]) == [1, 2]
    monkeypatch.setattr(access_mod, "scoped_site_ids", lambda *_a, **_k: {2})
    assert site_allowed(db, user, None) is True
    assert site_allowed(db, user, 2) is True
    assert site_allowed(db, user, 9) is False
    assert filter_site_ids(db, user, [1, 2, 3]) == [2]


class _Row:
    def __init__(self, site_id: int) -> None:
        self.site_id = site_id


class _ScopeDb:
    def query(self, *_a, **_k):  # noqa: ANN002
        class _Q:
            def filter(self, *_f, **_kw):  # noqa: ANN002
                return self

            def all(self):
                return [_Row(4), _Row(5)]

        return _Q()


@pytest.mark.plan19
def test_scoped_site_ids_operator_and_assigned() -> None:
    db = _ScopeDb()
    assert scoped_site_ids(db, _User([], ["operador"])) == {4, 5}
    assert scoped_site_ids(db, _User([], ["gerencia"])) == {4, 5}

    class _Empty:
        def query(self, *_a, **_k):  # noqa: ANN002
            class _Q:
                def filter(self, *_f, **_kw):  # noqa: ANN002
                    return self

                def all(self):
                    return []

            return _Q()

    assert scoped_site_ids(_Empty(), _User([], ["gerencia"])) is None
    assert scoped_site_ids(_Empty(), _User([], ["operador"])) == set()
