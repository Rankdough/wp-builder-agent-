"""Role-aware restyle of a Divi layout: change colour and radius settings by what they are used for.
Only the attributes of Divi shortcode tags are touched; content inside modules (text, Code module HTML/SVG)
is never changed. A theme is a dict of {role: {old_value: new_value}} plus optional rules:
  "card": settings forced onto any card-like element whose background is one of "card_backgrounds"
  "button": settings forced onto every custom-styled Button module."""
from __future__ import annotations

import re

TAG = re.compile(r"\[(et_pb_[a-z_]+)((?:\s+[a-z0-9_]+=\"[^\"]*\")*)\s*\]")
ATTR = re.compile(r'([a-z0-9_]+)="([^"]*)"')
CARD_TAGS = {"et_pb_column", "et_pb_column_inner", "et_pb_row", "et_pb_row_inner", "et_pb_text", "et_pb_blurb",
             "et_pb_testimonial", "et_pb_toggle", "et_pb_accordion", "et_pb_team_member", "et_pb_cta",
             "et_pb_pricing_table", "et_pb_number_counter"}


def role_of(attr: str) -> str | None:
    """Map a Divi attribute name to the role its colour plays."""
    if attr in ("icon_color", "icon_color_hover", "circle_color"):
        return "icon"
    if re.search(r"(^|_)(button_)?(text|header(_\d)?|body|title|quote_icon|link)_?(text_)?color", attr) and "background" not in attr:
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


def _set_attrs(attrs: str, values: dict) -> str:
    """Set (or add) attribute values inside a tag's attribute string."""
    for k, v in values.items():
        pat = re.compile(rf'(\s{k}=")[^"]*(")')
        attrs = pat.sub(rf"\g<1>{v}\g<2>", attrs) if pat.search(attrs) else f'{attrs} {k}="{v}"'
    return attrs


def restyle_layout(raw: str, theme: dict) -> tuple[str, dict]:
    """Return (new_raw, counts) where counts maps 'role:old->new' (or 'card:tag') to how many settings changed."""
    counts: dict[str, int] = {}

    def bump(key: str) -> None:
        counts[key] = counts.get(key, 0) + 1

    def fix_tag(m: re.Match) -> str:
        name, attrs = m.group(1), m.group(2)

        def fix_attr(a: re.Match) -> str:
            attr, val = a.group(1), a.group(2)
            role = role_of(attr)
            new = theme.get(role or "", {}).get(val.lower())
            if new is None or new == val:
                return a.group(0)
            bump(f"{role}:{val.lower()}->{new}")
            return f'{attr}="{new}"'

        attrs = ATTR.sub(fix_attr, attrs)
        values = dict(ATTR.findall(attrs))
        card = theme.get("card")
        if card and name in CARD_TAGS and values.get("background_color", "").lower() in theme.get("card_backgrounds", ()):
            if any(values.get(k) != v for k, v in card.items()):
                attrs = _set_attrs(attrs, card)
                bump(f"card:{name}")
        button = theme.get("button")
        if button and name == "et_pb_button" and values.get("custom_button") == "on":
            if any(values.get(k) != v for k, v in button.items()):
                attrs = _set_attrs(attrs, button)
                bump("button:radius")
        return f"[{name}{attrs}]"

    return TAG.sub(fix_tag, raw), counts


# Option A (picked 2026-10-13): the BestStudentHalls dashboard look (Tailwind navy-950/900, slate-800 borders,
# rounded-2xl cards, rounded-lg buttons), with Rank Dough red kept as the brand and icon colour.
PAGE, CARD, LINE = "#070d19", "#0a2540", "#1e293b"
NAVY_RED = {
    "background": {"#000000": PAGE, "#000": PAGE, "#0b0d10": PAGE, "#0a1120": PAGE,
                   "#14171b": CARD, "#0f1c2e": CARD},
    "button_bg": {"#000000": PAGE, "#0a1120": PAGE},
    "border": {"#23272d": LINE, "#26292f": LINE, "#1e3350": LINE,
               "#000000": PAGE, "#0a1120": PAGE},  # black borders were invisible on black: keep them invisible
    "text": {"#b8bec6": "#94a3b8", "#a3b1c6": "#94a3b8", "#9aa0a6": "#94a3b8", "#d4d8dd": "#cbd5e1"},
    "icon": {"#ffffff": "#f87171", "#fff": "#f87171"},
    "button_radius": {"3px": "8px", "4px": "8px", "5px": "8px", "6px": "8px"},
    "shadow": {"#000000": PAGE, "#0a1120": PAGE},  # hard black shadows were invisible on black: keep them invisible
    "card_backgrounds": (CARD,),
    "card": {"border_width_all": "1px", "border_color_all": LINE, "border_style_all": "solid",
             "border_radii": "on|16px|16px|16px|16px"},
    "button": {"button_border_radius": "8px"},
}
THEMES = {"navy-red": NAVY_RED}


# Navy palette from the Oct 2026 home brief (Rankdough/fetch-and-smile, rankdough-home): navy page, navy cards,
# slate borders and text, blue accent in place of red.
N_PAGE, N_ALT, N_CARD, N_LINE, N_BLUE, N_MUTED, N_BODY = ("#070c18", "#0a2542", "#0f1729", "#1d283a", "#3c83f6",
                                                          "#94a3b8", "#cbd5e1")
NAVY_BLUE = {
    "background": {"#000000": N_PAGE, "#0b0d10": N_ALT, "#14171b": N_CARD},
    "button_bg": {"#e02b20": N_BLUE},
    "border": {"#23272d": N_LINE, "#2c3036": N_LINE, "#000000": N_PAGE, "#f57600": N_BLUE},
    "text": {"#b8bec6": N_MUTED, "#d4d8dd": N_BODY},
    "shadow": {"#000000": N_PAGE},
    "gradient": {"rgba(224,43,32,0.28)": "rgba(60,131,246,0.28)"},
    # Colours inside existing Code module CSS (<style> blocks and style="" attributes): values only.
    "code_css": {"#e02b20": N_BLUE, "#14171b": N_CARD, "#23272d": N_LINE, "#2c3036": N_LINE, "#0b0d10": N_PAGE,
                 "#b8bec6": N_MUTED, "#d4d8dd": N_BODY},
}
THEMES["navy-blue"] = NAVY_BLUE

CODE = re.compile(r"(\[et_pb_code[^\]]*\])(.*?)(\[/et_pb_code\])", re.S)
HEX = re.compile(r"#[0-9a-fA-F]{6}\b")


def swap_code_colours(raw: str, mapping: dict) -> tuple[str, int]:
    """Change colour values inside Code modules' <style> blocks and style="" attributes only. Text is untouched."""
    n = 0

    def css(s: str) -> str:
        nonlocal n

        def one(m: re.Match) -> str:
            nonlocal n
            new = mapping.get(m.group(0).lower())
            if new:
                n += 1
                return new
            return m.group(0)
        return HEX.sub(one, s)

    def module(m: re.Match) -> str:
        body = re.sub(r"(<style[^>]*>)(.*?)(</style>)", lambda s: s.group(1) + css(s.group(2)) + s.group(3), m.group(2),
                      flags=re.S)
        body = re.sub(r'(style=")([^"]*)(")', lambda s: s.group(1) + css(s.group(2)) + s.group(3), body)
        return m.group(1) + body + m.group(3)

    return CODE.sub(module, raw), n


def swap_gradients(raw: str, mapping: dict) -> tuple[str, int]:
    n = 0
    for old, new in mapping.items():
        n += raw.count(old)
        raw = raw.replace(old, new)
    return raw, n


def visible_text(raw: str) -> str:
    """Words a visitor reads: shortcode tags, <style> blocks and HTML tags removed."""
    t = re.sub(r"<style.*?</style>", " ", raw, flags=re.S)
    t = re.sub(r"\[/?et_pb_[^\]]*\]", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    return " ".join(t.split())
