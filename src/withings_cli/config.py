"""Configuration and token storage for withings-cli."""

from __future__ import annotations

import fcntl
import json
import time
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

CONFIG_DIR = Path.home() / ".config" / "withings-cli"
TOKENS_FILE = CONFIG_DIR / "tokens.json"
TOKENS_LOCK_FILE = CONFIG_DIR / "tokens.lock"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def save_json(path: Path, data: dict[str, Any]) -> None:
    ensure_config_dir()
    path.write_text(json.dumps(data, indent=2) + "\n")


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    result: dict[str, Any] = json.loads(path.read_text())
    return result


def save_tokens(tokens: dict[str, Any]) -> None:
    stamped = dict(tokens)
    expires_in = stamped.get("expires_in")
    if isinstance(expires_in, int):
        # Withings refresh tokens are single-use; stamp an absolute expiry
        # so concurrent callers can skip redundant refreshes.
        stamped["expires_at"] = int(time.time()) + expires_in
    save_json(TOKENS_FILE, stamped)


@contextmanager
def tokens_lock() -> Iterator[None]:
    """Serialize read → refresh → write across concurrent processes."""
    ensure_config_dir()
    with TOKENS_LOCK_FILE.open("w") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def load_tokens() -> dict[str, Any] | None:
    return load_json(TOKENS_FILE)


def delete_tokens() -> None:
    if TOKENS_FILE.exists():
        TOKENS_FILE.unlink()


def save_credentials(client_id: str, client_secret: str) -> None:
    save_json(CREDENTIALS_FILE, {"client_id": client_id, "client_secret": client_secret})


def load_credentials() -> dict[str, Any] | None:
    return load_json(CREDENTIALS_FILE)
