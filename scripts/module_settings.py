"""Change the design settings of one Divi module, found by text inside it (like opening it in the Visual Builder and
editing its Design tab). key=value sets a setting; key= removes it so the theme default applies again.
The text must match exactly one module. Visible text is never changed. Dry run unless --confirm-site.
Usage (add --site <name>): module_settings.py <page_id> "<text in the module>" key=value [key=] ... [--confirm-site X]"""
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

FETCH = """async (id) => (await (await fetch(`/wp-json/wp/v2/pages/${id}?context=edit&_fields=status,content`,
    {headers: {'X-WP-Nonce': wpApiSettings.nonce}})).json())"""
KEY = re.compile(r"^[a-z0-9_]+$")


def change(raw: str, text: str, changes: dict) -> str:
    mods = [m for m in re.finditer(r"\[(et_pb_(?!section|row|column)[a-z_]+)( [^\]]*)\](.*?)\[/\1\]", raw, re.S)
            if text in m.group(3)]
    if len(mods) != 1:
        raise SystemExit(f"{len(mods)} modules contain {text!r}; need exactly one")
    m = mods[0]
    attrs = m.group(2)
    for k, v in changes.items():
        if not KEY.match(k) or '"' in v or "]" in v:
            raise SystemExit(f"Bad setting {k}={v}")
        pat = re.compile(rf'\s{k}="[^"]*"')
        if v == "":
            attrs = pat.sub("", attrs)
        elif pat.search(attrs):
            attrs = pat.sub(f' {k}="{v}"', attrs)
        else:
            attrs += f' {k}="{v}"'
    print(f"{m.group(1)}: {changes}")
    return raw[:m.start(2)] + attrs + raw[m.end(2):]


site = script_site()
args = [x for x in sys.argv[1:] if not x.startswith("--confirm-site")]
confirm = sys.argv[sys.argv.index("--confirm-site") + 1] if "--confirm-site" in sys.argv else None
if confirm:
    args.remove(confirm)
page_id, text, live = int(args[0]), args[1], confirm == site.name
changes = dict(a.split("=", 1) for a in args[2:])
log = RunLog(site.name, "module-settings" if live else "module-settings-dry")
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=not live, headless=True, allowed_writes=frozenset({
        f"et_fb_ajax_save@{page_id}", "et_core_portability_import", "et_fb_process_imported_content",
        "wpfc_delete_cache", "wpfc_delete_cache_and_minified"}))
    try:
        s.login()
        s.goto("/wp-admin/")
        page = s.page.evaluate(FETCH, page_id)
        raw = page["content"]["raw"]
        new = change(raw, text, changes)
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
