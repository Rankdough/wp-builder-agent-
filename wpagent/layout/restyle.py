"""Role-aware restyle of a Divi layout: change colour and radius settings by what they are used for.
Only the attributes of Divi shortcode tags are touched; content inside modules (text, Code module HTML/SVG)
is never changed. A theme is a dict of {role: {old_value: new_value}}; see THEMES."""
from __future__ import annotations

import re

TAG = re.compile(r"\[et_pb_[a-z_]+(?:\s+[a-z0-9_]+=\"[^\"]*\")*\s*\]")
ATTR = re.compile(r'([a-z0-9_]+)="([^"]*)"')


def role_of(attr: str) -> str | None:
    """Map a Divi attribute name to the role its colour plays."""
    if re.search(r"(^|_)(button_)?(text|header(_\d)?|body|title|quote_icon|icon|link)_?(text_)?color", attr) and "background" not in attr:
        return "text"
    if attr.startswith("button_bg_color"):
        return "button_bg"
    if "background_color" in attr and "gradient" not in attr:
        return "background"
    if attr.startswith(("border_color", "button_border_color")) or attr.endswith("_border_color"):
        return "border"
    if attr.startswith("button_border_radius"):
        return "button_radius"
    if "box_shadow_color" in attr:
        return "shadow"
    return None


def restyle_layout(raw: str, theme: dict) -> tuple[str, dict]:
    """Return (new_raw, counts) where counts maps 'role:old->new' to how many settings changed."""
    counts: dict[str, int] = {}

    def fix_tag(m: re.Match) -> str:
        tag = m.group(0)

        def fix_attr(a: re.Match) -> str:
            name, val = a.group(1), a.group(2)
            role = role_of(name)
            table = theme.get(role or "", {})
            new = table.get(val.lower())
            if new is None or new == val:
                return a.group(0)
            key = f"{role}:{val.lower()}->{new}"
            counts[key] = counts.get(key, 0) + 1
            return f'{name}="{new}"'

        return ATTR.sub(fix_attr, tag)

    return TAG.sub(fix_tag, raw), counts


# Option A (picked 2026-10-13): dashboard look in navy, Rank Dough red stays the brand colour.
NAVY_RED = {
    "background": {"#000000": "#0a1120", "#000": "#0a1120", "#0b0d10": "#0a1120", "#14171b": "#0f1c2e"},
    "button_bg": {"#000000": "#0a1120"},
    "border": {"#23272d": "#1e3350", "#26292f": "#1e3350", "#000000": "#0a1120"},  # black borders were invisible on black: keep them invisible
    "text": {"#b8bec6": "#a3b1c6", "#9aa0a6": "#94a3b8", "#d4d8dd": "#cbd5e1"},
    "button_radius": {"3px": "8px", "4px": "8px", "5px": "8px", "6px": "8px"},
    "shadow": {"#000000": "#0a1120"},  # hard black shadows were invisible on black: keep them invisible on navy
}
THEMES = {"navy-red": NAVY_RED}
