"""Turn each column of one row into a card (Divi column settings: background, padding, border, rounded corners)
and make the columns equal height. The row is found by text inside it, which must match exactly one row.
Text and modules are not touched. Dry run unless --confirm-site.
Usage (add --site <name>): box_columns.py <page_id> "<text in the row>" [--confirm-site X]"""
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

CARD = {"background_color": "#14171b", "custom_padding": "32px|28px|32px|28px|false|false",
        "border_radii": "on|16px|16px|16px|16px", "border_width_all": "1px", "border_color_all": "#23272d",
        "border_style_all": "solid"}
FETCH = """async (id) => (await (await fetch(`/wp-json/wp/v2/pages/${id}?context=edit&_fields=status,content`,
    {headers: {'X-WP-Nonce': wpApiSettings.nonce}})).json())"""


def set_attrs(tag: str, values: dict) -> str:
    for k, v in values.items():
        pat = re.compile(rf'(\s{k}=")[^"]*(")')
        tag = pat.sub(rf"\g<1>{v}\g<2>", tag) if pat.search(tag) else tag[:-1] + f' {k}="{v}"]'
    return tag


def box_row(raw: str, text: str) -> str:
    rows = [(m.start(), raw.index("[/et_pb_row]", m.end()) + len("[/et_pb_row]"))
            for m in re.finditer(r"\[et_pb_row[\s\]]", raw)]
    hits = [(a, b) for a, b in rows if text in raw[a:b]]
    if len(hits) != 1:
        raise SystemExit(f"{len(hits)} rows contain {text!r}; need exactly one")
    a, b = hits[0]
    row = raw[a:b]
    row = re.sub(r"^\[et_pb_row[^\]]*\]", lambda m: set_attrs(m.group(0), {"make_equal": "on"}), row)
    row, n = re.subn(r"\[et_pb_column [^\]]*\]", lambda m: set_attrs(m.group(0), CARD), row)
    print(f"{n} columns boxed")
    return raw[:a] + row + raw[b:]


site = script_site()
args = [x for x in sys.argv[1:] if not x.startswith("--confirm-site")]
confirm = sys.argv[sys.argv.index("--confirm-site") + 1] if "--confirm-site" in sys.argv else None
if confirm:
    args.remove(confirm)
page_id, text, live = int(args[0]), args[1], confirm == site.name
log = RunLog(site.name, "box-columns" if live else "box-columns-dry")
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=not live, headless=True, allowed_writes=frozenset({
        f"et_fb_ajax_save@{page_id}", "et_core_portability_import", "et_fb_process_imported_content",
        "wpfc_delete_cache", "wpfc_delete_cache_and_minified"}))
    try:
        s.login()
        s.goto("/wp-admin/")
        page = s.page.evaluate(FETCH, page_id)
        raw = page["content"]["raw"]
        new = box_row(raw, text)
        if visible_text(new) != visible_text(raw):
            raise SystemExit("Visible text would change: stopped")
        (log.backup / f"{page_id}-before.txt").write_text(raw, encoding="utf-8")
        (log.dir / f"{page_id}-after.txt").write_text(new, encoding="utf-8")
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
        else:
            print("Dry run. Nothing written.")
    finally:
        s.close()
        log.close()
