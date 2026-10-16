"""Remove every link to a retired page from one page: delete button modules that point at it and unlink inline text.
Dry run unless --confirm-site. Usage (add --site <name>): remove_checklist_links.py <page_id> <url_fragment> [--confirm-site X]"""
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


def strip_links(raw: str, frag: str) -> tuple[str, list[str]]:
    removed = []
    buttons = [m for m in re.finditer(r"\[et_pb_button\s[^\]]*\]", raw) if frag in m.group(0)]
    for m in reversed(buttons):
        end = m.end()
        close = raw.find("[/et_pb_button]", end)
        if close != -1 and not raw[end:close].strip():
            end = close + len("[/et_pb_button]")
        removed.append(raw[m.start():end])
        raw = raw[:m.start()] + raw[end:]
    lead = re.compile(r"Start with our <a\s[^>]*" + re.escape(frag) + r"[^>]*>.*?</a>, or ask for a ", re.S)
    for m in lead.finditer(raw):
        removed.append(m.group(0))
    raw = lead.sub("Ask for a ", raw)
    anchors = [m for m in re.finditer(r"<a\s[^>]*" + re.escape(frag) + r"[^>]*>(.*?)</a>", raw, re.S)]
    for m in reversed(anchors):
        removed.append(m.group(0))
        raw = raw[:m.start()] + m.group(1) + raw[m.end():]
    return raw, removed


site = script_site()
args = [a for a in sys.argv[1:] if not a.startswith("--confirm-site")]
confirm = sys.argv[sys.argv.index("--confirm-site") + 1] if "--confirm-site" in sys.argv else None
if confirm:
    args.remove(confirm)
page_id, frag, live = int(args[0]), args[1], confirm == site.name
log = RunLog(site.name, "remove-links" if live else "remove-links-dry")
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
        new, removed = strip_links(raw, frag)
        (log.backup / f"{page_id}-before.txt").write_text(raw, encoding="utf-8")
        (log.dir / f"{page_id}-after.txt").write_text(new, encoding="utf-8")
        print(f"{len(removed)} link(s) to remove, {len(raw) - len(new)} chars:")
        for r in removed:
            print("  -", r[:300])
        if live and removed:
            f = log.dir / "import.json"
            f.write_text(portability_json(new, page_id, global_colors(site.name)), encoding="utf-8")
            vb = VisualBuilder(s, page_id)
            vb.open()
            vb.import_layout(f, log.backup)
            (vb.save_draft if page["status"] == "draft" else vb.save_published)()
            if page["status"] == "publish":
                clear_caches(s)
            print(f"Page {page_id}: saved. Backup in {log.backup}")
        elif not live:
            print("Dry run. Nothing written.")
    finally:
        s.close()
        log.close()
