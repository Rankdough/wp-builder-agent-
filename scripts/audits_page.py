"""Website SEO Audits page redesign, all native Divi modules:
1. "Who This Service Is For": the three items become icon cards (same wording, icons instead of tick marks).
2. Technical and content audit sections in one shared format: graphic on one side (mirrored), heading, intro and
   pill card on the other, then a centred heading, a 3 x 2 grid of icon cards and a centred button.
3. "What changes after your audit": three outcome groups (Get found / Perform better / Keep growing) at the end of
   the page, before the final contact section.
Icons are small PNGs in the media library used as Blurb images. Works on a draft or the live page.
Dry run unless --confirm-site. Usage (add --site <name>): audits_page.py <page_id> [--confirm-site X]"""
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.adapters.divi.vb import VisualBuilder
from wpagent.adapters.wp.cache import clear_caches
from wpagent.adapters.wp.media import set_alt_text, upload_image
from wpagent.browser.session import MEDIA_UPLOAD, Session
from wpagent.config import ROOT, global_colors, script_site
from wpagent.layout.render import portability_json
from wpagent.runlog import RunLog

LP = ROOT / "runs" / "lp"
OLD_IMGS = ("travel-seo-service-case-study", "technical-seo-audit-checklist", "audit-checklist")
SHOTS = {
    "checklist": (LP / "seo-audit-checklist-example.png",
                  "Example technical SEO audit checklist: crawling, rendering, indexing, site architecture, "
                  "international SEO, backlinks and e-commerce, each with checks marked OK, to fix or to find out"),
    "content": (LP / "content-audit-example.png",
                "Example content audit: pages scored on Search Console data with keep, improve, merge or remove "
                "verdicts"),
}
ICONS = ["growth", "link", "shield", "window", "bars", "cart", "pie", "zap", "target", "merge", "flag", "quote",
         "search", "file"]
V = '_builder_version="4.27.4" _module_preset="default" global_colors_info="{}" theme_builder_area="post_content"'
CARD = ('background_color="#111316" custom_padding="28px|28px|28px|28px|false|false" '
        'border_radii="on|16px|16px|16px|16px" border_width_all="1px" border_color_all="#23272d" border_style_all="solid"')
BUTTON = (f'[et_pb_button button_url="https://www.rankdough.com/contact/" button_text="Get Your Audit" '
          f'button_alignment="center" {V} custom_button="on" button_text_size="16px" button_text_color="#ffffff" '
          f'button_bg_color="#e02b20" button_border_width="0px" button_border_color="#e02b20" '
          f'button_border_radius="8px" button_on_hover="off"][/et_pb_button]')

TECH = [
    ("growth", "Google finds and keeps your money pages", "We check robots.txt, sitemaps, redirects and Search "
     "Console coverage, so the pages that sell get crawled and indexed instead of junk URLs."),
    ("link", "Authority flows to the pages that sell", "Short click paths, breadcrumbs and internal links point "
     "Google at your key pages, in every country you sell to."),
    ("shield", "Protect the rankings you've built", "Broken and spammy backlinks, hidden text and cloaking can cost "
     "you rankings. We find them and fix the ones that matter."),
    ("window", "Visitors and Google see the same site", "Navigation and content load in the raw HTML, pages work on "
     "mobile, and forms don't lose leads."),
    ("bars", "More from the rankings you already have", "Clear titles and headings, no duplicate pages, working "
     "schema, and a brand that shows properly on Google and Maps."),
    ("cart", "Shop pages that rank and sell", "Category and product pages with reviews, clean filters and unique "
     "copy, so shoppers land where they can buy."),
]
CONTENT = [
    ("pie", "Know which pages earn and which don't", "Every page scored on clicks, impressions and position from "
     "Search Console, then marked keep, improve, merge or remove."),
    ("target", "Pages that match what buyers search", "Each key page is checked against what Google ranks for its "
     "main search: format, depth and the questions buyers ask."),
    ("flag", "Win the topics your competitors own", "We list the topics rivals rank for that you don't cover yet, "
     "and link them to the pages that sell."),
    ("zap", "Quick wins from pages close to page one", "Pages sitting in positions 5 to 15 get specific fixes "
     "first. They usually move fastest."),
    ("merge", "Stop your pages competing with each other", "Thin, duplicate and outdated pages are flagged, with the "
     "page to merge them into or update."),
    ("quote", "Get quoted by AI assistants", "Answers near the top, facts in plain text and named sources make your "
     "pages easier for ChatGPT and Google's AI answers to quote."),
]
SECTIONS = {
    "technical": {
        "h2": "Technical SEO Audit: Fix What Holds Your Site Back",
        "intro": "Content and links do little for pages Google can't crawl, index or trust. We run over 250 checks "
                 "across 16 areas on your Search Console data, a full crawl, Ahrefs and the site itself, then rank "
                 "every fix by what it's worth to your traffic and sales.",
        "card": "What you get", "card_p": "Everything your developers need to start fixing straight away.",
        "pills": ["250+ point checklist", "Fix list ranked critical first", "Example URLs for every issue",
                  "Traffic linked to each issue", "Effort and owner for every fix", "AI crawler access check",
                  "Recorded video walkthrough", "Live tracker as fixes go live"],
        "grid_h2": "A healthier site. More room to grow.", "cards": TECH,
    },
    "content": {
        "h2": "Content Audit: Make Every Page Earn Its Place",
        "intro": "Technical fixes let Google read your site. The content audit tells you which pages bring in "
                 "traffic, which to improve, which to merge or remove, and what to write next.",
        "card": "What you get", "card_p": "A clear verdict and next step for every page on your site.",
        "pills": ["Verdict for every page", "Search Console data per page", "Pages close to page one",
                  "Merge plan for competing pages", "Content gaps vs competitors", "Internal linking plan",
                  "Topics to write next", "Recorded video walkthrough"],
        "grid_h2": "Stronger pages. More of them earning.", "cards": CONTENT,
    },
}
OUTCOMES = [
    ("search", "Get found", "Remove the roadblocks stopping Google from finding and understanding your site.",
     [("file", *TECH[0][1:]), ("window", *TECH[3][1:])]),
    ("bars", "Perform better", "Fix what's holding your pages back so your existing rankings work harder.",
     [("link", *TECH[1][1:]), ("growth", *TECH[4][1:])]),
    ("shield", "Keep growing", "Protect your progress and get more revenue from the pages that sell.",
     [("shield", *TECH[2][1:]), ("cart", *TECH[5][1:])]),
]


def blurb(icon, title, body_html, place="top", card=True, title_size=19, extra=""):
    return (f'[et_pb_blurb title="{html.escape(title, quote=True)}" image="{icon}" alt="" use_icon="off" '
            f'icon_placement="{place}" image_icon_width="64px" icon_alignment="left" text_orientation="left" {V} header_level="h3" '
            f'header_text_color="#ffffff" header_font_size="{title_size}px" header_line_height="1.3em" '
            f'body_text_color="#b8bec6" body_font_size="15px" body_line_height="1.7em" '
            f'{CARD if card else ""} {extra}]{body_html}[/et_pb_blurb]')


def heading_row(h2):
    return (f'[et_pb_row {V} custom_padding="20px||10px|||"][et_pb_column type="4_4" {V}]'
            f'[et_pb_text {V} text_orientation="center" header_2_text_color="#ffffff"]<h2>{h2}</h2>[/et_pb_text]'
            "[/et_pb_column][/et_pb_row]")


def card_rows(cards, icons):
    out = ""
    for i in (0, 3):
        # Card styling sits on the column so the row's equal heights evens the boxes out.
        cols = "".join(f'[et_pb_column type="1_3" {V} {CARD}]{blurb(icons[ic], t, f"<p>{b}</p>", card=False)}'
                       "[/et_pb_column]" for ic, t, b in cards[i:i + 3])
        out += (f'[et_pb_row column_structure="1_3,1_3,1_3" use_custom_gutter="on" gutter_width="2" make_equal="on" '
                f'{V} custom_padding="8px||8px|||"]{cols}[/et_pb_row]')
    return out


def button_row():
    return f'[et_pb_row {V} custom_padding="20px||0px|||"][et_pb_column type="4_4" {V}]{BUTTON}[/et_pb_column][/et_pb_row]'


def section(key, img_src, img_alt, image_left, icons):
    c = SECTIONS[key]
    pills = "".join(f"<li>{p}</li>" for p in c["pills"])
    text_col = (
        f'[et_pb_column type="3_5" {V}]'
        f'[et_pb_text {V} text_text_color="#b8bec6" text_font_size="18px" text_line_height="1.65em" '
        f'header_2_text_color="#ffffff" custom_margin="||24px||false|false"]<h2>{c["h2"]}</h2><p>{c["intro"]}</p>'
        "[/et_pb_text]"
        f'[et_pb_blurb title="{c["card"]}" module_class="rd-pills rd-pills--lg" {V} header_level="h3" '
        f'header_text_color="#ffffff" header_font_size="20px" body_text_color="#d4d8dd" body_font_size="17px" '
        f'background_color="#14171b" custom_padding="28px|28px|28px|28px|false|false" '
        f'border_radii="on|16px|16px|16px|16px" border_width_all="1px" border_color_all="#23272d" '
        f'border_style_all="solid"]<p>{c["card_p"]}</p><ul>{pills}</ul>[/et_pb_blurb][/et_pb_column]')
    img_col = (f'[et_pb_column type="2_5" {V}][et_pb_image src="{img_src}" alt="{img_alt}" title_text="{img_alt}" {V}]'
               "[/et_pb_image][/et_pb_column]")
    top = (f'[et_pb_row column_structure="{"2_5,3_5" if image_left else "3_5,2_5"}" {V} '
           f'custom_padding="0px||30px|||"]{img_col + text_col if image_left else text_col + img_col}[/et_pb_row]')
    label = "Audit: technical" if key == "technical" else "Audit: content"
    return (f'[et_pb_section fb_built="1" admin_label="{label}" {V} background_color="#000000" '
            f'custom_padding="70px||70px|||"]{top}{heading_row(c["grid_h2"])}{card_rows(c["cards"], icons)}'
            f"{button_row()}[/et_pb_section]")


def outcomes(icons):
    cols = ""
    for n, (ic, title, intro, items) in enumerate(OUTCOMES):
        line = 'border_width_right="1px" border_color_right="#23272d" ' if n < 2 else ""
        mods = blurb(icons[ic], title, f"<p>{intro}</p>", place="left", card=False, title_size=24,
                     extra='custom_margin="||10px||false|false"')
        for i, (jc, t, b) in enumerate(items):
            mods += blurb(icons[jc], t, f"<p>{b}</p>", place="left", card=False, title_size=18,
                          extra='custom_padding="22px||10px|||" border_width_top="1px" border_color_top="#23272d"')
        cols += (f'[et_pb_column type="1_3" {V} {line}custom_padding="0px|24px|0px|0px|false|false"]{mods}'
                 "[/et_pb_column]")
    grid = (f'[et_pb_row column_structure="1_3,1_3,1_3" use_custom_gutter="on" gutter_width="3" {V} '
            f'custom_padding="20px||10px|||"]{cols}[/et_pb_row]')
    return (f'[et_pb_section fb_built="1" admin_label="Audit: outcomes" {V} background_color="#000000" '
            f'custom_padding="70px||70px|||"]{heading_row("What changes after your audit")}{grid}{button_row()}'
            "[/et_pb_section]")


def who_row(raw, icons):
    i = raw.find("Brands Looking to Scale")
    if i == -1:
        return raw  # already converted
    a = raw.rfind("[et_pb_row", 0, i)
    b = raw.index("[/et_pb_row]", i) + len("[/et_pb_row]")
    blurbs = re.findall(r'\[et_pb_blurb title="([^"]*)"[^\]]*\](.*?)\[/et_pb_blurb\]', raw[a:b], re.S)
    if len(blurbs) == 3:  # already converted on an earlier run: rebuild from the cards
        texts = [x for t, body in blurbs for x in (html.unescape(t), body)]
    else:
        texts = re.findall(r"\[et_pb_text[^\]]*\](.*?)\[/et_pb_text\]", raw[a:b], re.S)
    if len(texts) != 6:
        raise SystemExit(f"Who This Service Is For: expected 6 text modules, found {len(texts)}")
    cards = []
    for ic, (t, body) in zip(("growth", "target", "search"), zip(texts[0::2], texts[1::2])):
        title = html.unescape(re.sub(r"<[^>]+>", "", t)).replace("✔", "").strip()
        cards.append(f'[et_pb_column type="1_3" {V} {CARD}]{blurb(icons[ic], title, body.strip(), card=False)}'
                     "[/et_pb_column]")
    row = (f'[et_pb_row column_structure="1_3,1_3,1_3" use_custom_gutter="on" gutter_width="2" make_equal="on" '
           f'{V}]{"".join(cards)}[/et_pb_row]')
    return raw[:a] + row + raw[b:]


def sections(raw):
    starts = [m.start() for m in re.finditer(r"\[et_pb_section[\s\]]", raw)]
    return list(zip(starts, starts[1:] + [len(raw)]))


def transform(raw, checklist_src, content_src, icons):
    raw = who_row(raw, icons)
    secs = sections(raw)
    first = [(a, b) for a, b in secs if any(n in raw[a:b] for n in OLD_IMGS)]
    if len(first) != 1:
        raise SystemExit(f"Expected one 'what is included' image section, found {len(first)}")
    second = [(a, b) for a, b in secs if any(k in raw[a:b] for k in (
        "Why Your Site Needs a Technical SEO Audit", 'admin_label="Audit: why it matters"', 'admin_label="Audit: content"'))]
    both = (section("technical", checklist_src, SHOTS["checklist"][1], True, icons) +
            section("content", content_src, SHOTS["content"][1], False, icons))
    a1, b1 = first[0]
    end = b1
    if second:
        a2, b2 = second[0]
        if a2 != b1:
            raise SystemExit("The two audit sections are not next to each other")
        end = b2
    raw = raw[:a1] + both + raw[end:]
    secs = sections(raw)
    old = [(a, b) for a, b in secs if 'admin_label="Audit: outcomes"' in raw[a:b]]
    if old:
        a, b = old[0]
        return raw[:a] + outcomes(icons) + raw[b:]
    footer = [a for a, b in secs if 'admin_label="Footer"' in raw[a:b]]
    if len(footer) != 1:
        raise SystemExit("Final contact section (Footer) not found")
    return raw[:footer[0]] + outcomes(icons) + raw[footer[0]:]


FETCH = """async (id) => (await (await fetch(`/wp-json/wp/v2/pages/${id}?context=edit&_fields=status,content`,
    {headers: {'X-WP-Nonce': wpApiSettings.nonce}})).json())"""

site = script_site()
args = [a for a in sys.argv[1:] if not a.startswith("--confirm-site")]
confirm = sys.argv[sys.argv.index("--confirm-site") + 1] if "--confirm-site" in sys.argv else None
if confirm:
    args.remove(confirm)
page_id, live = int(args[0]), confirm == site.name
log = RunLog(site.name, "audits-page" if live else "audits-page-dry")
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=not live, headless=True, allowed_writes=frozenset({
        MEDIA_UPLOAD, f"et_fb_ajax_save@{page_id}", "et_core_portability_import", "et_fb_process_imported_content",
        "wpfc_delete_cache", "wpfc_delete_cache_and_minified"}))
    try:
        s.login()
        s.goto("/wp-admin/")
        page = s.page.evaluate(FETCH, page_id)
        raw = page["content"]["raw"]
        (log.backup / f"{page_id}-before.txt").write_text(raw, encoding="utf-8")
        if not live:
            fake = {n: f"{site.url}/wp-content/uploads/YYYY/MM/audit-icon2-{n}.png" for n in ICONS}
            new = transform(raw, fake["growth"], fake["link"], fake)
            print(f"Dry run ({page['status']}): {len(raw)} -> {len(new)} chars. Nothing written.")
        else:
            media = {k: upload_image(s, p) for k, (p, _) in SHOTS.items()}
            for k, m in media.items():
                s.allowed_writes = s.allowed_writes | {f"save-attachment@{m['id']}"}
                set_alt_text(s, m["id"], SHOTS[k][1])
            icons = {n: upload_image(s, LP / "icons" / f"audit-icon2-{n}.png")["source_url"] for n in ICONS}
            new = transform(raw, media["checklist"]["source_url"], media["content"]["source_url"], icons)
            (log.dir / f"{page_id}-after.txt").write_text(new, encoding="utf-8")
            f = log.dir / "import.json"
            f.write_text(portability_json(new, page_id, global_colors(site.name)), encoding="utf-8")
            vb = VisualBuilder(s, page_id)
            vb.open()
            vb.import_layout(f, log.backup)
            (vb.save_draft if page["status"] == "draft" else vb.save_published)()
            if page["status"] == "publish":
                clear_caches(s)
            print(f"Page {page_id} ({page['status']}) updated. Run folder: {log.dir}")
    finally:
        s.close()
        log.close()
