"""Tests for withings_cli.auth."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import httpx
import pytest
import respx

from withings_cli.auth import (
    AUTHORIZE_URL,
    TOKEN_URL,
    AuthError,
    exchange_code,
    get_authorize_url,
    refresh_access_token,
)


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
