"""Render a validated PageSpec into Divi 4's layout format (the same format Portability exports).
Attribute names follow Divi 4.27.4 as stored by the builder."""
from __future__ import annotations

import json


from .spec import Box, PageSpec

V = "4.27.4"


def _attr(value) -> str:
    # Divi encodes quotes and brackets inside shortcode attributes like this.
    return (str(value).replace('"', "%22").replace("[", "%91").replace("]", "%93")
            .replace("<", "%3C").replace(">", "%3E"))


def _attrs(d: dict) -> str:
    return " ".join(f'{k}="{_attr(v)}"' for k, v in d.items() if v is not None and v != "")


def _px(v):
    return None if v is None else f"{v}px"


def _box(b: Box) -> dict:
    a = {"background_color": b.background_color}
    if b.padding:
        t, r, bt, l = b.padding
        a["custom_padding"] = f"{t}px|{r}px|{bt}px|{l}px|false|false"
    if b.margin_bottom is not None:
        a["custom_margin"] = f"||{b.margin_bottom}px||false|false"
    if b.border_width is not None:
        a["border_width_all"] = f"{b.border_width}px"
    a["border_color_all"] = b.border_color
    a["border_style_all"] = b.border_style
    if b.border_radius is not None:
        r = b.border_radius
        a["border_radii"] = f"on|{r}px|{r}px|{r}px|{r}px"
    return a


def _module(m) -> str:
    base = {"_builder_version": V, "_module_preset": "default"}
    if m.type == "text":
        a = {**base, **_box(m), "text_text_color": m.text_color, "text_font_size": _px(m.font_size),
             "text_line_height": f"{m.line_height_em}em" if m.line_height_em else None,
             "header_text_color": m.heading_color, "header_font_size": _px(m.h1_size),
             "header_2_text_color": m.heading_color, "header_2_font_size": _px(m.h2_size),
             "header_3_text_color": m.heading_color, "header_3_font_size": _px(m.h3_size),
             "text_orientation": m.align, "module_class": m.css_class}
        return f"[et_pb_text {_attrs(a)}]{m.html}[/et_pb_text]"
    if m.type == "button":
        custom = any(v is not None for v in (m.text_color, m.bg_color, m.border_color, m.border_width,
                                             m.border_radius, m.font_size))
        a = {**base, "button_text": m.text, "button_url": m.url, "url_new_window": "on" if m.new_window else "off",
             "button_alignment": m.align, "custom_button": "on" if custom else "off",
             "button_text_color": m.text_color, "button_bg_color": m.bg_color,
             "button_border_color": m.border_color, "button_border_width": _px(m.border_width),
             "button_border_radius": _px(m.border_radius), "button_text_size": _px(m.font_size),
             "button_use_icon": "on" if m.show_arrow else ("off" if custom else None),
             "button_on_hover": "off" if m.show_arrow else None}
        return f"[et_pb_button {_attrs(a)}][/et_pb_button]"
    if m.type == "image":
        a = {**base, **_box(m), "src": m.src, "alt": m.alt, "title_text": m.title or m.alt}
        return f"[et_pb_image {_attrs(a)}][/et_pb_image]"
    if m.type == "blurb":
        a = {**base, **_box(m), "title": m.title, "use_icon": "off", "header_level": "h3",
             "header_text_color": m.title_color, "header_font_size": _px(m.title_size),
             "body_text_color": m.text_color, "body_font_size": _px(m.font_size),
             "module_class": m.css_class}
        return f"[et_pb_blurb {_attrs(a)}]{m.body_html}[/et_pb_blurb]"
    if m.type == "toggle":
        a = {**base, **_box(m), "title": m.title, "title_level": "h3", "open": "on" if m.open else "off",
             "title_text_color": m.title_color, "body_text_color": m.text_color, "icon_color": m.icon_color,
             "open_toggle_background_color": m.background_color, "closed_toggle_background_color": m.background_color}
        return f"[et_pb_toggle {_attrs(a)}]{m.body_html}[/et_pb_toggle]"
    if m.type == "code":
        compact = json.dumps(json.loads(m.jsonld), ensure_ascii=False, separators=(", ", ": "))
        a = {**base, "admin_label": "Schema (JSON-LD)"}
        return f'[et_pb_code {_attrs(a)}]<script type="application/ld+json">{compact}</script>[/et_pb_code]'
    raise ValueError(m.type)


def render(spec: PageSpec) -> str:
    out = []
    for sec in spec.sections:
        sa = {"fb_built": "1", "admin_label": sec.admin_label, "module_id": sec.css_id, "_builder_version": V, "_module_preset": "default",
              "background_color": sec.background_color,
              "custom_padding": f"{sec.padding_top or 0}px||{sec.padding_bottom or 0}px|||"
              if (sec.padding_top is not None or sec.padding_bottom is not None) else None}
        if sec.glow:
            g = sec.glow
            r, gr, b = (int(g.color[i:i + 2], 16) for i in (1, 3, 5))
            sa.update({"use_background_color_gradient": "on", "background_color_gradient_type": "circular",
                       "background_color_gradient_direction_radial": g.position,
                       "background_color_gradient_stops": f"rgba({r},{gr},{b},{g.opacity:g}) 0%|rgba(0,0,0,0) {g.fade_at_percent}%",
                       "background_color_gradient_unit": "%", "background_color_gradient_repeat": "off"})
        out.append(f"[et_pb_section {_attrs(sa)}]")
        for row in sec.rows:
            ra = {"column_structure": row.structure, "_builder_version": V, "_module_preset": "default",
                  "max_width": _px(row.max_width), **_box(row),
                  "use_custom_gutter": "on" if row.gutter else None, "gutter_width": row.gutter,
                  "make_equal": "on" if row.equal_heights else None}
            out.append(f"[et_pb_row {_attrs(ra)}]")
            for col, ctype in zip(row.columns, row.structure.split(",")):
                ca = {"type": ctype, "_builder_version": V, "_module_preset": "default", **_box(col)}
                out.append(f"[et_pb_column {_attrs(ca)}]")
                out.extend(_module(m) for m in col.modules)
                out.append("[/et_pb_column]")
            out.append("[/et_pb_row]")
        out.append("[/et_pb_section]")
    return "".join(out)


def portability_json(layout: str, post_id: int, global_colors: list) -> str:
    return json.dumps({"context": "et_builder", "data": {str(post_id): layout}, "presets": {},
                       "global_colors": global_colors, "images": {}, "thumbnails": []}, ensure_ascii=False)



