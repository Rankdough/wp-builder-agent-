"""Clear page caches through their own admin-bar buttons, like a human would after a change."""
from __future__ import annotations

from ...browser.session import Session

WPFC_PARENT = "#wp-admin-bar-wpfc-toolbar-parent"
WPFC_CLEAR = "#wp-admin-bar-wpfc-toolbar-parent-delete-cache-and-minified a"


def clear_caches(s: Session) -> list[str]:
    cleared = []
    s.goto("/wp-admin/")
    if s.page.locator(WPFC_PARENT).count():
        s.page.hover(WPFC_PARENT)
        s.log.event("click", target=WPFC_CLEAR, note="WP Fastest Cache: Clear Cache and Minified CSS/JS")
        s.page.click(WPFC_CLEAR)
        s.page.wait_for_timeout(3_000)
        cleared.append("wp-fastest-cache")
    s.log.event("caches_cleared", caches=cleared)
    return cleared
