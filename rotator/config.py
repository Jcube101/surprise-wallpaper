"""Load and validate configuration from config.json."""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# Project root = parent of the rotator package directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.json"
EXAMPLE_CONFIG_PATH = PROJECT_ROOT / "config.json.example"

IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".webp", ".jfif"})


@dataclass
class Config:
    """Runtime configuration for the wallpaper rotator."""

    grok_daily_dir: Path
    curated_dir: Path
    state_file: Path
    log_file: Path
    timezone: str = "Asia/Kolkata"
    prefer_primary: bool = True
    show_toast: bool = True
    toast_title: str = "Grok Surprise Wallpaper"
    image_extensions: frozenset[str] = field(default_factory=lambda: IMAGE_EXTENSIONS)
    nasa_api_key: str = "DEMO_KEY"
    apod_count: int = 1
    apod_save_to: Path | None = None
    pexels_api_key: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], base: Path | None = None) -> Config:
        """Build a Config from a parsed JSON object.

        Relative paths are resolved against *base* (defaults to project root).
        """
        base = base or PROJECT_ROOT

        def resolve(key: str, default: str | None = None) -> Path:
            raw = data.get(key, default)
            if raw is None:
                raise ValueError(f"Missing required config key: {key}")
            p = Path(raw)
            if not p.is_absolute():
                p = (base / p).resolve()
            return p

        exts = data.get("image_extensions")
        if exts:
            image_extensions = frozenset(
                e.lower() if e.startswith(".") else f".{e.lower()}" for e in exts
            )
        else:
            image_extensions = IMAGE_EXTENSIONS

        apod_save = data.get("apod_save_to")
        apod_path = resolve("apod_save_to") if apod_save else None

        return cls(
            grok_daily_dir=resolve("grok_daily_dir", "Grok_Daily"),
            curated_dir=resolve("curated_dir", "Curated"),
            state_file=resolve("state_file", ".last_set.txt"),
            log_file=resolve("log_file", "logs/rotator.log"),
            timezone=str(data.get("timezone", "Asia/Kolkata")),
            prefer_primary=bool(data.get("prefer_primary", True)),
            show_toast=bool(data.get("show_toast", True)),
            toast_title=str(data.get("toast_title", "Grok Surprise Wallpaper")),
            image_extensions=image_extensions,
            nasa_api_key=str(data.get("nasa_api_key", "DEMO_KEY")),
            apod_count=max(1, int(data.get("apod_count", 1))),
            apod_save_to=apod_path,
            pexels_api_key=(
                str(data["pexels_api_key"]).strip()
                if data.get("pexels_api_key")
                else None
            ),
        )


def find_config_path(explicit: str | Path | None = None) -> Path:
    """Locate config.json: explicit path, else project root, else CWD."""
    if explicit:
        return Path(explicit).expanduser().resolve()

    candidates = [
        PROJECT_ROOT / "config.json",
        Path.cwd() / "config.json",
    ]
    for c in candidates:
        if c.is_file():
            return c

    return DEFAULT_CONFIG_PATH


def load_config(path: str | Path | None = None) -> Config:
    """Load config from JSON. Exit with a clear message if missing.

    Also loads optional project-root ``.env`` (does not override existing env).
    ``NASA_API_KEY`` from the environment wins over ``nasa_api_key`` in JSON.
    """
    from rotator.envutil import load_dotenv, resolve_nasa_api_key, resolve_optional_key

    cfg_path = find_config_path(path)

    # Load .env next to config (or project root) before reading secrets
    env_candidates = [cfg_path.parent / ".env", PROJECT_ROOT / ".env"]
    for env_path in env_candidates:
        if load_dotenv(env_path) is not None:
            break

    if not cfg_path.is_file():
        print(
            f"Config not found: {cfg_path}\n"
            f"Copy {EXAMPLE_CONFIG_PATH.name} to config.json and edit paths:\n"
            f"  copy config.json.example config.json",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        with cfg_path.open(encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in {cfg_path}: {e}", file=sys.stderr)
        sys.exit(1)

    base = cfg_path.parent
    try:
        cfg = Config.from_dict(data, base=base)
    except (ValueError, TypeError, KeyError) as e:
        print(f"Bad config in {cfg_path}: {e}", file=sys.stderr)
        sys.exit(1)

    # Env / .env overrides config.json for secrets
    cfg.nasa_api_key = resolve_nasa_api_key(cfg.nasa_api_key)
    cfg.pexels_api_key = resolve_optional_key(
        "PEXELS_API_KEY",
        config_value=cfg.pexels_api_key,
    )

    log.debug("Loaded config from %s", cfg_path)
    return cfg


def ensure_directories(cfg: Config) -> None:
    """Create wallpaper folders and log directory if they do not exist."""
    for d in (cfg.grok_daily_dir, cfg.curated_dir, cfg.log_file.parent, cfg.state_file.parent):
        d.mkdir(parents=True, exist_ok=True)
