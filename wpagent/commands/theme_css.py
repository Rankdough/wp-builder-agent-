"""`wpagent theme-css <file> --confirm-site <name>`: append a CSS block to Divi Theme Options > Custom CSS
through its editor, Save Changes, then verify. Last-resort rung: logged with the existing value backed up."""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

from ..adapters.wp.cache import clear_caches
from ..browser.session import Session
from ..config import Site
from ..runlog import RunLog

FIELD = 'textarea[name="divi_custom_css"]'
BLOCK_START = "/* wp-builder-agent: reusable components"
BLOCK_END = "/* end wp-builder-agent components */"


def merge_block(before: str, block: str) -> str:
    """Put our block into the existing Custom CSS: replace an earlier version of it, or append. Other CSS is kept."""
    start = before.find(BLOCK_START)
    if start == -1:
        return (before.rstrip() + "\n\n" if before.strip() else "") + block + "\n"
    end = before.find(BLOCK_END, start)
    tail = before[end + len(BLOCK_END):] if end != -1 else ""  # v1 had no end marker and was the last block
    return before[:start] + block + ("\n" + tail.lstrip("\n") if tail.strip() else "\n")


def _read(s: Session) -> str:
    s.goto("/wp-admin/admin.php?page=et_divi_options")
    return s.page.locator(FIELD).input_value()


def run(site: Site, css_file: str, confirm_site: str | None, reason: str = "", headless: bool = False) -> int:
    if not reason:
        print("CSS is a last resort: pass --reason explaining why no native Divi setting can do this")
        return 2
    if confirm_site != site.name:
        print(f"Production write: pass --confirm-site {site.name}")
        return 2
    block = Path(css_file).read_text(encoding="utf-8").strip()
    log = RunLog(site.name, "theme-css")
    allowed = frozenset({"save_epanel", "wpfc_delete_cache", "wpfc_delete_cache_and_minified"})
    with sync_playwright() as pw:
        s = Session(pw, site, log, read_only=False, headless=headless, allowed_writes=allowed)
        try:
            s.login()
            before = _read(s)
            (log.backup / "custom-css-before.css").write_text(before, encoding="utf-8")
            if block in before:
                print("This exact block is already present; nothing to do.")
                return 0
            target = merge_block(before, block)
            log.event("rung", rung="theme_custom_css", reason=reason)
            editor = s.page.locator(f"{FIELD} ~ .CodeMirror, .CodeMirror").first
            editor.scroll_into_view_if_needed()
            editor.click()
            s.page.keyboard.press("Control+A")
            s.page.keyboard.insert_text(target)  # paste the merged CSS over the selection
            s.screenshot("custom-css-typed", full_page=False)
            save = s.page.locator("#epanel-save, button:has-text('Save Changes'), a:has-text('Save Changes')").first
            s.log.event("click", target="Save Changes", note="Theme Options")
            save.click()
            s.page.wait_for_timeout(5_000)
            after = _read(s)
            ok = after.strip() == target.strip()
            log.event("verify", saved_as_intended=ok, replaced_previous=BLOCK_START in before)
            clear_caches(s)
            resp = s.context.request.get(f"{site.url}/?wpagent=css")
            live = ".rd-pills" in resp.text()
            log.event("verify_front", css_in_page=live)
        finally:
            s.close()
            log.close()
    print(f"Saved: {ok}. CSS served on front end: {live}. Backup: {log.backup / 'custom-css-before.css'}")
    return 0 if ok and live else 4
