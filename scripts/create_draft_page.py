"""Create a new draft page from a local file, unchanged, like a person pasting it into Pages > Add New (Text tab),
then set its slug with Quick Edit. Never publishes. Checks the saved content matches the file.
Dry run unless --confirm-site. Usage (add --site <name>): create_draft_page.py <file> "<title>" <slug> [--confirm-site X]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.adapters.wp.pages import create_draft_page, quick_edit
from wpagent.browser.session import Session
from wpagent.config import script_site
from wpagent.runlog import RunLog

FETCH = """async (id) => (await (await fetch(`/wp-json/wp/v2/pages/${id}?context=edit&_fields=status,slug,title,content`,
    {headers: {'X-WP-Nonce': wpApiSettings.nonce}})).json())"""


def norm(t: str) -> str:
    return t.replace("\r\n", "\n").strip()


site = script_site()
args = [a for a in sys.argv[1:] if not a.startswith("--confirm-site")]
confirm = sys.argv[sys.argv.index("--confirm-site") + 1] if "--confirm-site" in sys.argv else None
if confirm:
    args.remove(confirm)
src, title, slug = Path(args[0]), args[1], args[2]
content = src.read_text(encoding="utf-8")
live = confirm == site.name
if not live:
    print(f"Dry run: would create draft {title!r} (slug {slug}) from {src.name}, {len(content)} chars. Nothing written.")
    sys.exit(0)
log = RunLog(site.name, "create-draft")
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=False, headless=True, allowed_writes=frozenset())
    try:
        s.login()
        page_id = create_draft_page(s, title, content)
        s.allowed_writes = s.allowed_writes | {f"inline-save@{page_id}"}
        quick_edit(s, page_id, title, slug)
        s.goto("/wp-admin/")
        saved = s.page.evaluate(FETCH, page_id)
        same = norm(saved["content"]["raw"]) == norm(content)
        log.event("checked", page_id=page_id, status=saved["status"], slug=saved["slug"], content_unchanged=same)
        print(f"PAGE_ID={page_id} status={saved['status']} slug={saved['slug']} title={saved['title']['raw']!r} "
              f"content_unchanged={same} blocked={s.blocked}")
    finally:
        s.close()
        log.close()
