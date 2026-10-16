"""Website SEO Audits page rebuilt in the service page template. Copy comes from the current page (read from it, not
retyped). Layout chosen for an audit page: header, who it is for, technical audit as a numbered accordion with
example checks, content audit feature, a 'how the audit works' timeline, outcome groups, testimonials, contact.
Text that is deliberately dropped is listed in DROPPED; any other lost text stops the run.
Dry run unless --confirm-site. Usage (add --site <name>): audits_template_page.py <page_id> [--confirm-site X]"""
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.adapters.divi.vb import VisualBuilder
from wpagent.adapters.wp.cache import clear_caches
from wpagent.adapters.wp.media import upload_image
from wpagent.browser.session import MEDIA_UPLOAD, Session
from wpagent.config import ROOT, global_colors, script_site
from wpagent.layout import service_template as T
from wpagent.layout.render import portability_json
from wpagent.runlog import RunLog

CONTACT = "https://www.rankdough.com/contact/"
ICONS = ["search", "window", "bars", "file", "activity", "checksq"]
DROPPED = {"A healthier site. More room to grow.", "Everything your developers need to start fixing straight away."}
CHECKS = [  # illustrative example rows, one per technical benefit, in the page's order
    [("/category/boots", "indexed", "OK", "ok"), ("/?sort=price", "crawled, not indexed", "Review", "warn")],
    [("/category/boots", "2 clicks from home", "OK", "ok"), ("/guides/size-chart", "no links in", "Orphan", "warn")],
    [("Referring domains", "312", "OK", "ok"), ("Spammy links", "41 domains", "Review", "warn")],
    [("Main navigation", "in the raw HTML", "OK", "ok"), ("Contact form", "fails on mobile", "Fix", "warn")],
    [("Title tag", "matches the H1", "OK", "ok"), ("Product schema", "2 errors", "Review", "warn")],
    [("Product reviews", "on cards", "OK", "ok"), ("Filter URLs", "1,240 indexed", "Review", "warn")],
]
PHASES = [
    ("Collect", [
        ("search", "Crawl and data", "<p>A full crawl joined to your Search Console data, Ahrefs backlinks and the "
         "traffic each page earns.</p>"),
        ("window", "Page-by-page browser checks", "<p>Navigation, forms, mobile layout, schema and how your brand "
         "shows on Google and Maps, checked by hand.</p>")]),
    ("Prioritise", [
        ("bars", "Every issue ranked", "<p>Critical to nice to have, with effort, impact and an owner for each "
         "fix.</p>"),
        ("file", "Evidence attached", "<p>Example URLs and the traffic each issue touches, so your developers know "
         "where to start.</p>")]),
    ("Deliver", [
        ("activity", "Video walkthrough", "<p>A short summary of the critical issues and a recorded walkthrough of "
         "the findings.</p>"),
        ("checksq", "Live tracker", "<p>The action list becomes the tracker we work from as fixes go live.</p>")]),
]
TOOLS = ["Google Search Console", "Screaming Frog crawl", "Ahrefs", "PageSpeed Insights", "Rich Results Test",
         "Desktop and mobile checks"]


def secs(raw):
    s = [m.start() for m in re.finditer(r"\[et_pb_section[\s\]]", raw)]
    return [raw[a:b] for a, b in zip(s, s[1:] + [len(raw)])]


def one(pattern, text):
    m = re.findall(pattern, text, re.S)
    if len(m) != 1:
        raise SystemExit(f"Expected one match of {pattern[:50]!r}, found {len(m)}")
    return m[0]


def blurbs(sec):
    """(title, body_html, image_url) for every icon card in a section, in order."""
    out = []
    for m in re.finditer(r'\[et_pb_blurb title="([^"]*)" image="([^"]*)"[^\]]*\](.*?)\[/et_pb_blurb\]', sec, re.S):
        out.append((html.unescape(m.group(1)), m.group(3).strip(), m.group(2)))
    return out


def pill_card(sec):
    m = re.search(r'\[et_pb_blurb title="([^"]*)" module_class="rd-pills[^\]]*\]<p>(.*?)</p><ul>(.*?)</ul>', sec, re.S)
    return html.unescape(m.group(1)), m.group(2), re.findall(r"<li>(.*?)</li>", m.group(3))


def build(raw, icons):
    S = secs(raw)
    label = lambda s: (re.search(r'admin_label="([^"]*)"', s[:500]) or [None, ""])[1]
    hero_s, who_s = S[0], S[1]
    tech = next(s for s in S if label(s) == "Audit: technical")
    cont = next(s for s in S if label(s) == "Audit: content")
    rest = [s for s in S[2:] if label(s) not in ("Audit: technical", "Audit: content")]

    h1 = re.sub(r"<[^>]+>", "", one(r"<h2>(.*?)</h2>", hero_s))
    intro = "".join(f"<p>{re.sub(r'<[^>]+>', '', p)}</p>" for p in re.findall(r"<p>(.*?)</p>", hero_s))
    hero_img = one(r'\[et_pb_image src="([^"]*seo-audit-summary[^"]*)"', hero_s)
    hero_alt = html.unescape(one(r'seo-audit-summary[^"]*" alt="([^"]*)"', hero_s))
    hero = T.hero(["250+ checks", "Technical and content", "Video walkthrough"], h1, intro,
                  ("Get in Touch", CONTACT), ("See What Is Included", "#technical"), hero_img, hero_alt)

    who_h2 = html.unescape(one(r'\[et_pb_heading title="([^"]*)"', who_s)) if "et_pb_heading" in who_s else \
        re.sub(r"<[^>]+>", "", one(r"<h2>(.*?)</h2>", who_s))
    who_cards = [(img, t, b) for t, b, img in blurbs(who_s)]
    who = T.cards_section("Who it is for", who_h2, "", who_cards, {c[0]: c[0] for c in who_cards})

    t_h2 = one(r"<h2>(.*?)</h2>", tech.split("[et_pb_blurb", 1)[0])
    t_intro = one(r"</h2><p>(.*?)</p>", tech)
    t_card = pill_card(tech)
    t_items = [(t, f"<p>{re.sub(r'</?p>', '', b)}</p>" + T.check_panel(rows))
               for (t, b, _), rows in zip(blurbs(tech), CHECKS)]
    technical = T.accordion_section("Audit: technical", "Technical audit", t_h2, f"<p>{t_intro}</p>",
                                    ("Get Your Audit", CONTACT), t_items, footer_label=t_card[0],
                                    footer_items=t_card[2], css_id="technical")

    c_h2 = one(r"<h2>(.*?)</h2>", cont.split("[et_pb_blurb", 1)[0])
    c_intro = one(r"</h2><p>(.*?)</p>", cont)
    c_card = pill_card(cont)
    c_img = one(r'\[et_pb_image src="([^"]*)"', cont)
    c_alt = html.unescape(one(r'\[et_pb_image src="[^"]*" alt="([^"]*)"', cont))
    c_grid = re.findall(r"<h2>(.*?)</h2>", cont)[-1]
    c_cards = [(img, t, b) for t, b, img in blurbs(cont)]
    content = T.feature("Audit: content", c_img, c_alt, False, c_h2, f"<p>{c_intro}</p>", c_cards,
                        {c[0]: c[0] for c in c_cards}, ("Get Your Audit", CONTACT),
                        pills=(c_card[0], c_card[2], c_card[1]), grid_h2=c_grid)

    process = T.timeline_section(
        "Audit: process", "How the audit works", "From Your Data to a Ranked Fix List",
        "<p>Three steps, built on your own data. You see the evidence behind every fix.</p>", PHASES, icons,
        ("checksq", "250+ checks. One ranked fix list.",
         "Built from your own data, in the order that brings traffic and sales back first.",
         ("Get Your Audit", CONTACT)),
        pills=("Tools we use", TOOLS))

    widen = lambda s: re.sub(r"\[et_pb_row (?![^\]]*max_width)", f'[et_pb_row max_width="{T.ROW_W}" ', s)
    return hero + who + technical + content + process + "".join(widen(s) for s in rest)


FETCH = """async (id) => (await (await fetch(`/wp-json/wp/v2/pages/${id}?context=edit&_fields=status,content`,
    {headers: {'X-WP-Nonce': wpApiSettings.nonce}})).json())"""

site = script_site()
args = [a for a in sys.argv[1:] if not a.startswith("--confirm-site")]
confirm = sys.argv[sys.argv.index("--confirm-site") + 1] if "--confirm-site" in sys.argv else None
if confirm:
    args.remove(confirm)
page_id, live = int(args[0]), confirm == site.name
log = RunLog(site.name, "audits-template" if live else "audits-template-dry")
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
        if live:
            icons = {n: upload_image(s, ROOT / "runs" / "lp" / "icons" / f"audit-icon2-{n}.png")["source_url"] for n in ICONS}
        else:
            icons = {n: f"{site.url}/wp-content/uploads/YYYY/MM/audit-icon2-{n}.png" for n in ICONS}
        new = build(raw, icons)
        words = T.visible_words(new).lower()
        lost = [g for g in T.text_segments(raw) if g.lower() not in words and g not in DROPPED]
        if lost:
            raise SystemExit("Text would be lost: " + " | ".join(lost[:10]))
        (log.dir / f"{page_id}-after.txt").write_text(new, encoding="utf-8")
        print(f"Text kept (dropped on purpose: {len(DROPPED)}). {len(raw)} -> {len(new)} chars.")
        if live:
            f = log.dir / "import.json"
            f.write_text(portability_json(new, page_id, global_colors(site.name)), encoding="utf-8")
            vb = VisualBuilder(s, page_id)
            vb.open()
            vb.import_layout(f, log.backup)
            (vb.save_draft if page["status"] == "draft" else vb.save_published)()
            if page["status"] == "publish":
                clear_caches(s)
            print(f"Page {page_id} ({page['status']}) saved. Run folder: {log.dir}")
    finally:
        s.close()
        log.close()
