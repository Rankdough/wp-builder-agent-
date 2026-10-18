"""Rank Dough service page template (Oct 2026), as native Divi shortcodes. The same design as the Website SEO Audits
page: icon cards (Blurb modules, card styling on the column so rows even out), feature sections (graphic one side,
heading, intro and pill card the other, then a grid of icon cards and a centred button), a proof band, and an FAQ
built from Toggle modules with the page's JSON-LD in one data-only Code module. Only design settings, no CSS."""
from __future__ import annotations

import html
import re

V = '_builder_version="4.27.4" _module_preset="default" global_colors_info="{}" theme_builder_area="post_content"'
CARD = ('background_color="#111316" custom_padding="28px|28px|28px|28px|false|false" '
        'border_radii="on|16px|16px|16px|16px" border_width_all="1px" border_color_all="#23272d" border_style_all="solid"')
RED = "#e02b20"


def attr(text: str) -> str:
    """Plain text for a shortcode attribute (Divi stores titles escaped)."""
    return html.escape(html.unescape(text), quote=True).replace("[", "&#91;").replace("]", "&#93;")


def blurb(icon, title, body_html, place="top", card=False, title_size=19, extra=""):
    return (f'[et_pb_blurb title="{attr(title)}" image="{icon}" alt="" use_icon="off" icon_placement="{place}" '
            f'image_icon_width="64px" icon_alignment="left" text_orientation="left" content_max_width="100%" {V} header_level="h3" '
            f'header_text_color="#ffffff" header_font_size="{title_size}px" header_line_height="1.3em" '
            f'body_text_color="#b8bec6" body_font_size="15px" body_line_height="1.7em" {CARD if card else ""} '
            f'{extra}]{body_html}[/et_pb_blurb]')


def text_row(html_body, align="center", size=17, pad="20px||10px|||"):
    return (f'[et_pb_row {V} custom_padding="{pad}"][et_pb_column type="4_4" {V}][et_pb_text {V} '
            f'text_orientation="{align}" header_2_text_color="#ffffff" header_3_text_color="#ffffff" '
            f'text_text_color="#b8bec6" text_font_size="{size}px" text_line_height="1.65em"]{html_body}[/et_pb_text]'
            "[/et_pb_column][/et_pb_row]")


def card_rows(cards, icons):
    """cards: [(icon_name, title, body_html)], three per row; the column carries the card so heights even out."""
    out = ""
    for i in range(0, len(cards), 3):
        cols = "".join(f'[et_pb_column type="1_3" {V} {CARD}]{blurb(icons[ic], t, b)}[/et_pb_column]'
                       for ic, t, b in cards[i:i + 3])
        out += (f'[et_pb_row column_structure="1_3,1_3,1_3" use_custom_gutter="on" gutter_width="2" make_equal="on" '
                f'{V} custom_padding="8px||8px|||"]{cols}[/et_pb_row]')
    return out


def button(text, url, align="center"):
    return (f'[et_pb_button button_url="{url}" button_text="{attr(text)}" button_alignment="{align}" {V} '
            f'custom_button="on" button_text_size="16px" button_text_color="#ffffff" button_bg_color="{RED}" '
            f'button_border_width="0px" button_border_color="{RED}" button_border_radius="8px" button_on_hover="off"]'
            "[/et_pb_button]")


def button_row(text, url):
    return (f'[et_pb_row {V} custom_padding="20px||0px|||"][et_pb_column type="4_4" {V}]{button(text, url)}'
            "[/et_pb_column][/et_pb_row]")


def section(label, rows, bg="#000000", pad=70, css_id=None):
    rows = re.sub(r'\[et_pb_row (?![^\]]*max_width)', f'[et_pb_row max_width="{ROW_W}" ', rows)
    mid = f' module_id="{css_id}"' if css_id else ""
    return (f'[et_pb_section fb_built="1" admin_label="{attr(label)}"{mid} {V} background_color="{bg}" '
            f'custom_padding="{pad}px||{pad}px|||"]{rows}[/et_pb_section]')


def pill_card(title, pills, intro=None, min_height=None):
    """min_height (px, desktop only) stretches the card so the text column ends level with the graphic beside it."""
    p = f"<p>{intro}</p>" if intro else ""
    mh = (f'min_height="{min_height}px" min_height_tablet="0px" min_height_phone="0px" '
          f'min_height_last_edited="on|phone" ' if min_height else "")
    return (f'[et_pb_blurb title="{attr(title)}" module_class="rd-pills rd-pills--lg" {V} {mh}header_level="h3" '
            f'header_text_color="#ffffff" header_font_size="20px" body_text_color="#d4d8dd" body_font_size="17px" '
            f'background_color="#14171b" custom_padding="28px|28px|28px|28px|false|false" '
            f'border_radii="on|16px|16px|16px|16px" border_width_all="1px" border_color_all="#23272d" '
            f'border_style_all="solid"]{p}<ul>{"".join(f"<li>{x}</li>" for x in pills)}</ul>[/et_pb_blurb]')


def feature(label, img, img_alt, image_left, h2, lead_html, cards, icons, cta, pills=None, grid_h2=None,
            min_height=None):
    """Graphic + heading/intro/pill card, then optional centred heading, icon card grid and button."""
    text_col = (f'[et_pb_column type="3_5" {V}][et_pb_text {V} text_text_color="#b8bec6" text_font_size="18px" '
                f'text_line_height="1.65em" header_2_text_color="#ffffff" custom_margin="||24px||false|false"]'
                f"<h2>{h2}</h2>{lead_html}[/et_pb_text]{pill_card(*pills, min_height=min_height) if pills else ''}"
                # no card grid: the button sits under the text, never alone under an empty grid
                f"{'' if cards else button(cta[0], cta[1], align='left')}[/et_pb_column]")
    img_col = (f'[et_pb_column type="2_5" {V}][et_pb_image src="{img}" alt="{attr(img_alt)}" '
               f'title_text="{attr(img_alt)}" {V}][/et_pb_image][/et_pb_column]')
    top = (f'[et_pb_row column_structure="{"2_5,3_5" if image_left else "3_5,2_5"}" module_class="rd-level" make_equal="on" {V} custom_padding="0px||30px|||"]'
           f"{img_col + text_col if image_left else text_col + img_col}[/et_pb_row]")
    grid_head = text_row(f"<h2>{grid_h2}</h2>") if grid_h2 else ""
    return section(label, top + (grid_head + card_rows(cards, icons) + button_row(*cta) if cards else ""))


def cards_section(label, h2, lead_html, cards, icons, note_html=None):
    """Centred heading and intro, a row of icon cards, optional centred note underneath."""
    note = text_row(note_html, size=16, pad="24px||0px|||") if note_html else ""
    return section(label, text_row(f"<h2>{h2}</h2>{lead_html}", pad="0px||20px|||") + card_rows(cards, icons) + note)


def proof(label, kicker, stat, h2, lead_html, bg="#0b0d10", img=None, img_alt="", image_left=False):
    left = (f'[et_pb_text {V} text_text_color="{RED}" text_font_size="13px" text_letter_spacing="0.12em" '
            f'text_font="|600||on|||||" custom_margin="||8px||false|false"]<p>{kicker}</p>[/et_pb_text]'
            f'[et_pb_text {V} text_text_color="{RED}" text_font_size="88px" text_line_height="1em" '
            f'text_font="|800|||||||"]<p>{stat}</p>[/et_pb_text]')
    right = (f'[et_pb_text {V} text_text_color="#b8bec6" text_font_size="17px" text_line_height="1.65em" '
             f'header_2_text_color="#ffffff"]<h2>{h2}</h2>{lead_html}[/et_pb_text]')
    if img:  # result text in one column, the chart in the other
        # same column split as the feature sections, so every graphic on the page is the same size
        txt = f'[et_pb_column type="3_5" {V}]{left}{right}[/et_pb_column]'
        pic = (f'[et_pb_column type="2_5" {V}][et_pb_image src="{img}" alt="{attr(img_alt)}" '
               f'title_text="{attr(img_alt)}" align="center" {V}][/et_pb_image][/et_pb_column]')
        row = (f'[et_pb_row column_structure="{"2_5,3_5" if image_left else "3_5,2_5"}" {V} custom_padding="0px||0px|||"]'
               f'{pic + txt if image_left else txt + pic}[/et_pb_row]')
        return section(label, row, bg=bg)
    row = (f'[et_pb_row column_structure="1_3,2_3" {V}][et_pb_column type="1_3" {V}]{left}[/et_pb_column]'
           f'[et_pb_column type="2_3" {V}]{right}[/et_pb_column][/et_pb_row]')
    return section(label, row, bg=bg)


def faq(label, h2, lead_html, qa, jsonld=None, bg="#0b0d10"):
    """qa: [(question, answer_html)]. First toggle open. JSON-LD (script tag included) in a data-only Code module."""
    toggles = ""
    for i, (q, a) in enumerate(qa):
        toggles += (f'[et_pb_toggle title="{attr(q)}"{" open=\"on\"" if i == 0 else ""} '
                    f'open_toggle_background_color="#14171b" closed_toggle_background_color="#14171b" '
                    f'icon_color="{RED}" {V} title_text_color="#ffffff" title_font_size="19px" title_level="h3" body_text_color="#d4d8dd" '
                    f'background_color="#14171b" custom_margin="||12px||false|false" '
                    f'custom_padding="20px|24px|20px|24px|false|false" border_radii="on|14px|14px|14px|14px" '
                    f'border_width_all="1px" border_color_all="{RED if i == 0 else "#23272d"}" border_style_all="solid"]'
                    f"{a}[/et_pb_toggle]")
    code = (f'[et_pb_code admin_label="Schema (JSON-LD)" {V}]{jsonld}[/et_pb_code]' if jsonld else "")
    row = (f'[et_pb_row {V} max_width="860px"][et_pb_column type="4_4" {V}][et_pb_text {V} text_text_color="#b8bec6" '
           f'text_font_size="17px" header_2_text_color="#ffffff" custom_margin="||26px||false|false"]<h2>{h2}</h2>'
           f"{lead_html}[/et_pb_text]{toggles}{code}[/et_pb_column][/et_pb_row]")
    return section(label, row, bg=bg)


def swap_header_form(raw, img_src, alt, form='[form id="824"]'):
    """Header (first section): the form Code module becomes an image. Re-runs replace the earlier image."""
    end = raw.index("[/et_pb_section]") + len("[/et_pb_section]")
    head = raw[:end]
    img = f'[et_pb_image src="{img_src}" alt="{attr(alt)}" title_text="{attr(alt)}" {V}][/et_pb_image]'
    new, n = re.subn(r"\[et_pb_code[^\]]*\]\s*" + re.escape(form) + r"\s*\[/et_pb_code\]", lambda m: img, head, count=1)
    if not n:
        new, n = re.subn(r'\[et_pb_image src="[^"]*-example[^\]]*\]\[/et_pb_image\]', lambda m: img, head, count=1)
    if not n:
        raise ValueError("Header form (or earlier header graphic) not found in the first section")
    return new + raw[end:]


def sections(raw):
    starts = [m.start() for m in re.finditer(r"\[et_pb_section[\s\]]", raw)]
    return [raw[a:b] for a, b in zip(starts, starts[1:] + [len(raw)])]


def text_segments(raw):
    """Every run of visible text (between tags) outside <style>/<script>, for a no-content-lost check."""
    t = re.sub(r"<style.*?</style>|<script.*?</script>", " ", raw, flags=re.S)
    t = re.sub(r"\[/?et_pb_[^\]]*\]|\[form[^\]]*\]", "|", t)
    return [s for s in (" ".join(html.unescape(x).split()) for x in re.split(r"<[^>]+>|\|", t)) if s]


def visible_words(raw):
    """All visible text of a layout, including Blurb and Toggle titles held in shortcode attributes."""
    titles = " ".join(html.unescape(t) for t in re.findall(r'\[et_pb_(?:blurb|toggle)[^\]]*?\btitle="([^"]*)"', raw))
    t = re.sub(r"<style.*?</style>|<script.*?</script>", " ", raw, flags=re.S)
    t = re.sub(r"\[/?et_pb_[^\]]*\]|\[form[^\]]*\]", " ", t)
    t = re.sub(r"</?span[^>]*>", "", t)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", t) + " " + titles).split())


def outcomes(label, h2, groups, icons, cta):
    """'What changes after…' section: three columns with dividing lines. Each group: (icon, title, intro_html,
    [(icon, title, body_html), (icon, title, body_html)]). Always included on service pages."""
    cols = ""
    for n, (ic, title, intro, items) in enumerate(groups):
        line = 'border_width_right="1px" border_color_right="#23272d" ' if n < len(groups) - 1 else ""
        mods = blurb(icons[ic], title, intro, place="left", title_size=24, extra='custom_margin="||10px||false|false"')
        for jc, t, b in items:
            mods += blurb(icons[jc], t, b, place="left", title_size=18,
                          extra='custom_padding="22px||10px|||" border_width_top="1px" border_color_top="#23272d"')
        cols += f'[et_pb_column type="1_3" {V} {line}custom_padding="0px|24px|0px|0px|false|false"]{mods}[/et_pb_column]'
    grid = (f'[et_pb_row column_structure="1_3,1_3,1_3" use_custom_gutter="on" gutter_width="3" {V} '
            f'custom_padding="20px||10px|||"]{cols}[/et_pb_row]')
    return section(label, text_row(f"<h2>{h2}</h2>") + grid + button_row(*cta))


# --- Timeline section (Oct 2026). Every piece of copy is passed in by the page, so it fits that page's context. ---

def eyebrow_heading(eyebrow, h2, lead_html):
    """Small red uppercase line, a big centred heading and the intro."""
    eb = (f'[et_pb_text {V} text_orientation="center" text_text_color="{RED}" text_font="|700||on|||||" '
          f'text_font_size="12px" text_letter_spacing="0.22em" custom_margin="||10px||false|false"]<p>{eyebrow}</p>'
          "[/et_pb_text]")
    hd = (f'[et_pb_text {V} text_orientation="center" header_2_text_color="#ffffff" header_2_font_size="44px" '
          f'header_2_line_height="1.15em" text_text_color="#b8bec6" text_font_size="17px" text_line_height="1.65em" '
          f'max_width="760px" module_alignment="center"]<h2>{h2}</h2>{lead_html}[/et_pb_text]')
    return f'[et_pb_row {V} custom_padding="0px||24px|||"][et_pb_column type="4_4" {V}]{eb}{hd}[/et_pb_column][/et_pb_row]'


def timeline(phases, icons):
    """phases: [(label, [(icon, title, body_html), (icon, title, body_html)])] x 3. A row of phase labels on a red line
    with dots (rd-phase), then a row of cards, one per phase, each with two icon items split by a line."""
    ends = ["rd-phase--first", "", "rd-phase--last"]
    labels = "".join(f'[et_pb_column type="1_3" {V}][et_pb_text module_class="{("rd-phase " + ends[i]).strip()}" text_orientation="center" {V}]'
                     f"<p>{lbl}</p>[/et_pb_text][/et_pb_column]" for i, (lbl, _) in enumerate(phases))
    cards = ""
    for _, items in phases:
        mods = ""
        for k, (ic, t, b) in enumerate(items):
            extra = ('custom_padding="22px||0px|||" border_width_top="1px" border_color_top="#23272d"' if k
                     else 'custom_padding="0px||22px|||"')
            mods += blurb(icons[ic], t, b, place="left", title_size=18, extra=extra)
        cards += f'[et_pb_column type="1_3" {V} {CARD}]{mods}[/et_pb_column]'
    return (f'[et_pb_row column_structure="1_3,1_3,1_3" use_custom_gutter="on" gutter_width="2" {V} '
            f'custom_padding="10px||14px|||"]{labels}[/et_pb_row]'
            f'[et_pb_row column_structure="1_3,1_3,1_3" use_custom_gutter="on" gutter_width="2" make_equal="on" {V} '
            f'custom_padding="0px||20px|||"]{cards}[/et_pb_row]')


def cta_banner(icon, title, body, cta, icons):
    """Wide card: icon, a bold line and a short sentence on the left, a red button on the right."""
    left = blurb(icons[icon], title, f"<p>{body}</p>", place="left", title_size=26)
    return (f'[et_pb_row column_structure="2_3,1_3" {V} background_color="#111316" '
            f'custom_padding="26px|30px|26px|30px|false|false" border_radii="on|18px|18px|18px|18px" '
            f'border_width_all="1px" border_color_all="#23272d" border_style_all="solid"]'
            f'[et_pb_column type="2_3" {V}]{left}[/et_pb_column]'
            f'[et_pb_column type="1_3" {V}]{button(cta[0], cta[1], align="right")}[/et_pb_column][/et_pb_row]')


def pill_row(label, items):
    """Centred label with lines either side, then centred pills with dots between them."""
    return (f'[et_pb_row {V} custom_padding="34px||0px|||"][et_pb_column type="4_4" {V}]'
            f'[et_pb_text module_class="rd-label-lines" {V} custom_margin="||16px||false|false"]<p>{label}</p>'
            f'[/et_pb_text][et_pb_text module_class="rd-pills rd-pills--center" {V} text_text_color="#d4d8dd"]'
            f'<ul>{"".join(f"<li>{x}</li>" for x in items)}</ul>[/et_pb_text][/et_pb_column][/et_pb_row]')


def timeline_section(label, eyebrow, h2, lead_html, phases, icons, banner, pills=None, css_id=None):
    """banner: (icon, title, body, (button text, url)). pills: (label, [items]) or None."""
    rows = eyebrow_heading(eyebrow, h2, lead_html) + timeline(phases, icons) + cta_banner(*banner[:3], banner[3], icons)
    return section(label, rows + (pill_row(*pills) if pills else ""), css_id=css_id)


def numbered_items(eyebrow, h2, lead_html, cta, items, icons, footer_label=None, footer_items=None):
    """Specialty section: intro on the left (eyebrow, big heading, intro, button); on the right a two-column grid of
    numbered items (rd-risk: big grey number with an icon, short red line, title, text). items: [(icon, title, body)].
    Optional footer line, e.g. 'Platforms we migrate' with names."""
    left = (f'[et_pb_column type="1_3" {V}]'
            f'[et_pb_text {V} text_text_color="{RED}" text_font="|700||on|||||" text_font_size="12px" '
            f'text_letter_spacing="0.22em" custom_margin="||14px||false|false"]<p>{eyebrow}</p>[/et_pb_text]'
            f'[et_pb_text {V} header_2_text_color="#ffffff" header_2_font_size="56px" header_2_line_height="1.05em" '
            f'text_text_color="#b8bec6" text_font_size="18px" text_line_height="1.65em" '
            f'custom_margin="||28px||false|false"]<h2>{h2}</h2>{lead_html}[/et_pb_text]'
            f"{button(cta[0], cta[1], align='left')}[/et_pb_column]")
    rows = ""
    for i in range(0, len(items), 2):
        cols = ""
        for n, (ic, t, b) in enumerate(items[i:i + 2], start=i + 1):
            cols += (f'[et_pb_column_inner type="1_2" saved_specialty_column_type="2_3" {V}]'
                     f'[et_pb_text module_class="rd-risk" {V} text_text_color="#b8bec6" text_font_size="15px" '
                     f'text_line_height="1.65em"]<p>{n:02d} <img src="{icons[ic]}" alt="" width="34" height="34" /></p>'
                     f"<h3>{t}</h3>{b}[/et_pb_text][/et_pb_column_inner]")
        rows += (f'[et_pb_row_inner use_custom_gutter="on" gutter_width="3" {V} custom_padding="0px||28px|||"]'
                 f"{cols}[/et_pb_row_inner]")
    right = (f'[et_pb_column type="2_3" specialty_columns="2" {V} border_width_left="1px" border_color_left="#2a2f36" '
             f'custom_padding="0px||0px|48px|false|false"]{rows}[/et_pb_column]')
    out = (f'[et_pb_section fb_built="1" specialty="on" admin_label="Numbered items" {V} background_color="#000000" '
           f'custom_padding="80px||40px|||"]{left}{right}[/et_pb_section]')
    if footer_label:
        line = (f'<p><strong>{footer_label}</strong>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;{" &middot; ".join(footer_items)}</p>')
        out += section("Numbered items footer",
                       f'[et_pb_row {V} custom_padding="20px||0px|||" border_width_top="1px" border_color_top="#23272d"]'
                       f'[et_pb_column type="4_4" {V}][et_pb_text {V} text_orientation="right" text_text_color="#d4d8dd" '
                       f'text_font_size="13px"]{line}[/et_pb_text][/et_pb_column][/et_pb_row]', pad=20)
    return out


def check_panel(rows, label="Illustrative check"):
    """rows: [(left, middle, badge_text, 'ok'|'warn')]. Small example panel inside an accordion item (rd-check)."""
    tr = "".join(f"<tr><td>{a}</td><td>&rarr;</td><td>{b}</td><td><b class=\"{k}\">{t}</b></td></tr>" for a, b, t, k in rows)
    return f'<div class="rd-check"><p>{label}</p><table>{tr}</table></div>'


def accordion_section(label, eyebrow, h2, lead_html, cta, items, footer_label=None, footer_items=None, css_id=None):
    """Left: eyebrow with a red rule, heading, intro, button, then an optional small list (e.g. platforms).
    Right: numbered accordion (Toggle modules, rd-acc), first item open. items: [(title, body_html)]."""
    foot = ""
    if footer_label:
        foot = (f'[et_pb_text {V} text_text_color="#d4d8dd" text_font_size="16px" text_line_height="1.8em" '
                f'custom_margin="36px||||false|false" custom_padding="26px||||false|false" border_width_top="1px" '
                f'border_color_top="#23272d"]<p><span style="color: #64748b; font-size: 11px; letter-spacing: 0.2em;">'
                f'{footer_label.upper()}</span><br />{" &middot; ".join(footer_items)}</p>[/et_pb_text]')
    left = (f'[et_pb_column type="2_5" {V}]'
            f'[et_pb_text module_class="rd-eyebrow" {V} text_text_color="{RED}" text_font="|700||on|||||" '
            f'text_font_size="12px" text_letter_spacing="0.22em" custom_margin="||16px||false|false"]<p>{eyebrow}</p>'
            f'[/et_pb_text][et_pb_text {V} header_2_text_color="#ffffff" header_2_font_size="40px" '
            f'header_2_line_height="1.1em" text_text_color="#b8bec6" text_font_size="19px" text_line_height="1.6em" '
            f'custom_margin="||28px||false|false"]<h2>{h2}</h2>{lead_html}[/et_pb_text]'
            f"{button(cta[0], cta[1], align='left')}{foot}[/et_pb_column]")
    toggles = ""
    for i, (t, body) in enumerate(items):
        cls = "rd-acc rd-acc--first" if i == 0 else "rd-acc"
        top = f'border_width_top="1px" border_color_top="{RED}" ' if i == 0 else ""
        toggles += (f'[et_pb_toggle title="{attr(t)}"{" open=\"on\"" if i == 0 else ""} module_class="{cls}" {V} '
                    f'open_toggle_background_color="rgba(0,0,0,0)" closed_toggle_background_color="rgba(0,0,0,0)" '
                    f'title_text_color="#ffffff" closed_title_text_color="#ffffff" title_font_size="20px" '
                    f'title_level="h3" body_text_color="#b8bec6" body_font_size="16px" icon_color="#94a3b8" '
                    f'open_icon_color="{RED}" border_radii="on|0px|0px|0px|0px" border_width_all="0px" '
                    f'border_width_bottom="1px" border_color_bottom="#23272d" {top}'
                    f'custom_padding="22px|0px|22px|0px|false|false" custom_margin="||0px||false|false"]'
                    f"{body}[/et_pb_toggle]")
    right = f'[et_pb_column type="3_5" {V}]{toggles}[/et_pb_column]'
    row = (f'[et_pb_row column_structure="2_5,3_5" use_custom_gutter="on" gutter_width="4" module_class="rd-level rd-level--spread" make_equal="on" {V}]'
           f"{left}{right}[/et_pb_row]")
    return section(label, row, css_id=css_id)


ROW_W = "1120px"  # content width for template rows: leaves room either side so text never runs to the screen edge


def hero(pills, h1, intro_html, primary, secondary, img, img_alt):
    """Page header in the GSC Connector style: red pills, H1, intro, a red button and an outline button on the left;
    the graphic in a red dotted frame on the right; red glow top right. Copy is the page's own."""
    pill_mod = (f'[et_pb_text module_class="rd-pills rd-pills--red" {V} custom_margin="||12px||false|false"]'
                f'<ul>{"".join(f"<li>{p}</li>" for p in pills)}</ul>[/et_pb_text]')
    text = (f'[et_pb_text {V} text_text_color="#ffffff" text_font_size="18px" text_line_height="1.7em" '
            f'header_text_color="#ffffff" header_font_size="48px" header_line_height="1.1em" '
            f'header_font_size_tablet="38px" header_font_size_phone="32px" header_font_size_last_edited="on|phone" '
            f'custom_margin="||26px||false|false"]<h1>{h1}</h1>{intro_html}[/et_pb_text]')
    btn2 = (f'[et_pb_button button_url="{secondary[1]}" button_text="{attr(secondary[0])}" button_alignment="left" {V} '
            f'custom_button="on" button_text_size="16px" button_text_color="#ffffff" button_border_width="1px" '
            f'button_border_color="#b3b3b3" button_border_radius="8px" button_on_hover="off" '
            f'custom_margin="12px||||false|false"][/et_pb_button]')
    left = f'[et_pb_column type="3_5" {V}]{pill_mod}{text}{button(primary[0], primary[1], align="left")}{btn2}[/et_pb_column]'
    right = (f'[et_pb_column type="2_5" {V} custom_padding="14px|14px|14px|14px|false|false" '
             f'border_radii="on|18px|18px|18px|18px" border_width_all="3px" border_color_all="{RED}" '
             f'border_style_all="dotted"][et_pb_image src="{img}" alt="{attr(img_alt)}" title_text="{attr(img_alt)}" '
             f'{V} border_radii="on|10px|10px|10px|10px"][/et_pb_image][/et_pb_column]')
    row = (f'[et_pb_row column_structure="3_5,2_5" {V} max_width="{ROW_W}" '
           f'custom_padding="0px|0px|0px|0px|false|false"]{left}{right}[/et_pb_row]')
    return (f'[et_pb_section fb_built="1" admin_label="Hero" {V} background_color="#000000" '
            f'use_background_color_gradient="on" background_color_gradient_type="circular" '
            f'background_color_gradient_direction_radial="top right" '
            f'background_color_gradient_stops="rgba(224,43,32,0.28) 0%|rgba(0,0,0,0) 55%" '
            f'custom_padding="90px||80px|||"]{row}[/et_pb_section]')


def contact_section(h2, lead, form='[form id="824"]', label="Contact", bg="#0b0d10"):
    """Closing contact section in the template style: bold heading and readable intro on the left, the form in a
    card on the right. Replaces the old footer block whose intro text was black on black."""
    left = (f'[et_pb_column type="2_5" {V}][et_pb_text {V} text_text_color="#b8bec6" text_font_size="18px" '
            f'text_line_height="1.65em" header_2_text_color="#ffffff" header_2_font_size="40px" '
            f'header_2_line_height="1.15em"]<h2>{h2}</h2><p>{lead}</p>[/et_pb_text][/et_pb_column]')
    right = (f'[et_pb_column type="3_5" {V} {CARD}][et_pb_code {V}]{form}[/et_pb_code][/et_pb_column]')
    row = (f'[et_pb_row column_structure="2_5,3_5" use_custom_gutter="on" gutter_width="4" {V}]{left}{right}'
           "[/et_pb_row]")
    return section(label, row, bg=bg, css_id="contact")
