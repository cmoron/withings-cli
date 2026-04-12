"""Tests for withings_cli.auth."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import httpx
import pytest
import respx

if TYPE_CHECKING:
    from pathlib import Path

from withings_cli import config as config_mod
from withings_cli.auth import (
    AUTHORIZE_URL,
    TOKEN_URL,
    AuthError,
    exchange_code,
    get_authorize_url,
    get_valid_access_token,
    refresh_access_token,
)


@pytest.fixture()
def isolated_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect CONFIG_DIR to a temp path so tests don't touch real tokens."""
    monkeypatch.setattr(config_mod, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config_mod, "TOKENS_FILE", tmp_path / "tokens.json")
    monkeypatch.setattr(config_mod, "TOKENS_LOCK_FILE", tmp_path / "tokens.lock")
    monkeypatch.setattr(config_mod, "CREDENTIALS_FILE", tmp_path / "credentials.json")
    return tmp_path


def test_authorize_url_builds_correct_url() -> None:
    url = get_authorize_url("my-client-id", "https://example.com/cb", state="abc123")
    assert url.startswith(AUTHORIZE_URL)
    assert "client_id=my-client-id" in url
    assert "redirect_uri=https%3A%2F%2Fexample.com%2Fcb" in url
    assert "state=abc123" in url
    assert "scope=user.metrics" in url
    assert "response_type=code" in url


def test_authorize_url_generates_state() -> None:
    url = get_authorize_url("cid", "https://example.com/cb")
    assert "state=" in url


def test_exchange_code_success(token_response: dict[str, Any]) -> None:
    with respx.mock:
        respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json=token_response))
        with patch("withings_cli.auth.save_tokens") as mock_save:
            tokens = exchange_code("cid", "secret", "auth-code", "https://example.com/cb")

    assert tokens["access_token"] == "test-access-token"
    assert tokens["refresh_token"] == "test-refresh-token"
    mock_save.assert_called_once_with(tokens)


def test_exchange_code_api_error() -> None:
    error_resp = {"status": 503, "error": "Invalid code"}
    with respx.mock:
        respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json=error_resp))
        with pytest.raises(AuthError):
            exchange_code("cid", "secret", "bad-code", "https://example.com/cb")


def test_refresh_token_success(token_response: dict[str, Any]) -> None:
    with respx.mock:
        respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json=token_response))
        with patch("withings_cli.auth.save_tokens"):
            tokens = refresh_access_token("cid", "secret", "old-refresh-token")

    assert tokens["access_token"] == "test-access-token"


def test_refresh_token_api_error() -> None:
    error_resp = {"status": 401, "error": "Invalid refresh token"}
    with respx.mock:
        respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json=error_resp))
        with pytest.raises(AuthError):
            refresh_access_token("cid", "secret", "bad-token")


def test_save_tokens_stamps_expires_at(isolated_config: Path) -> None:
    before = int(time.time())
    config_mod.save_tokens({"access_token": "a", "refresh_token": "r", "expires_in": 10800})
    after = int(time.time())

    data = json.loads((isolated_config / "tokens.json").read_text())
    assert before + 10800 <= data["expires_at"] <= after + 10800


def test_get_valid_access_token_skips_refresh_when_fresh(isolated_config: Path) -> None:
    config_mod.save_credentials("cid", "secret")
    config_mod.save_tokens(
        {"access_token": "still-good", "refresh_token": "r", "expires_in": 10800}
    )

    with respx.mock:
        route = respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"status": 0}))
        token = get_valid_access_token()

    assert token == "still-good"
    assert route.call_count == 0


def test_get_valid_access_token_refreshes_when_expired(
    isolated_config: Path, token_response: dict[str, Any]
) -> None:
    config_mod.save_credentials("cid", "secret")
    # Pre-expired tokens: expires_at in the past.
    config_mod.save_json(
        isolated_config / "tokens.json",
        {
            "access_token": "old",
            "refresh_token": "old-r",
            "expires_in": 10800,
            "expires_at": int(time.time()) - 60,
        },
    )

    with respx.mock:
        respx.post(TOKEN_URL).mock(return_value=httpx.Response(200, json=token_response))
        token = get_valid_access_token()

    assert token == "test-access-token"
    # The new tokens should be persisted with a fresh expires_at.
    saved = json.loads((isolated_config / "tokens.json").read_text())
    assert saved["access_token"] == "test-access-token"
    assert saved["expires_at"] > int(time.time())


def test_get_valid_access_token_propagates_refresh_failure(isolated_config: Path) -> None:
    """When the refresh fails, we must raise — never silently serve a stale token."""
    config_mod.save_credentials("cid", "secret")
    config_mod.save_json(
        isolated_config / "tokens.json",
        {
            "access_token": "stale",
            "refresh_token": "dead-r",
            "expires_in": 10800,
            "expires_at": int(time.time()) - 60,
        },
    )

    with respx.mock:
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(200, json={"status": 401, "error": "invalid"})
        )
        with pytest.raises(AuthError):
            get_valid_access_token()
