"""Replace one image on a page with a local file, like changing it in the Image module: upload through Media > Add New
(with alt text), point the module (and any schema/other reference) at the new file, save the page and clear the cache.
The old file name must appear in exactly one Image module. Dry run unless --confirm-site.
Usage (add --site <name>): swap_image.py <page_id> <old-file-name> <new-file> "<alt text>" [--confirm-site X]"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.adapters.divi.vb import VisualBuilder
from wpagent.adapters.wp.cache import clear_caches
from wpagent.adapters.wp.media import check_file, set_alt_text, upload_image
from wpagent.browser.session import MEDIA_UPLOAD, Session
from wpagent.config import global_colors, script_site
from wpagent.layout.render import portability_json
from wpagent.runlog import RunLog

FETCH = """async (id) => (await (await fetch(`/wp-json/wp/v2/pages/${id}?context=edit&_fields=status,content`,
    {headers: {'X-WP-Nonce': wpApiSettings.nonce}})).json())"""


def swap(raw: str, old_name: str, new_src: str, alt: str) -> str:
    mods = [m for m in re.finditer(r'\[et_pb_image src="([^"]*)"([^\]]*)\]', raw) if old_name in m.group(1)]
    if len(mods) != 1:
        raise SystemExit(f"{len(mods)} Image modules use {old_name!r}; need exactly one")
    m = mods[0]
    attrs = re.sub(r'alt="[^"]*"', f'alt="{alt}"', m.group(2))
    attrs = re.sub(r'title_text="[^"]*"', f'title_text="{alt}"', attrs)
    raw = raw[:m.start()] + f'[et_pb_image src="{new_src}"{attrs}]' + raw[m.end():]
    old_url = m.group(1)
    return raw.replace(old_url, new_src)  # schema image and any other reference to the same file


site = script_site()
args = [a for a in sys.argv[1:] if not a.startswith("--confirm-site")]
confirm = sys.argv[sys.argv.index("--confirm-site") + 1] if "--confirm-site" in sys.argv else None
if confirm:
    args.remove(confirm)
page_id, old_name, new_file, alt = int(args[0]), args[1], Path(args[2]), args[3]
check_file(new_file)
live = confirm == site.name
log = RunLog(site.name, "swap-image" if live else "swap-image-dry")
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
        if not live:
            swap(raw, old_name, f"{site.url}/wp-content/uploads/YYYY/MM/{new_file.name}", alt)
            print(f"Dry run: one Image module uses {old_name}; would upload {new_file.name}. Nothing written.")
        else:
            media = upload_image(s, new_file)
            s.allowed_writes = s.allowed_writes | {f"save-attachment@{media['id']}"}
            set_alt_text(s, media["id"], alt)
            new = swap(raw, old_name, media["source_url"], alt)
            (log.dir / f"{page_id}-after.txt").write_text(new, encoding="utf-8")
            f = log.dir / "import.json"
            f.write_text(portability_json(new, page_id, global_colors(site.name)), encoding="utf-8")
            vb = VisualBuilder(s, page_id)
            vb.open()
            vb.import_layout(f, log.backup)
            (vb.save_draft if page["status"] == "draft" else vb.save_published)()
            if page["status"] == "publish":
                clear_caches(s)
            print(f"Page {page_id}: image swapped to {media['source_url']}. Backup in {log.backup}")
    finally:
        s.close()
        log.close()
