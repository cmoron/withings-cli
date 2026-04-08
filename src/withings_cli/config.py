"""Configuration and token storage for withings-cli."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".config" / "withings-cli"
TOKENS_FILE = CONFIG_DIR / "tokens.json"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def save_json(path: Path, data: dict[str, Any]) -> None:
    ensure_config_dir()
    path.write_text(json.dumps(data, indent=2) + "\n")


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())  # type: ignore[no-any-return]


def save_tokens(tokens: dict[str, Any]) -> None:
    save_json(TOKENS_FILE, tokens)


def load_tokens() -> dict[str, Any] | None:
    return load_json(TOKENS_FILE)


def delete_tokens() -> None:
    if TOKENS_FILE.exists():
        TOKENS_FILE.unlink()


def save_credentials(client_id: str, client_secret: str) -> None:
    save_json(CREDENTIALS_FILE, {"client_id": client_id, "client_secret": client_secret})


def load_credentials() -> dict[str, str] | None:
    return load_json(CREDENTIALS_FILE)  # type: ignore[return-value]
