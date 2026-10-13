"""Component registry: every `rd-*` class defined in a component stylesheet under assets/ (or a site's own
components/ folder) is allowed as a module css_class. To add a component, write its CSS with an `rd-` class;
the spec accepts it automatically, and nothing else can be smuggled in as a class."""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLASS = re.compile(r"\.(rd-[a-z0-9-]+)")


def stylesheets() -> list[Path]:
    files = sorted((ROOT / "assets").glob("*.css"))
    files += sorted((ROOT / "sites").glob("*/components/*.css"))
    return files


@lru_cache(maxsize=1)
def registered() -> frozenset[str]:
    names: set[str] = set()
    for f in stylesheets():
        css = re.sub(r"/\*.*?\*/", "", f.read_text(encoding="utf-8"), flags=re.S)  # ignore comments
        names.update(CLASS.findall(css))
    return frozenset(names)


def check_classes(value: str) -> str:
    tokens = value.split()
    unknown = [t for t in tokens if t not in registered()]
    if not tokens or unknown:
        raise ValueError(f"unknown component class(es): {unknown or value!r}; define them in a component stylesheet first")
    return " ".join(tokens)


def catalogue() -> list[dict]:
    """Each stylesheet's leading comment (its usage notes) plus the classes it defines, for the page designer."""
    out = []
    for f in stylesheets():
        css = f.read_text(encoding="utf-8")
        doc = re.match(r"\s*/\*(.*?)\*/", css, re.S)
        classes = sorted(set(CLASS.findall(re.sub(r"/\*.*?\*/", "", css, flags=re.S))))
        out.append({"file": f.name, "usage": doc.group(1).strip() if doc else "", "classes": classes})
    return out


def bundle(site: str) -> str:
    """All component CSS (shared assets + this site's own components) as one Theme Options block."""
    parts = ["/* wp-builder-agent: reusable components (bundle). Classes: see each part. */"]
    for f in [p for p in stylesheets() if "/components/" not in p.as_posix() or f"/{site}/" in p.as_posix()]:
        css = re.sub(r"/\* end wp-builder-agent[^*]*\*/", "", f.read_text(encoding="utf-8"))
        css = re.sub(r"^/\* wp-builder-agent: reusable components[^*]*\*/", "", css.strip())
        parts.append(f"/* --- {f.name} --- */\n{css.strip()}")
    parts.append("/* end wp-builder-agent components */")
    return "\n".join(parts) + "\n"
