"""Lightweight .env loader (no python-dotenv dependency).

Loads KEY=VALUE pairs from a .env file into os.environ if the key is not
already set. Missing files are fine — offline / secret-optional design.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)


def load_dotenv(path: Path | None = None, *, override: bool = False) -> Path | None:
    """Load environment variables from *path*.

    Returns the path loaded, or None if no file was found / readable.
    Does not raise on missing file.
    """
    if path is None:
        return None
    path = Path(path)
    if not path.is_file():
        log.debug("No .env at %s (optional)", path)
        return None

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        log.warning("Could not read .env %s: %s", path, e)
        return None

    count = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if not key:
            continue
        if not override and key in os.environ and os.environ[key] != "":
            continue
        os.environ[key] = value
        count += 1

    log.debug("Loaded %d var(s) from %s", count, path)
    return path


def resolve_nasa_api_key(config_key: str | None = None) -> str:
    """Priority: env NASA_API_KEY → config value → DEMO_KEY."""
    env = (os.environ.get("NASA_API_KEY") or "").strip()
    if env:
        return env
    cfg = (config_key or "").strip()
    if cfg:
        return cfg
    return "DEMO_KEY"


def resolve_optional_key(*env_names: str, config_value: str | None = None) -> str | None:
    """First non-empty among env names, then config_value, else None."""
    for name in env_names:
        val = (os.environ.get(name) or "").strip()
        if val:
            return val
    cfg = (config_value or "").strip()
    return cfg or None
