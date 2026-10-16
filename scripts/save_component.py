"""Build a template component on a throwaway draft and save it to the Divi Library for later use, then move the draft
to Trash. Nothing is added to a live page. Usage (add --site <name>): save_component.py <copy_from_page_id> --confirm-site X"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.adapters.divi.vb import LIBRARY_ACTION, VisualBuilder, save_to_library
from wpagent.adapters.wp.media import upload_image
from wpagent.adapters.wp.pages import NEW_DRAFT, clone_as_draft, trash_draft
from wpagent.browser.session import MEDIA_UPLOAD, Session
from wpagent.config import ROOT, global_colors, script_site
from wpagent.layout import service_template as T
from wpagent.layout.render import portability_json
from wpagent.runlog import RunLog

NAME = "Component: numbered items with intro (Oct 2026)"
ICONS = ["unlink", "file", "external", "eyeoff", "copy", "bars"]
ITEMS = [  # sample copy (migration risks); swap per page when it is used
    ("unlink", "Redirects missing or wrong", "<p>Old URLs that return 404s or redirect to the wrong page lose the rankings and links they earned.</p>"),
    ("file", "Content and metadata lost", "<p>Titles, descriptions, headings, copy and structured data often get dropped or rewritten when templates change.</p>"),
    ("external", "Internal links broken", "<p>New navigation and templates can orphan key pages or send link equity to the wrong places.</p>"),
    ("eyeoff", "Search engines and AI crawlers blocked", "<p>Staging rules, noindex tags or JavaScript-only rendering can hide the new site from Google and AI crawlers.</p>"),
    ("copy", "Staging site indexed", "<p>An open staging site can get indexed and compete with your live pages.</p>"),
    ("bars", "No benchmark to measure against", "<p>Without a pre-launch baseline you cannot tell what dropped, where, or why.</p>"),
]

site = script_site()
args = [a for a in sys.argv[1:] if not a.startswith("--confirm-site")]
confirm = sys.argv[sys.argv.index("--confirm-site") + 1] if "--confirm-site" in sys.argv else None
if confirm:
    args.remove(confirm)
if confirm != site.name:
    sys.exit(f"Writes a draft and a library layout: pass --confirm-site {site.name}")
source = int(args[0])
log = RunLog(site.name, "save-component")
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=False, headless=True, allowed_writes=frozenset({
        NEW_DRAFT, MEDIA_UPLOAD, "et_core_portability_import", "et_fb_process_imported_content", LIBRARY_ACTION}))
    try:
        s.login()
        icons = {n: upload_image(s, ROOT / "runs" / "lp" / "icons" / f"risk-icon-{n}.png")["source_url"] for n in ICONS}
        draft = clone_as_draft(s, source)
        s.allowed_writes = s.allowed_writes | {f"et_fb_ajax_save@{draft}", f"trash@{draft}"}
        layout = T.numbered_items(
            "01 / Migration risks", "Protect every ranking. Plan every move.",
            "<p>A successful migration is more than a tech project. We help you avoid the common pitfalls that cost "
            "traffic, rankings and revenue.</p>",
            ("Get The Free Migration Checklist", "https://www.rankdough.com/site-migration-services/site-migration-checklist/"),
            ITEMS, icons, "Platforms we migrate",
            ["Shopify", "WordPress", "WooCommerce", "Magento", "BigCommerce", "Custom builds"])
        f = log.dir / "import.json"
        f.write_text(portability_json(layout, draft, global_colors(site.name)), encoding="utf-8")
        vb = VisualBuilder(s, draft)
        vb.open()
        vb.import_layout(f, log.backup)
        vb.save_draft()
        vb.open()
        save_to_library(vb, NAME)
        s.page.screenshot(path=str(log.dir / "component.png"), full_page=False)
        trash_draft(s, draft)
        print(f"Saved to Divi Library as {NAME!r}. Throwaway draft {draft} moved to Trash.")
    finally:
        s.close()
        log.close()
