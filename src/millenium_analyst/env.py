"""Small, dependency-free loader for ignored local environment files."""

from __future__ import annotations

import os
from pathlib import Path


ALLOWED_KEYS = {
    "ANALYST_PROVIDER",
    "ANALYST_MODEL",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_VERSION",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
}


def load_local_env(root: Path) -> None:
    """Load simple KEY=VALUE entries without executing shell syntax."""

    for filename in (".env.local", ".env"):
        path = root / filename
        if not path.is_file():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key not in ALLOWED_KEYS:
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            if value:
                os.environ.setdefault(key, value)
