"""Shopify SEO page rebuilt in the service page template. All existing copy is kept word for word (checked); new
sections explain the Shopify-specific issues we fix and what changes after. One H1 (the page had three).
Reads the live page at run time. Dry run unless --confirm-site. Usage (add --site <name>): shopify_page.py <page_id> [--confirm-site X]"""
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
from wpagent.layout import service_template as T
from wpagent.layout.render import portability_json
from wpagent.runlog import RunLog

LP = ROOT / "runs" / "lp"
CONTACT = ("Get a Free Video Audit", "#contact")
SHOTS = {
    "hero": (LP / "shopify-audit-hero.png", "Example Shopify SEO audit: duplicate product URLs from collection paths, "
             "collections without copy and indexed tag filter pages, ranked by priority"),
    "chat": (LP / "shopify-chat-example.png", "Example: Claude reading Search Console data to pick the Shopify "
             "collection pages closest to page one"),
    "ppt": (LP / "proplayerteam-migration-chart2.png", "ProPlayerTeam organic clicks before and after its move to "
            "Shopify (Search Console)"),
}
ICONS = ["copy", "file", "layout", "unlink", "bars", "activity", "search", "cart", "growth", "shield", "window",
         "checksq"]
ISSUES = [  # Shopify-specific, accurate to how the platform works
    ("Duplicate product URLs", "<p>Shopify serves every product at /products/ and again under each collection path. "
     "We make your theme link to one URL so ranking signals are not split.</p>",
     [("/collections/shoes/products/trail-one", "linked in theme", "Duplicate", "warn"),
      ("/products/trail-one", "canonical", "OK", "ok")]),
    ("Collections with no copy", "<p>Most collection pages are a grid of products and nothing else. A short intro "
     "and answers to buyer questions give Google something to rank.</p>",
     [("/collections/running-shoes", "0 words above products", "Add copy", "warn"),
      ("/collections/kids", "160 words, FAQ", "OK", "ok")]),
    ("Tag and filter pages indexed", "<p>Tag filters create thousands of thin URLs. We keep the useful ones and "
     "stop the rest using up Google's attention.</p>",
     [("/collections/shoes/red+size-9", "indexed", "Review", "warn"),
      ("/collections/shoes/trail", "indexed, has copy", "Keep", "ok")]),
    ("Apps slowing the store", "<p>Every app adds scripts. We find the ones that slow your templates down and the "
     "ones you no longer use.</p>",
     [("Reviews app", "320 KB on every page", "Review", "warn"), ("Theme", "LCP 2.1s on mobile", "OK", "ok")]),
    ("Product schema gaps", "<p>Price, stock and reviews in structured data help your products show properly in "
     "Google and in AI shopping answers.</p>",
     [("Product schema", "no review data", "Review", "warn"), ("Offer schema", "price and stock", "OK", "ok")]),
    ("robots.txt and sitemaps", "<p>Shopify lets you edit robots.txt through robots.txt.liquid. We check what is "
     "blocked, what is in the sitemap, and what Google actually indexes.</p>",
     [("/search?q=", "blocked in robots.txt", "OK", "ok"), ("Sitemap products", "1,486 vs 1,102 indexed", "Review", "warn")]),
]


def strip(h):
    return re.sub(r"<[^>]+>", "", h).strip()


def build(raw, img, icons):
    texts = [m.group(1) for m in re.finditer(r"\[et_pb_text[^\]]*\](.*?)\[/et_pb_text\]", raw, re.S)]
    t0, t1, t2, t3, t4 = texts[:5]
    h1a, h1b = [strip(x) for x in re.findall(r"<h1[^>]*>(.*?)</h1>", t0, re.S) if strip(x)]
    intro = f"<p>{strip(t1)}</p>"
    benefit_h2 = html.unescape(re.search(r'\[et_pb_heading title="([^"]*)"', raw).group(1))
    benefit = "".join(f"<p>{strip(p)}</p>" for p in re.findall(r"<p[^>]*>(.*?)</p>", t2, re.S) if strip(p))
    why_h2 = strip(re.search(r"<h2[^>]*>(.*?)</h2>", t3, re.S).group(1))
    why = [strip(p) for p in re.findall(r"<p>(.*?)</p>", t3, re.S)]
    us_h2 = strip(re.search(r"<h2[^>]*>(.*?)</h2>", t4, re.S).group(1))
    us = "".join("<p>" + re.sub(r"</?span[^>]*>", "", p).replace("<b>", "<strong>").replace("</b>", "</strong>") + "</p>"
                 for p in re.findall(r"<p>(.*?)</p>", t4, re.S))

    hero = T.hero(["Shopify", "Shopify Plus", "Revenue, not just traffic"], f"{h1a} {h1b}", intro, CONTACT,
                  ("See What We Fix", "#issues"), img["hero"], SHOTS["hero"][1])
    fit = T.feature("Is Shopify SEO for you", img["chat"], SHOTS["chat"][1], False, benefit_h2, benefit, [], icons,
                    CONTACT, pills=("A good fit if you", ["Already sell on Shopify", "Run paid ads that convert",
                                                          "Have products people search for", "Use Shopify or Shopify Plus"]))
    issues = T.accordion_section(
        "Shopify issues", "What we fix", "Shopify SEO Problems We Fix",
        "<p>Shopify handles the basics. These are the store-level issues that hold rankings and sales back, and we "
        "check every one.</p>", CONTACT,
        [(t, b + T.check_panel(rows)) for t, b, rows in ISSUES], css_id="issues")
    proof = T.proof("ProPlayerTeam result", "Shopify result", "+104%",
                    "ProPlayerTeam: Organic Clicks Up 104% in Two Months After Moving to Shopify",
                    "<p>We ran the SEO side of ProPlayerTeam's move to Shopify. Organic clicks rose 104% in the two "
                    "months after launch.</p>", img=img["ppt"], img_alt=SHOTS["ppt"][1], image_left=True)
    why_us = T.section("Why us", T.text_row(f"<h2>{us_h2}</h2>{us}", align="left", size=18, pad="0px||10px|||")
                       + T.cta_banner("checksq", why_h2 + " " + why[0], " ".join(why[1:]), CONTACT, icons))
    item = lambda k, ic: (ic, ISSUES[k][0], ISSUES[k][1])
    changes = T.outcomes("Shopify outcomes", "What changes after Shopify SEO", [
        ("search", "Get found", "<p>Google indexes the pages that sell, not thousands of filter and duplicate URLs."
         "</p>", [item(0, "copy"), item(2, "layout")]),
        ("cart", "Sell more", "<p>Collections and products rank for what buyers search and convert when they land."
         "</p>", [item(1, "file"), item(4, "bars")]),
        ("growth", "Keep growing", "<p>A faster, cleaner store that holds its rankings as you add products.</p>",
         [item(3, "activity"), item(5, "shield")]),
    ], icons, CONTACT)
    secs = [m.start() for m in re.finditer(r"\[et_pb_section[\s\]]", raw)]
    footer = raw[secs[-1]:]
    if 'admin_label="Footer"' not in footer[:600]:
        raise SystemExit("Final contact section not found")
    if 'module_id="contact"' not in footer[:600]:
        footer = footer.replace('admin_label="Footer"', 'admin_label="Footer" module_id="contact"', 1)
    return hero + fit + issues + proof + why_us + changes + footer


FETCH = """async (id) => (await (await fetch(`/wp-json/wp/v2/pages/${id}?context=edit&_fields=status,content`,
    {headers: {'X-WP-Nonce': wpApiSettings.nonce}})).json())"""

site = script_site()
args = [a for a in sys.argv[1:] if not a.startswith("--confirm-site")]
confirm = sys.argv[sys.argv.index("--confirm-site") + 1] if "--confirm-site" in sys.argv else None
if confirm:
    args.remove(confirm)
page_id, live = int(args[0]), confirm == site.name
log = RunLog(site.name, "shopify-page" if live else "shopify-page-dry")
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
            media = {k: upload_image(s, p) for k, (p, _) in SHOTS.items()}
            for k, m in media.items():
                s.allowed_writes = s.allowed_writes | {f"save-attachment@{m['id']}"}
                set_alt_text(s, m["id"], SHOTS[k][1])
            img = {k: m["source_url"] for k, m in media.items()}
            icons = {n: upload_image(s, LP / "icons" / f"audit-icon2-{n}.png")["source_url"] for n in ICONS}
        else:
            img = {k: f"{site.url}/wp-content/uploads/YYYY/MM/{p.name}" for k, (p, _) in SHOTS.items()}
            icons = {n: f"{site.url}/wp-content/uploads/YYYY/MM/audit-icon2-{n}.png" for n in ICONS}
        new = build(raw, img, icons)
        words = T.visible_words(new).replace("’", "'").lower()
        lost = [g for g in T.text_segments(raw) if g.replace("’", "'").lower() not in words
                and g.strip(" . ") and g not in ("GET IN TOUCH",)]
        if lost:
            raise SystemExit("Text would be lost: " + " | ".join(lost[:10]))
        if new.count("<h1") != 1:
            raise SystemExit(f"Expected one H1, found {new.count('<h1')}")
        (log.dir / f"{page_id}-after.txt").write_text(new, encoding="utf-8")
        print(f"All original text kept, one H1. {len(raw)} -> {len(new)} chars.")
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
