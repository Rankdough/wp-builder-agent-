"""New components the page designer may define while copying a design. Each is checked before it can be used:
every selector must start with its own rd- class (so it can't restyle anything else), no square brackets (they break
Divi shortcodes), no imports, no external URLs (only inline data: SVG), no fixed positioning or script-like content.
Accepted components are written to sites/<site>/components/<name>.css and become registered classes."""
from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, Field

from .components import ROOT, registered

NAME = re.compile(r"^rd-[a-z0-9]+(-[a-z0-9]+)*$")


class NewComponent(BaseModel):
    name: str = Field(description="Base class, e.g. rd-score-ring. Modifiers must start with it, e.g. rd-score-ring--red")
    usage: str = Field(description="What to put in the Text module and which classes to add")
    css: str = Field(description="CSS rules; every selector starts with .<name> (or one of its --modifiers)")


class ComponentError(Exception):
    pass


def check_component(c: NewComponent) -> None:
    if not NAME.match(c.name):
        raise ComponentError(f"{c.name!r}: names are rd- plus lowercase words")
    if c.name in registered():
        raise ComponentError(f"{c.name} already exists; use it instead of redefining it")
    css = re.sub(r"/\*.*?\*/", "", c.css, flags=re.S)
    for bad, why in (("[", "square brackets break Divi shortcodes"), ("]", "square brackets break Divi shortcodes"),
                     ("@import", "no imports"), ("position:fixed", "no fixed positioning"),
                     ("expression(", "no script-like CSS"), ("javascript:", "no script-like CSS"), ("</", "no HTML")):
        if bad in css.replace(" ", "").lower():
            raise ComponentError(f"{c.name}: {why}")
    for url in re.findall(r"url\(\s*['\"]?([^'\")]+)", css):
        if not url.startswith("data:image/svg+xml"):
            raise ComponentError(f"{c.name}: only inline data:image/svg+xml URLs are allowed, not {url[:40]}")
    body = re.sub(r"@media[^{]*\{", "", css)
    for selector_list in re.findall(r"([^{}]+)\{", body):
        for sel in selector_list.split(","):
            sel = sel.strip()
            if sel and not re.match(rf"\.{re.escape(c.name)}(--[a-z0-9-]+)?(?![a-z0-9-])", sel):
                raise ComponentError(f"{c.name}: selector {sel!r} must start with .{c.name}")


def save_components(site: str, comps: list[NewComponent]) -> list[Path]:
    folder = ROOT / "sites" / site / "components"
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for c in comps:
        check_component(c)
        p = folder / f"{c.name}.css"
        p.write_text(f"/* {c.name}: {c.usage} */\n{c.css.strip()}\n", encoding="utf-8")
        paths.append(p)
    registered.cache_clear()
    return paths
