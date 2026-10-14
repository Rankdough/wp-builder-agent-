"""Layout spec: native Divi sections, rows, columns and modules with design values only.
Claude fills this in; code validates it; render.py turns it into Divi's own layout format."""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from typing import Annotated, Literal, Optional, Union

from pydantic import AfterValidator, BaseModel, Field

from .components import check_classes

Hex = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]
Px = Annotated[int, Field(ge=0, le=400)]
Width = Annotated[int, Field(ge=320, le=2000)]
COLUMN_STRUCTURES = ("4_4", "1_2,1_2", "1_3,1_3,1_3", "1_4,1_4,1_4,1_4", "2_3,1_3", "1_3,2_3", "3_5,2_5", "2_5,3_5")


class Box(BaseModel):
    """Shared design settings, all optional. Set in each module's Design tab."""
    background_color: Optional[Hex] = None
    padding: Optional[list[Px]] = Field(None, description="[top, right, bottom, left] in px")
    margin_bottom: Optional[Px] = None
    border_width: Optional[Px] = None
    border_color: Optional[Hex] = None
    border_style: Optional[Literal["solid", "dashed", "dotted"]] = None
    border_radius: Optional[Px] = None


CssClass = Annotated[str, AfterValidator(check_classes)]  # any registered rd-* component class(es)


class TextModule(Box):
    type: Literal["text"]
    css_class: Optional[CssClass] = Field(None, description="Space-separated registered component classes, e.g. rd-kpi rd-kpi--green rd-ico-chart")
    html: str = Field(description="Only p, h1-h4, strong, em, a[href], ul, ol, li, br. No attributes except href.")
    text_color: Optional[Hex] = None
    font_size: Optional[Px] = None
    line_height_em: Optional[float] = Field(None, ge=1, le=3)
    heading_color: Optional[Hex] = None
    h1_size: Optional[Px] = None
    h2_size: Optional[Px] = None
    h3_size: Optional[Px] = None
    align: Optional[Literal["left", "center", "right"]] = None


class ButtonModule(BaseModel):
    type: Literal["button"]
    text: str
    url: str
    new_window: bool = False
    align: Optional[Literal["left", "center", "right"]] = None
    text_color: Optional[Hex] = None
    bg_color: Optional[Hex] = None
    border_color: Optional[Hex] = None
    border_width: Optional[Px] = None
    border_radius: Optional[Px] = None
    font_size: Optional[Px] = None
    show_arrow: bool = Field(False, description="Show Divi's arrow icon after the text at all times")


class ImageModule(Box):
    type: Literal["image"]
    src: str
    alt: str
    title: Optional[str] = None


class BlurbModule(Box):
    type: Literal["blurb"]
    css_class: Optional[CssClass] = None
    title: str
    body_html: str = Field(description="Same tag rules as TextModule.html")
    title_color: Optional[Hex] = None
    title_size: Optional[Px] = None
    text_color: Optional[Hex] = None
    font_size: Optional[Px] = None


class ToggleModule(Box):
    type: Literal["toggle"]
    title: str
    body_html: str
    open: bool = False
    title_color: Optional[Hex] = None
    text_color: Optional[Hex] = None
    icon_color: Optional[Hex] = None


class CodeModule(BaseModel):
    type: Literal["code"]
    jsonld: str = Field(description="The JSON-LD object only, without the <script> tag")


Module = Annotated[Union[TextModule, ButtonModule, ImageModule, BlurbModule, ToggleModule, CodeModule],
                   Field(discriminator="type")]


class Column(Box):
    modules: list[Module]


class Row(Box):
    structure: Literal[COLUMN_STRUCTURES]  # type: ignore[valid-type]
    max_width: Optional[Width] = Field(None, description="Row max width in px; null = theme default")
    gutter: Optional[Literal[1, 2, 3, 4]] = Field(None, description="Divi gutter width: 1=0%, 2=3%, 3=5.5%, 4=8%")
    equal_heights: bool = Field(False, description="Equalize column heights (cards in a grid)")
    columns: list[Column]


class Glow(BaseModel):
    """Divi native background gradient (Background > Gradient > Circular)."""
    color: Hex
    opacity: float = Field(ge=0, le=1)
    position: Literal["center", "top left", "top", "top right", "right", "bottom right", "bottom", "bottom left", "left"]
    fade_at_percent: int = Field(ge=1, le=100)


class Section(BaseModel):
    admin_label: str
    css_id: Optional[Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]{0,40}$")]] = Field(None, description="Anchor id, e.g. setup for #setup links")
    background_color: Optional[Hex] = None
    glow: Optional[Glow] = None
    padding_top: Optional[Px] = None
    padding_bottom: Optional[Px] = None
    rows: list[Row]


class PageSpec(BaseModel):
    sections: list[Section]
    notes: list[str] = Field(default_factory=list, description="Where the rebuild differs visually from the original, and why")


class SpecError(Exception):
    pass


CURLY = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})


def straighten_quotes(spec: PageSpec) -> PageSpec:
    """Turn curly quotes back into straight ones (when the source page used straight quotes)."""
    def walk(v):
        if isinstance(v, str):
            return v.translate(CURLY)
        if isinstance(v, list):
            return [walk(x) for x in v]
        if isinstance(v, dict):
            if v.get("type") == "code":
                return v  # JSON-LD is copied verbatim
            return {k: walk(x) for k, x in v.items()}
        return v
    return PageSpec.model_validate(walk(spec.model_dump()))


ALLOWED_TAGS = {"p", "h1", "h2", "h3", "h4", "strong", "em", "a", "ul", "ol", "li", "br"}


class _Checker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.errors: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED_TAGS:
            self.errors.append(f"tag <{tag}> not allowed")
        for k, v in attrs:
            if not (tag == "a" and k in ("href", "target", "rel")):
                self.errors.append(f"attribute {k}= on <{tag}> not allowed")
            if k == "href" and v and v.strip().lower().startswith("javascript:"):
                self.errors.append("javascript: link not allowed")


def check_html(fragment: str, where: str) -> None:
    if "[" in fragment or "]" in fragment:
        raise SpecError(f"{where}: square brackets would break Divi shortcodes")
    c = _Checker()
    c.feed(fragment)
    if c.errors:
        raise SpecError(f"{where}: " + "; ".join(sorted(set(c.errors))))


def validate_spec(spec: PageSpec, media_base: str | None = None) -> None:
    """media_base: images must start with it (the site's /wp-content/uploads/). None = any https URL."""
    codes = 0
    for si, sec in enumerate(spec.sections):
        for ri, row in enumerate(sec.rows):
            want = len(row.structure.split(","))
            if len(row.columns) != want:
                raise SpecError(f"section {si} row {ri}: structure {row.structure} needs {want} columns, got {len(row.columns)}")
            for ci, col in enumerate(row.columns):
                for mi, m in enumerate(col.modules):
                    where = f"section {si} row {ri} col {ci} module {mi} ({m.type})"
                    if m.type == "text":
                        check_html(m.html, where)
                    elif m.type in ("blurb", "toggle"):
                        check_html(m.body_html, where)
                        for t in (m.title,):
                            if re.search(r"[<>\[\]]", t):
                                raise SpecError(f"{where}: title contains markup")
                    elif m.type == "button":
                        if re.search(r"[<>\[\]\"]", m.text) or not re.match(r"^(https?://|#|/|mailto:[^\s<>\"]+$)", m.url):
                            raise SpecError(f"{where}: bad button text or url")
                    elif m.type == "image":
                        if not m.src.startswith(media_base or "https://"):
                            raise SpecError(f"{where}: image must come from the site's media library")
                    elif m.type == "code":
                        codes += 1
                        try:
                            json.loads(m.jsonld)
                        except ValueError as exc:
                            raise SpecError(f"{where}: jsonld is not valid JSON ({exc})") from exc
                        if "</script" in m.jsonld.lower():
                            raise SpecError(f"{where}: jsonld must not contain a script tag")
    if codes > 1:
        raise SpecError(f"{codes} Code modules; only one (the JSON-LD) is allowed")


def _plain(html_or_text: str) -> str:
    import html as _html
    t = re.sub(r"<[^>]+>", " ", html_or_text or "")
    t = _html.unescape(t).translate(CURLY)
    return re.sub(r"\s+", " ", t).strip()


def missing_text(source_nodes: list[dict], spec: PageSpec, min_len: int = 20) -> list[str]:
    """Source passages (own text of each element, >= min_len chars) that do not appear verbatim in the spec.
    Link text is excluded from source nodes, so a passage is split at links: check each piece."""
    parts = []
    for sec in spec.sections:
        for row in sec.rows:
            for col in row.columns:
                for m in col.modules:
                    for f in ("html", "body_html", "title", "text"):
                        if getattr(m, f, None):
                            parts.append(_plain(getattr(m, f)))
    blob = " ".join(parts)
    missing = []
    for n in source_nodes:
        text = _plain(n.get("text") or "")
        if len(text) < min_len:
            continue
        pieces = [p.strip(" .") for p in re.split(r"\s{2,}| \. |(?<=from) \.", text) if len(p.strip(" .")) >= 8]
        if not all(p in blob for p in pieces):
            missing.append(text)
    return missing
