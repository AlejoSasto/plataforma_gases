"""Tests unitarios de seguridad JWT."""

from app.core.security import create_access_token, decode_access_token


def test_create_and_decode_access_token_includes_permissions() -> None:
    token = create_access_token(
        user_id=42,
        roles=["admin"],
        permissions=["users.manage", "roles.manage"],
    )
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["roles"] == ["admin"]
    assert "users.manage" in payload["permissions"]
    assert "roles.manage" in payload["permissions"]


def test_decode_invalid_token_returns_none() -> None:
    assert decode_access_token("not-a-valid-token") is None
