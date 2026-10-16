"""Remove per-module font overrides so the theme font (Customizer) applies everywhere. Module settings like
header_2_font="Lexend|500|||||||" keep their weight/style and lose only the family ("|500|||||||"); settings left
empty are removed. Code module CSS: font-family Lexend becomes the theme font. Visible text must not change.
Reads each page's live content just before editing it. Dry run unless --confirm-site.
Usage (add --site <name>): fonts_cleanup.py <page_id ...|all> [--font Lexend] [--confirm-site X]"""
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

THEME_FONT = "Archivo"
FETCH = """async (id) => (await (await fetch(`/wp-json/wp/v2/pages/${id}?context=edit&_fields=id,status,link,content`,
    {headers: {'X-WP-Nonce': wpApiSettings.nonce}})).json())"""
LIST = """async () => { let out = [], p = 1; while (true) { const r = await fetch(`/wp-json/wp/v2/pages?per_page=100&page=${p}&status=publish&_fields=id`, {headers: {'X-WP-Nonce': wpApiSettings.nonce}}); if (!r.ok) break; const j = await r.json(); if (!j.length) break; out = out.concat(j.map(x => x.id)); p++; } return out; }"""


def clean(raw: str, font: str) -> tuple[str, int]:
    n = 0

    def attr(m):
        nonlocal n
        n += 1
        rest = m.group(2)
        return "" if not rest.strip("|") else f' {m.group(1)}="|{rest}"'
    raw = re.sub(rf'\s([a-z0-9_]*font(?:_tablet|_phone)?)="{font}\|([^"]*)"', attr, raw)

    def css(m):
        nonlocal n
        n += 1
        return f"font-family:{THEME_FONT},sans-serif"
    raw = re.sub(rf"font-family:\s*(?:{THEME_FONT},)?{font},\s*sans-serif", css, raw)
    return raw, n


site = script_site()
args = [a for a in sys.argv[1:] if not a.startswith("--confirm-site")]
confirm = sys.argv[sys.argv.index("--confirm-site") + 1] if "--confirm-site" in sys.argv else None
if confirm:
    args.remove(confirm)
font = "Lexend"
if "--font" in args:
    i = args.index("--font"); font = args[i + 1]; del args[i:i + 2]
live = confirm == site.name
log = RunLog(site.name, "fonts-cleanup" if live else "fonts-cleanup-dry")
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=not live, headless=True, allowed_writes=frozenset({
        "et_core_portability_import", "et_fb_process_imported_content", "wpfc_delete_cache",
        "wpfc_delete_cache_and_minified"}))
    try:
        s.login()
        s.goto("/wp-admin/")
        ids = s.page.evaluate(LIST) if args == ["all"] else [int(a) for a in args]
        done = 0
        for pid in ids:
            s.goto("/wp-admin/")
            page = s.page.evaluate(FETCH, pid)
            raw = page["content"]["raw"]
            new, n = clean(raw, font)
            path = page["link"].replace(site.url, "")
            if not n:
                continue
            if visible_text(new) != visible_text(raw):
                print(f"{path}: visible text would change, skipped")
                continue
            (log.backup / f"{pid}-before.txt").write_text(raw, encoding="utf-8")
            (log.dir / f"{pid}-after.txt").write_text(new, encoding="utf-8")
            print(f"{path} ({pid}): {n} font override(s)")
            if live:
                s.allowed_writes = s.allowed_writes | {f"et_fb_ajax_save@{pid}"}
                f = log.dir / f"{pid}-import.json"
                f.write_text(portability_json(new, pid, global_colors(site.name)), encoding="utf-8")
                vb = VisualBuilder(s, pid)
                vb.open()
                vb.import_layout(f, log.backup)
                (vb.save_draft if page["status"] == "draft" else vb.save_published)()
                done += 1
        if live and done:
            clear_caches(s)
        print(f"{'Saved' if live else 'Dry run'}: {done if live else len(ids)} page(s).")
    finally:
        s.close()
        log.close()
