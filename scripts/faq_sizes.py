"""Set every FAQ toggle (Toggle modules, not the numbered rd-acc accordions) to the site standard: question 18px,
answer 16px, via each module's own font size settings. Reads each page live just before editing. Dry run unless
--confirm-site. Usage (add --site <name>): faq_sizes.py <page_id ...> [--confirm-site X]"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.adapters.divi.vb import VisualBuilder
from wpagent.adapters.wp.cache import clear_caches
from wpagent.browser.session import Session
from wpagent.config import global_colors, script_site
from wpagent.layout.render import portability_json
from wpagent.layout.restyle import visible_text
from wpagent.runlog import RunLog

SIZES = {"title_font_size": "18px", "body_font_size": "16px"}
FETCH = """async (id) => (await (await fetch(`/wp-json/wp/v2/pages/${id}?context=edit&_fields=status,link,content`,
    {headers: {'X-WP-Nonce': wpApiSettings.nonce}})).json())"""


def fix(raw):
    n = 0

    def tag(m):
        nonlocal n
        t = m.group(0)
        if "rd-acc" in t:
            return t
        t = re.sub(r'\s(title_font_size|body_font_size)(_tablet|_phone|_last_edited)?="[^"]*"', "", t)
        n += 1
        return t[:-1] + "".join(f' {k}="{v}"' for k, v in SIZES.items()) + "]"
    return re.sub(r"\[et_pb_toggle [^\]]*\]", tag, raw), n


site = script_site()
args = [a for a in sys.argv[1:] if not a.startswith("--confirm-site")]
confirm = sys.argv[sys.argv.index("--confirm-site") + 1] if "--confirm-site" in sys.argv else None
if confirm:
    args.remove(confirm)
live = confirm == site.name
log = RunLog(site.name, "faq-sizes" if live else "faq-sizes-dry")
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=not live, headless=True, allowed_writes=frozenset({
        "et_core_portability_import", "et_fb_process_imported_content", "wpfc_delete_cache",
        "wpfc_delete_cache_and_minified"}))
    try:
        s.login()
        for pid in map(int, args):
            s.goto("/wp-admin/")
            page = s.page.evaluate(FETCH, pid)
            raw = page["content"]["raw"]
            new, n = fix(raw)
            if visible_text(new) != visible_text(raw):
                print(f"{pid}: text would change, skipped")
                continue
            print(f"{page['link'].replace(site.url, '')} ({pid}): {n} FAQ toggle(s)")
            (log.backup / f"{pid}-before.txt").write_text(raw, encoding="utf-8")
            if live and n:
                s.allowed_writes = s.allowed_writes | {f"et_fb_ajax_save@{pid}"}
                f = log.dir / f"{pid}-import.json"
                f.write_text(portability_json(new, pid, global_colors(site.name)), encoding="utf-8")
                vb = VisualBuilder(s, pid)
                vb.open()
                vb.import_layout(f, log.backup)
                (vb.save_draft if page["status"] == "draft" else vb.save_published)()
        if live:
            clear_caches(s)
    finally:
        s.close()
        log.close()
