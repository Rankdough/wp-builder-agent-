"""Remove one item from a WordPress menu (Appearance > Menus). Usage (add --site <name>): menu_remove.py <menu_id> "<title>" --confirm-site X"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.adapters.wp.cache import clear_caches
from wpagent.adapters.wp.menus import remove_item
from wpagent.browser.session import Session
from wpagent.config import script_site
from wpagent.runlog import RunLog

site = script_site()
args = [a for a in sys.argv[1:] if not a.startswith("--confirm-site")]
confirm = sys.argv[sys.argv.index("--confirm-site") + 1] if "--confirm-site" in sys.argv else None
if confirm:
    args.remove(confirm)
if confirm != site.name:
    sys.exit(f"Production write: pass --confirm-site {site.name}")
menu_id, title = int(args[0]), args[1]
log = RunLog(site.name, "menu-remove")
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=False, headless=True, allowed_writes=frozenset({
        f"nav_menu_save@{menu_id}", "wpfc_delete_cache", "wpfc_delete_cache_and_minified"}))
    try:
        s.login()
        item = remove_item(s, menu_id, title)
        clear_caches(s)
        print(f"Removed {title!r} (item {item}) from menu {menu_id}. Blocked requests: {s.blocked}")
    finally:
        s.close()
        log.close()
