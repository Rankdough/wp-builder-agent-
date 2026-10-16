"""Site Migration Services page, rebuilt natively in the service page template. All wording is read from the current
page and kept word for word (checked before saving). The hand-coded sections (Code modules with their own CSS) are
replaced by Divi modules: header graphic instead of the header form, "Migrations We Handle" icon cards, two feature
sections (risks, stages) with migration graphics, then the ProPlayerTeam proof band and the FAQ as Toggle modules
with the JSON-LD kept in a data-only Code module. The final contact section is kept as it is.
Dry run unless --confirm-site. Usage (add --site <name>): migration_page.py <page_id> [--confirm-site X]"""
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
SHOTS = {
    "plan": (LP / "migration-plan-example.png", "Example SEO migration plan: URLs crawled, redirects mapped, "
             "checks before launch, and the plan from benchmark to launch-day checks"),
    "redirects": (LP / "migration-redirects-example.png", "Example redirect check: old URLs mapped to new ones, "
                  "with correct 301s, missing redirects and redirect chains"),
    "hw_chart": (LP / "hostelworld-migration-chart.png", "Hostelworld organic traffic before and after moving its "
                 "German, French, Spanish and Italian sites from subdomains to subfolders (Ahrefs estimates)"),
    "ppt_chart": (LP / "proplayerteam-migration-chart.png", "ProPlayerTeam organic clicks before and after its move "
                  "to Shopify (Search Console)"),
    "monitor": (LP / "migration-monitor-example.png", "Example launch monitor: organic clicks against the "
                "pre-launch benchmark, indexing, crawl errors and rankings after launch"),
}
ICONS = ["refresh", "globe", "layout", "unlink", "file", "share", "eyeoff", "copy", "bars", "search", "route",
         "window", "activity"]
CHECKLIST = "https://www.rankdough.com/site-migration-services/site-migration-checklist/"


def code_bodies(raw):
    return [re.sub(r"<style.*?</style>", "", m.group(1), flags=re.S)
            for m in re.finditer(r"\[et_pb_code[^\]]*\](.*?)\[/et_pb_code\]", raw, re.S)]


def find(pattern, body, n=None):
    found = re.findall(pattern, body, re.S)
    if n is not None and len(found) != n:
        raise SystemExit(f"Expected {n} matches of {pattern[:40]!r}, found {len(found)}")
    return found


def head(body):
    h2 = find(r"<h2>(.*?)</h2>", body, 1)[0]
    lead = find(r'<p class="lead"[^>]*>(.*?)</p>', body, 1)[0]
    return h2, f"<p>{lead}</p>"


def build(raw, img, icons):
    secs = T.sections(raw)
    labels = [re.search(r'admin_label="([^"]*)"', s[:400]) for s in secs]
    labels = [m.group(1) if m else "" for m in labels]
    by = dict(zip(labels, secs))
    need = ["Migration proof", "Migration risks", "What is included", "Migration types", "Migration FAQ", "Footer"]
    missing = [n for n in need if n not in by]
    if missing:
        raise SystemExit(f"Sections not found: {missing}")
    code = {n: code_bodies(by[n])[0] for n in need[:-1]}

    hero = T.swap_header_form(secs[0], img["plan"], SHOTS["plan"][1])

    h2, lead = head(code["Migration types"])
    types = find(r"<h3>(.*?)</h3><p>(.*?)</p>", code["Migration types"], 4)
    who = T.cards_section("Migrations we handle", h2, lead,
                          [(ic, t, f"<p>{b}</p>") for ic, (t, b) in zip(("refresh", "globe", "layout"), types[:3])],
                          icons, note_html=f"<h3>{types[3][0]}</h3><p>{types[3][1]}</p>")

    h2, lead = head(code["Migration risks"])
    risks = find(r"<h3>(.*?)</h3><p>(.*?)</p>", code["Migration risks"], 6)
    platforms = ["Shopify", "WordPress", "WooCommerce", "Magento", "BigCommerce", "Custom builds"]
    risk_sec = T.feature("Migration risks", img["redirects"], SHOTS["redirects"][1], True, h2, lead,
                         [(ic, t, f"<p>{b}</p>") for ic, (t, b) in
                          zip(("unlink", "file", "share", "eyeoff", "copy", "bars"), risks)],
                         icons, ("Get The Free Migration Checklist", CHECKLIST),
                         pills=("Platforms we migrate", platforms))

    h2, lead = head(code["What is included"])
    stages = find(r'<span class="num">(.*?)</span><h3>(.*?)</h3><p>(.*?)</p>', code["What is included"], 6)
    dev_pills = ["Redirect map", "Checklists", "Staging tests", "Launch-day checks", "Post-launch monitoring"]
    stage_sec = T.feature("What is included", img["monitor"], SHOTS["monitor"][1], False, h2, lead,
                          [(ic, f"{n}: {t}", f"<p>{b}</p>") for ic, (n, t, b) in
                           zip(("search", "route", "file", "share", "window", "activity"), stages)],
                          icons, ("Talk to Us Before You Launch", "#contact"),
                          pills=("What your developers get", dev_pills))

    p = code["Migration proof"]
    kicker = find(r'<span class="num">(.*?)</span>', p, 1)[0]
    stat = re.sub(r"<[^>]+>", "", find(r'<p class="stat">(.*?)</p>', p, 1)[0])
    ph2 = find(r"<h2>(.*?)</h2>", p, 1)[0]
    plead = find(r'<p class="lead"[^>]*>(.*?)</p>', p, 1)[0]
    hw = T.proof("Hostelworld result", kicker, "+25%",
                 "Hostelworld: Organic Traffic Up 25% a Year After Moving to Subfolders",
                 "<p>A migration done well does more than hold traffic steady. Hostelworld's German, French, Spanish "
                 "and Italian sites moved from subdomains to subfolders. Within four months, organic traffic across "
                 "the four languages was back above its pre-migration level. A year later it was up 25%. We have also "
                 "run migrations for ProPlayerTeam and Smyths Toys.</p>",
                 bg="#000000", img=img["hw_chart"], img_alt=SHOTS["hw_chart"][1], image_left=False)
    proof = hw + T.proof("ProPlayerTeam result", kicker, stat, ph2, f"<p>{plead}</p>", img=img["ppt_chart"],
                         img_alt=SHOTS["ppt_chart"][1], image_left=True)

    f = code["Migration FAQ"]
    fh2, flead = head(f)
    qa = [(q, f"<p>{a}</p>") for q, a in find(r"<summary><h3>(.*?)</h3></summary><p>(.*?)</p>", f)]
    jsonld = re.search(r'<script type="application/ld\+json">.*?</script>', f, re.S)
    faq = T.faq("Migration FAQ", fh2, flead, qa, jsonld.group(0) if jsonld else None)

    footer = by["Footer"]
    if 'module_id="contact"' not in footer[:600]:
        footer = footer.replace('admin_label="Footer"', 'admin_label="Footer" module_id="contact"', 1)
    return hero + who + risk_sec + stage_sec + proof + faq + footer


FETCH = """async (id) => (await (await fetch(`/wp-json/wp/v2/pages/${id}?context=edit&_fields=status,content`,
    {headers: {'X-WP-Nonce': wpApiSettings.nonce}})).json())"""

site = script_site()
args = [a for a in sys.argv[1:] if not a.startswith("--confirm-site")]
confirm = sys.argv[sys.argv.index("--confirm-site") + 1] if "--confirm-site" in sys.argv else None
if confirm:
    args.remove(confirm)
page_id, live = int(args[0]), confirm == site.name
SOURCE = ROOT / "runs" / "migration-layout.txt"  # the original page, read before any rebuild
log = RunLog(site.name, "migration-page" if live else "migration-page-dry")
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=not live, headless=True, allowed_writes=frozenset({
        MEDIA_UPLOAD, f"et_fb_ajax_save@{page_id}", "et_core_portability_import", "et_fb_process_imported_content",
        "wpfc_delete_cache", "wpfc_delete_cache_and_minified"}))
    try:
        s.login()
        s.goto("/wp-admin/")
        page = s.page.evaluate(FETCH, page_id)
        current = page["content"]["raw"]
        original = SOURCE.read_text(encoding="utf-8")
        (log.backup / f"{page_id}-before.txt").write_text(current, encoding="utf-8")
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
        new = build(original, img, icons)
        words = T.visible_words(new)
        lost = [seg for seg in T.text_segments(original) if seg not in words]
        if lost:
            raise SystemExit("Text would be lost: " + " | ".join(lost[:10]))
        if "<style" in new or new.count("[et_pb_code") != 2:
            raise SystemExit("Expected no CSS and only two Code modules (JSON-LD and the contact form)")
        (log.dir / f"{page_id}-after.txt").write_text(new, encoding="utf-8")
        print(f"All {len(T.text_segments(original))} text pieces kept. No CSS. {len(original)} -> {len(new)} chars.")
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
