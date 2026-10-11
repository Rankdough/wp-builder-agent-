"""Front-end checks as a logged-out visitor: computed styles and element inspection."""
from __future__ import annotations

import re
import time

from playwright.sync_api import Browser

from ..config import USER_AGENT, Site

BUTTON_PROPS = ("background-color", "color", "border-radius", "border-top-color", "border-top-width")


def normalize(value: str) -> str:
    """Turn #rgb, #rrggbb, rgb() and rgba(...,1) into rgb(r, g, b); keep other values trimmed."""
    v = (value or "").strip().lower()
    m = re.fullmatch(r"#([0-9a-f]{3}|[0-9a-f]{6})", v)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return f"rgb({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)})"
    m = re.fullmatch(r"rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)", v)
    if m:
        r, g, b, a = m.groups()
        if a is None or float(a) == 1:
            return f"rgb({r}, {g}, {b})"
        return f"rgba({r}, {g}, {b}, {float(a):g})"
    return v


class FrontEnd:
    """A separate cookie-less context, so checks see what visitors see."""

    def __init__(self, browser: Browser, site: Site):
        self.site = site
        self.context = browser.new_context(user_agent=USER_AGENT, viewport={"width": 1440, "height": 900})
        self.page = self.context.new_page()

    def open(self, path: str, bust_cache: bool = True) -> None:
        url = self.site.url + path
        if bust_cache:
            url += ("&" if "?" in url else "?") + f"wpagent={int(time.time())}"
        self.page.goto(url, wait_until="networkidle", timeout=60_000)

    def computed(self, selector: str, prop: str) -> str | None:
        return self.page.evaluate(
            "([sel, prop]) => { const e = document.querySelector(sel); return e ? getComputedStyle(e).getPropertyValue(prop) : null; }",
            [selector, prop],
        )

    def buttons(self) -> list[dict]:
        return self.page.evaluate(
            """(props) => [...document.querySelectorAll('.et_pb_button')].map(b => {
                const c = getComputedStyle(b), out = {text: b.innerText.trim().slice(0, 40),
                    selector: '.' + [...b.classList].find(x => /^et_pb_button_\\d+$/.test(x))};
                props.forEach(p => out[p] = c.getPropertyValue(p)); return out; })""",
            list(BUTTON_PROPS),
        )

    def close(self) -> None:
        self.context.close()


def run_checks(front: FrontEnd, checks) -> list[dict]:
    results, current = [], None
    for c in checks:
        if c.page != current:
            front.open(c.page)
            current = c.page
        actual = front.computed(c.selector, c.css_property)
        ok = actual is not None and normalize(actual) == normalize(c.expected)
        results.append({"page": c.page, "selector": c.selector, "property": c.css_property,
                        "expected": c.expected, "actual": actual, "pass": ok})
    return results
