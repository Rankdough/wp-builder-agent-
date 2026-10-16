"""Save a page's layout to the Divi Library as one named layout (Visual Builder > Save to Library), so new pages can
start from it with Load From Library. The page itself is not changed.
Usage (add --site <name>): save_to_library.py <page_id> "<layout name>" [--replace <old_layout_id>] --confirm-site X
--replace moves the older library layout to Trash (restorable for 30 days) after the new one is saved."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.adapters.divi.vb import LIBRARY_ACTION, VisualBuilder, save_to_library
from wpagent.browser.session import Session
from wpagent.config import script_site
from wpagent.runlog import RunLog

site = script_site()
args = [a for a in sys.argv[1:] if not a.startswith("--confirm-site")]
confirm = sys.argv[sys.argv.index("--confirm-site") + 1] if "--confirm-site" in sys.argv else None
if confirm:
    args.remove(confirm)
replace = None
if "--replace" in args:
    i = args.index("--replace"); replace = int(args[i + 1]); del args[i:i + 2]
page_id, name = int(args[0]), args[1]
if confirm != site.name:
    print(f"Writes to the Divi Library: pass --confirm-site {site.name}")
    sys.exit(2)
log = RunLog(site.name, "save-to-library")
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=False, headless=True, allowed_writes=frozenset({LIBRARY_ACTION} | ({f"trash@{replace}"} if replace else set())))
    try:
        s.login()
        vb = VisualBuilder(s, page_id)
        vb.open()
        save_to_library(vb, name)
        s.goto("/wp-admin/edit.php?post_type=et_pb_layout")
        found = s.page.locator("a.row-title", has_text=name).count()
        print(f"Saved to Divi Library as {name!r}: listed in Divi Library = {bool(found)}")
        if replace and found:
            row = s.page.locator(f"#post-{replace}")
            row.hover()
            s.log.event("click", target=".row-actions .trash a", layout_id=replace, note="Move old library layout to Trash")
            row.locator(".row-actions .trash a").click()
            s.page.wait_for_load_state("networkidle")
            print(f"Old library layout {replace} moved to Trash")
    finally:
        s.close()
        log.close()
