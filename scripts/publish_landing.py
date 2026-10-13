"""Finish the WP Builder Agent landing page: upload the header image (Media > Add New), swap it into the hero image
module and the schema, save the draft through the Visual Builder, then set Yoast's SEO title, meta description and
focus keyphrase on the edit screen and click Publish. Dry run unless --confirm-site.
Usage (add --site <name>): publish_landing.py <draft_id> [--confirm-site X]"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.adapters.divi.vb import VisualBuilder
from wpagent.adapters.wp.cache import clear_caches
from wpagent.adapters.wp.media import set_alt_text, upload_image
from wpagent.adapters.wp.pages import set_seo_and_publish
from wpagent.browser.session import MEDIA_UPLOAD, Session
from wpagent.config import ROOT, global_colors, script_site
from wpagent.layout.render import portability_json
from wpagent.runlog import RunLog

IMAGE = ROOT / "runs" / "lp" / "wp-builder-agent-header.png"
ALT = ("WP Builder Agent: an agent that edits WordPress through Divi's builder, global styles, templates and "
       "reusable components")
SEO_TITLE = "WP Builder Agent | Free WordPress & Divi Editing Agent | Rank Dough"
META_DESC = ("A free agent that edits WordPress through Divi's Visual Builder, Theme Options and the Customizer, not "
             "CSS dumps. Backups first, drafts before live.")
KEYPHRASE = "wp builder agent"
OLD_HERO = "wp-builder-agent-divi-visual-builder"
FETCH = """async (id) => (await (await fetch(`/wp-json/wp/v2/pages/${id}?context=edit&_fields=status,content`,
    {headers: {'X-WP-Nonce': wpApiSettings.nonce}})).json())"""


def swap_hero(raw: str, src: str) -> str:
    img = list(re.finditer(r'\[et_pb_image src="([^"]*)" alt="[^"]*" title_text="[^"]*"', raw))
    hero = [m for m in img if OLD_HERO in m.group(1)]
    if len(hero) != 1:
        raise SystemExit(f"Expected one hero image, found {len(hero)}")
    m = hero[0]
    raw = raw[:m.start()] + f'[et_pb_image src="{src}" alt="{ALT}" title_text="{ALT}"' + raw[m.end():]
    raw = re.sub(r'("image": ")[^"]*(")', lambda x: x.group(1) + src + x.group(2), raw, count=1)  # schema image
    if OLD_HERO in raw:
        raise SystemExit("Old hero image still referenced")
    return raw


site = script_site()
args = [a for a in sys.argv[1:] if not a.startswith("--confirm-site")]
confirm = sys.argv[sys.argv.index("--confirm-site") + 1] if "--confirm-site" in sys.argv else None
if confirm:
    args.remove(confirm)
draft_id, live = int(args[0]), confirm == site.name
log = RunLog(site.name, "publish-landing" if live else "publish-landing-dry")
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=not live, headless=True, allowed_writes=frozenset({
        MEDIA_UPLOAD, f"et_fb_ajax_save@{draft_id}", "et_core_portability_import", "et_fb_process_imported_content",
        f"post_edit@{draft_id}", "wpfc_delete_cache", "wpfc_delete_cache_and_minified"}))
    try:
        s.login()
        s.goto("/wp-admin/")
        page = s.page.evaluate(FETCH, draft_id)
        if page["status"] != "draft":
            raise SystemExit(f"Page {draft_id} is {page['status']}, not a draft: refusing")
        raw = page["content"]["raw"]
        (log.backup / f"{draft_id}-before.txt").write_text(raw, encoding="utf-8")
        if not live:
            new = swap_hero(raw, f"{site.url}/wp-content/uploads/YYYY/MM/{IMAGE.name}")
            print(f"Dry run: hero image swap OK ({len(raw)} -> {len(new)} chars). Nothing written.")
        else:
            media = upload_image(s, IMAGE)
            s.allowed_writes = s.allowed_writes | {f"save-attachment@{media['id']}"}
            set_alt_text(s, media["id"], ALT)
            new = swap_hero(raw, media["source_url"])
            (log.dir / f"{draft_id}-after.txt").write_text(new, encoding="utf-8")
            f = log.dir / "import.json"
            f.write_text(portability_json(new, draft_id, global_colors(site.name)), encoding="utf-8")
            vb = VisualBuilder(s, draft_id)
            vb.open()
            vb.import_layout(f, log.backup)
            vb.save_draft()
            set_seo_and_publish(s, draft_id, SEO_TITLE, META_DESC, KEYPHRASE)
            clear_caches(s)
            print(f"Published page {draft_id}. Run folder: {log.dir}")
    finally:
        s.close()
        log.close()
