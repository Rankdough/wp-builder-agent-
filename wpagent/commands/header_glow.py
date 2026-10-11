"""`wpagent header-glow [--confirm-site <name>]`: add the site's native hero glow (section background gradient)
to the first section of every Divi page with a dark header. Without --confirm-site it is a dry run: it reads
every layout, prepares the change and reports, without writing. Live mode works one page at a time:
Divi backup -> import -> Save -> clear cache -> verify, and stops at the first failure."""
from __future__ import annotations

import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

from ..adapters.divi.vb import VisualBuilder
from ..adapters.wp.cache import clear_caches
from ..browser.session import Session
from ..config import Site, USER_AGENT, global_colors, site_profile
from ..layout.render import portability_json
from ..runlog import RunLog

SECTION_OPEN = re.compile(r"\[et_pb_section(?P<attrs>(?:\s+[a-z0-9_]+=\"[^\"]*\")*)\s*\]")
DARK_DEFAULT = {"#000000", "#000", "#0a0a0a", "#0b0d10", "#111111", "#14171b"}


def glow_attrs(glow: dict) -> dict:
    r, g, b = (int(glow["color"][i:i + 2], 16) for i in (1, 3, 5))
    return {"use_background_color_gradient": "on", "background_color_gradient_type": "circular",
            "background_color_gradient_direction_radial": glow["position"],
            "background_color_gradient_stops": f"rgba({r},{g},{b},{glow['opacity']:g}) 0%|rgba(0,0,0,0) {glow['fade_at_percent']}%",
            "background_color_gradient_unit": "%", "background_color_gradient_repeat": "off"}


def add_glow(raw: str, glow: dict, dark: set[str] = DARK_DEFAULT) -> tuple[str, str]:
    """Return (new_raw, status). Only the first section's opening tag changes."""
    m = SECTION_OPEN.search(raw)
    if not m:
        return raw, "skip: no Divi section"
    attrs = dict(re.findall(r'([a-z0-9_]+)="([^"]*)"', m.group("attrs")))
    if attrs.get("use_background_color_gradient") == "on":
        return raw, "skip: already has a gradient"
    if attrs.get("background_image"):
        return raw, "skip: section has a background image"
    if attrs.get("background_color", "").lower() not in dark:
        return raw, f"skip: header background {attrs.get('background_color') or 'not set'} is not dark"
    extra = "".join(f' {k}="{v}"' for k, v in glow_attrs(glow).items())
    new_tag = m.group(0)[:-1].rstrip() + extra + "]"
    new = raw[:m.start()] + new_tag + raw[m.end():]
    # Everything except the first section's opening tag must be byte-identical.
    assert new[:m.start()] == raw[:m.start()] and new[m.start() + len(new_tag):] == raw[m.end():]
    return new, "change"


def list_pages(site: Site, only: list[int] | None = None) -> list[dict]:
    """Published pages from the public REST API (ids and URLs)."""
    pages, n = [], 1
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        ctx = b.new_context(user_agent=USER_AGENT)
        while True:
            r = ctx.request.get(f"{site.url}/wp-json/wp/v2/pages?per_page=100&page={n}&_fields=id,link")
            if not r.ok:
                break
            batch = r.json()
            pages += [{"id": p["id"], "url": p["link"]} for p in batch if not only or p["id"] in only]
            if len(batch) < 100:
                break
            n += 1
        b.close()
    return pages


def run(site: Site, confirm_site: str | None = None, only: list[int] | None = None, headless: bool = False) -> int:
    live = confirm_site == site.name
    profile = site_profile(site.name)
    glow = profile.get("design_tokens", {}).get("hero_glow")
    if not glow:
        print("Set design_tokens.hero_glow in sites/<site>.json first (see sites/example.json)")
        return 2
    dark = {c.lower() for c in profile.get("dark_header_colors", [])} or DARK_DEFAULT
    targets = list_pages(site, only)
    colors = global_colors(site.name)
    log = RunLog(site.name, "header-glow" if live else "header-glow-dry")
    results = []
    with sync_playwright() as pw:
        allowed = frozenset({"et_core_portability_import", "et_fb_process_imported_content",
                             "wpfc_delete_cache", "wpfc_delete_cache_and_minified"}
                            | {f"et_fb_ajax_save@{t['id']}" for t in targets})
        s = Session(pw, site, log, read_only=not live, headless=headless, allowed_writes=allowed)
        front = s.browser.new_context(user_agent=USER_AGENT).new_page()
        try:
            s.login()
            s.goto("/wp-admin/")
            for t in targets:
                raw = s.page.evaluate("""async (id) => (await (await fetch(`/wp-json/wp/v2/pages/${id}?context=edit&_fields=content`,
                    {headers: {'X-WP-Nonce': wpApiSettings.nonce}})).json()).content.raw""", t["id"])
                new, status = add_glow(raw, glow, dark)
                row = {"id": t["id"], "path": t["url"].replace(site.url, ""), "status": status}
                (log.backup / f"{t['id']}-before.txt").write_text(raw, encoding="utf-8")
                if status != "change":
                    results.append(row)
                    log.event("page", **row)
                    continue
                f = log.dir / f"{t['id']}-import.json"
                f.write_text(portability_json(new, t["id"], colors), encoding="utf-8")
                if live:
                    vb = VisualBuilder(s, t["id"])
                    vb.open()
                    vb.import_layout(f, log.backup)
                    vb.save_published()
                    clear_caches(s)
                    front.goto(t["url"] + "?wpagent=glow", wait_until="load")
                    bg = front.evaluate("getComputedStyle(document.querySelector('#main-content .et_pb_section')).backgroundImage")
                    row["verified"] = "radial-gradient" in bg
                    log.event("page", **row)
                    results.append(row)
                    s.goto("/wp-admin/")
                    if not row["verified"]:
                        print(f"Stopped: glow not visible on {row['path']}")
                        break
                else:
                    row["status"] = "would change"
                    results.append(row)
                    log.event("page", **row)
        finally:
            s.close()
    log.write_json("results.json", results)
    log.close()
    for r in results:
        print(f"{r['id']:<5} {r['status']:<55} {r.get('verified', '')!s:<6} {r['path']}")
    print(f"\n{sum('change' in r['status'] for r in results)} to change / changed, run folder: {log.dir}")
    return 0
