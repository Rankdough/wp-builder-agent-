"""`wpagent clone <page_id> --confirm-site <name>`: Duplicate Post 'New Draft'. Only that action is allowed."""
from __future__ import annotations

from playwright.sync_api import sync_playwright

from ..adapters.wp.pages import NEW_DRAFT, clone_as_draft, page_status
from ..browser.session import Session
from ..config import Site
from ..runlog import RunLog


def run(site: Site, page_id: int, confirm_site: str | None, headless: bool = False) -> int:
    if confirm_site != site.name:
        print(f"Production write: pass --confirm-site {site.name}")
        return 2
    log = RunLog(site.name, "clone")
    log.event("start", site=site.name, page_id=page_id)
    with sync_playwright() as pw:
        s = Session(pw, site, log, read_only=False, headless=headless, allowed_writes=frozenset({NEW_DRAFT}))
        try:
            s.login()
            draft_id = clone_as_draft(s, page_id)
            s.screenshot("draft-editor", full_page=False)
            status = page_status(s, draft_id)
            log.write_json("clone.json", {"source": page_id, "draft": draft_id, "status": status})
            log.event("done", **status)
        finally:
            s.close()
            log.close()
    print(f"\nDraft {draft_id}: {status}")
    return 0 if status.get("status") == "draft" else 4
