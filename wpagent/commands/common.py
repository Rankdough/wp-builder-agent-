"""Shared steps for plan / apply / rollback."""
from __future__ import annotations

import re
from urllib.parse import urlparse

from ..adapters.divi.customizer import Customizer
from ..browser.session import Session
from ..verify.styles import FrontEnd

# admin-ajax actions a Customizer plan is allowed to trigger. Everything else stays blocked.
CUSTOMIZER_WRITES = frozenset({
    "customize_save",
    "wpfc_delete_cache",
    "wpfc_delete_cache_and_minified",
})


def read_customizer(s: Session) -> dict:
    c = Customizer(s)
    c.open()
    return s.page.evaluate("() => { const o = {}; wp.customize.each((v, id) => { o[id] = v.get(); }); return o; }")


def page_list(s: Session) -> list[str]:
    pages = list(s.site.pages)
    resp = s.context.request.get(f"{s.site.url}/feed/")
    if resp.ok:
        m = re.search(r"<item>.*?<link>([^<]+)</link>", resp.text(), re.S)
        if m:
            path = urlparse(m.group(1).strip()).path
            if path not in pages:
                pages.append(path)
    return pages


def inspect_buttons(front: FrontEnd, pages: list[str]) -> dict:
    out = {}
    for p in pages:
        front.open(p)
        out[p] = front.buttons()
    return out


def button_globals(customizer: dict) -> dict:
    return {k: v for k, v in customizer.items() if k.startswith("et_divi[all_buttons_")}


def print_plan(plan) -> None:
    print("\n================ CHANGE PLAN ================")
    print(f"Task:      {plan.task}")
    print(f"Feasible:  {plan.feasible}")
    if not plan.feasible:
        print(f"Blocked:   {plan.blocked_reason}")
    if plan.rung:
        print(f"Edit rung: {plan.rung}")
    for r in plan.skipped_rungs:
        print(f"  skipped: {r}")
    for c in plan.changes:
        print(f"  CHANGE {c.setting}: {c.old_value!r} -> {c.new_value!r}  ({c.reason})")
    for p in plan.pages_affected:
        print(f"  page: {p}")
    for e in plan.side_effects:
        print(f"  note: {e}")
    for v in plan.verify:
        print(f"  verify {v.page} {v.selector} {v.css_property} == {v.expected}")
    print("=============================================\n")
