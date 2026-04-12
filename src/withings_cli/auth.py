"""OAuth2 authentication for Withings API."""

from __future__ import annotations

import secrets
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from withings_cli.config import load_credentials, load_tokens, save_tokens, tokens_lock

AUTHORIZE_URL = "https://account.withings.com/oauth2_user/authorize2"
TOKEN_URL = "https://wbsapi.withings.net/v2/oauth2"
SCOPE = "user.metrics"
# Refresh when the access token has less than this many seconds of life left.
REFRESH_SKEW_SECONDS = 300


def _is_token_fresh(tokens: dict[str, Any]) -> bool:
    expires_at = tokens.get("expires_at")
    if not isinstance(expires_at, int):
        return False
    return expires_at - int(time.time()) > REFRESH_SKEW_SECONDS


class AuthError(Exception):
    pass


def get_authorize_url(client_id: str, redirect_uri: str, state: str | None = None) -> str:
    """Build the Withings OAuth2 authorization URL."""
    if state is None:
        state = secrets.token_urlsafe(16)
    params = {
        "response_type": "code",
        "client_id": client_id,
        "scope": SCOPE,
        "redirect_uri": redirect_uri,
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def exchange_code(
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> dict[str, Any]:
    """Exchange an authorization code for access and refresh tokens."""
    response = httpx.post(
        TOKEN_URL,
        data={
            "action": "requesttoken",
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
    )
    response.raise_for_status()
    data = response.json()
    if data.get("status") != 0:
        raise AuthError(f"Token exchange failed: {data}")
    tokens: dict[str, Any] = data["body"]
    save_tokens(tokens)
    return tokens


def refresh_access_token(
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> dict[str, Any]:
    """Refresh an expired access token."""
    response = httpx.post(
        TOKEN_URL,
        data={
            "action": "requesttoken",
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
    )
    response.raise_for_status()
    data = response.json()
    if data.get("status") != 0:
        raise AuthError(f"Token refresh failed: {data}")
    tokens: dict[str, Any] = data["body"]
    save_tokens(tokens)
    return tokens


def get_valid_access_token() -> str:
    """Return a valid access token, refreshing under a file lock if needed.

    Withings refresh tokens are single-use (rotated on each refresh), so
    concurrent invocations must serialize read → refresh → write. Otherwise a
    second call that read the same refresh_token before the first call
    rewrote it will fail and invalidate the stored state.
    """
    credentials = load_credentials()
    if credentials is None:
        raise AuthError("No credentials found. Run 'withings login' first.")

    with tokens_lock():
        tokens = load_tokens()
        if tokens is None:
            raise AuthError("Not authenticated. Run 'withings login' first.")

        if _is_token_fresh(tokens):
            return str(tokens["access_token"])

        new_tokens = refresh_access_token(
            credentials["client_id"],
            credentials["client_secret"],
            tokens["refresh_token"],
        )
        return str(new_tokens["access_token"])
