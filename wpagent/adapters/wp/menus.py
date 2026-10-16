"""Appearance > Menus: remove one item from a menu and Save Menu, like a person would. Needs nav_menu_save@<menu id>."""
from __future__ import annotations

from ...browser.session import Session


def remove_item(s: Session, menu_id: int, title: str) -> int:
    s.goto(f"/wp-admin/nav-menus.php?action=edit&menu={menu_id}")
    items = s.page.locator("#menu-to-edit > li").filter(has=s.page.locator(".menu-item-title", has_text=title))
    match = [i for i in range(items.count()) if items.nth(i).locator(".menu-item-title").inner_text().strip() == title]
    if len(match) != 1:
        raise RuntimeError(f"{len(match)} items titled {title!r} in menu {menu_id}; need exactly one")
    li = items.nth(match[0])
    item_id = int(li.get_attribute("id").split("-")[-1])
    s.log.event("click", target="item edit arrow", item=item_id)
    li.locator(".item-edit").click()
    s.log.event("click", target="Remove", item=item_id, note=f"remove {title!r} from menu {menu_id}")
    li.locator(".item-delete").click()
    s.page.wait_for_timeout(1500)
    s.log.event("click", target="Save Menu", menu=menu_id)
    s.page.locator("[name=save_menu]:visible").first.click()
    s.page.wait_for_load_state("networkidle")
    s.goto(f"/wp-admin/nav-menus.php?action=edit&menu={menu_id}")  # read back from the site, not the edited screen
    titles = s.page.evaluate("() => [...document.querySelectorAll('#menu-to-edit .menu-item-title')].map(e => e.innerText.trim())")
    if title in titles:
        raise RuntimeError(f"{title!r} is still in the menu after saving")
    s.log.event("menu_item_removed", menu=menu_id, item=item_id, title=title)
    return item_id
