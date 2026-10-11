"""Site config loaded from .env. Secrets never leave this module except to the login form."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# A normal desktop Chrome UA. Some hosts' ModSecurity rules return 406 to bot-like agents.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Site:
    name: str
    url: str
    user: str
    password: str = field(repr=False)
    pages: tuple[str, ...]
    is_staging: bool

    @property
    def admin(self) -> str:
        return f"{self.url}/wp-admin/"


def load_site(name: str) -> Site:
    if not name.isidentifier():
        raise ConfigError(f"Invalid site name: {name!r}")
    prefix = f"SITE_{name.upper()}_"

    def get(key: str, required: bool = True) -> str:
        value = os.getenv(prefix + key, "").strip()
        if required and not value:
            raise ConfigError(f"Missing {prefix}{key} in .env (see .env.example)")
        return value

    url = get("URL").rstrip("/")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ConfigError(f"{prefix}URL must be a full https URL, got {url!r}")

    pages = tuple(p.strip() for p in get("PAGES", required=False).split(",") if p.strip()) or ("/",)
    for p in pages:
        if not p.startswith("/"):
            raise ConfigError(f"Page paths must start with '/': {p!r}")

    return Site(
        name=name,
        url=url,
        user=get("USER"),
        password=get("PASSWORD"),
        pages=pages,
        is_staging=get("IS_STAGING", required=False).lower() == "true",
    )


def site_profile(name: str) -> dict:
    """Learned, non-secret facts about a site (sites/<name>.json), fed to the planner and designer."""
    import json
    path = ROOT / "sites" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def global_colors(name: str) -> list:
    """Divi global colours to ship with imported layouts (sites/<name>.json "divi_global_colors"); [] is fine."""
    return site_profile(name).get("divi_global_colors", [])


def script_site() -> Site:
    """For scripts/: take --site <name> from argv (or WPAGENT_SITE) and remove it from argv."""
    import sys
    name = os.getenv("WPAGENT_SITE", "")
    if "--site" in sys.argv:
        i = sys.argv.index("--site")
        name = sys.argv[i + 1]
        del sys.argv[i:i + 2]
    if not name:
        raise ConfigError("Pass --site <name> or set WPAGENT_SITE")
    return load_site(name)
