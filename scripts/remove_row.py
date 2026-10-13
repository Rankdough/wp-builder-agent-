"""Delete one row from a page, found by text inside it (like deleting the row in the Visual Builder).
The text must match exactly one row. Drafts are saved as drafts; published pages are saved and the cache cleared.
Dry run unless --confirm-site. Usage (add --site <name>): remove_row.py <page_id> "<text in the row>" [--confirm-site X]"""
import re
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.adapters.divi.vb import VisualBuilder
from wpagent.adapters.wp.cache import clear_caches
from wpagent.browser.session import Session
from wpagent.config import global_colors, script_site
from wpagent.layout.render import portability_json
from wpagent.runlog import RunLog

FETCH = """async (id) => (await (await fetch(`/wp-json/wp/v2/pages/${id}?context=edit&_fields=status,content`,
    {headers: {'X-WP-Nonce': wpApiSettings.nonce}})).json())"""


def remove_row(raw: str, text: str) -> str:
    rows = [(m.start(), raw.index("[/et_pb_row]", m.end()) + len("[/et_pb_row]"))
            for m in re.finditer(r"\[et_pb_row[\s\]]", raw)]
    hits = [(a, b) for a, b in rows if text in raw[a:b]]
    if len(hits) != 1:
        raise SystemExit(f"{len(hits)} rows contain {text!r}; need exactly one")
    a, b = hits[0]
    return raw[:a] + raw[b:]


site = script_site()
args = [a for a in sys.argv[1:] if not a.startswith("--confirm-site")]
confirm = sys.argv[sys.argv.index("--confirm-site") + 1] if "--confirm-site" in sys.argv else None
if confirm:
    args.remove(confirm)
page_id, text, live = int(args[0]), args[1], confirm == site.name
log = RunLog(site.name, "remove-row" if live else "remove-row-dry")
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=not live, headless=True,
                allowed_writes=frozenset({f"et_fb_ajax_save@{page_id}", "et_core_portability_import",
                                          "et_fb_process_imported_content", "wpfc_delete_cache",
                                          "wpfc_delete_cache_and_minified"}))
    try:
        s.login()
        s.goto("/wp-admin/")
        page = s.page.evaluate(FETCH, page_id)
        raw = page["content"]["raw"]
        new = remove_row(raw, text)
        (log.backup / f"{page_id}-before.txt").write_text(raw, encoding="utf-8")
        (log.dir / f"{page_id}-after.txt").write_text(new, encoding="utf-8")
        if not live:
            print(f"Dry run: one row removed ({len(raw) - len(new)} chars). Nothing written.")
        else:
            f = log.dir / "import.json"
            f.write_text(portability_json(new, page_id, global_colors(site.name)), encoding="utf-8")
            vb = VisualBuilder(s, page_id)
            vb.open()
            vb.import_layout(f, log.backup)
            (vb.save_draft if page["status"] == "draft" else vb.save_published)()
            if page["status"] == "publish":
                clear_caches(s)
            print(f"Page {page_id}: row removed. Backup in {log.backup}")
    finally:
        s.close()
        log.close()
