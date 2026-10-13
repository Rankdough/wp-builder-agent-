"""`wpagent restyle --theme navy-red [--only IDS] [--confirm-site <name>]`: apply a role-aware colour/radius
theme to Divi pages. Dry run by default (reads every layout, reports what would change, writes nothing).
Live mode, one page at a time: Divi backup -> import -> Save (Save Draft for drafts) -> clear cache -> verify."""
from __future__ import annotations

from playwright.sync_api import sync_playwright

from ..adapters.divi.vb import VisualBuilder
from ..adapters.wp.cache import clear_caches
from ..browser.session import Session
from ..config import Site, global_colors
from ..layout.render import portability_json
from ..layout.restyle import THEMES, restyle_layout
from ..runlog import RunLog
from .header_glow import list_pages

FETCH = """async (id) => { const r = await fetch(`/wp-json/wp/v2/pages/${id}?context=edit&_fields=id,status,link,content`,
    {headers: {'X-WP-Nonce': wpApiSettings.nonce}}); return r.ok ? await r.json() : null; }"""
FIRST_BG = """() => { const s = document.querySelector('#main-content .et_pb_section');
    return s ? getComputedStyle(s).backgroundColor : null; }"""


def _rgb(hex_: str) -> str:
    h = hex_.lstrip("#")
    return f"rgb({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)})"


def run(site: Site, theme_name: str, confirm_site: str | None = None, only: list[int] | None = None,
        headless: bool = False) -> int:
    if theme_name not in THEMES:
        print(f"Unknown theme {theme_name!r}; available: {', '.join(THEMES)}")
        return 2
    theme, live = THEMES[theme_name], confirm_site == site.name
    ids = list(only) if only else [p["id"] for p in list_pages(site)]
    colors = global_colors(site.name)
    log = RunLog(site.name, "restyle" if live else "restyle-dry")
    allowed = frozenset({"et_core_portability_import", "et_fb_process_imported_content",
                         "wpfc_delete_cache", "wpfc_delete_cache_and_minified"} | {f"et_fb_ajax_save@{i}" for i in ids})
    results = []
    with sync_playwright() as pw:
        s = Session(pw, site, log, read_only=not live, headless=headless, allowed_writes=allowed)
        try:
            s.login()
            for pid in ids:
                s.goto("/wp-admin/")
                page = s.page.evaluate(FETCH, pid)
                row = {"id": pid, "path": (page or {}).get("link", "").replace(site.url, ""), "status": (page or {}).get("status")}
                raw = ((page or {}).get("content") or {}).get("raw", "")
                if "[et_pb_section" not in raw:
                    row["result"] = "skip: not a Divi page"
                    results.append(row)
                    continue
                new, counts = restyle_layout(raw, theme)
                (log.backup / f"{pid}-before.txt").write_text(raw, encoding="utf-8")
                (log.dir / f"{pid}-after.txt").write_text(new, encoding="utf-8")
                row["changes"] = sum(counts.values())
                row["detail"] = counts
                if not counts:
                    row["result"] = "nothing to change"
                    results.append(row)
                    continue
                if not live:
                    row["result"] = "would change"
                    results.append(row)
                    log.event("page", **{k: v for k, v in row.items() if k != "detail"})
                    continue
                f = log.dir / f"{pid}-import.json"
                f.write_text(portability_json(new, pid, colors), encoding="utf-8")
                vb = VisualBuilder(s, pid)
                vb.open()
                vb.import_layout(f, log.backup)
                (vb.save_draft if row["status"] == "draft" else vb.save_published)()
                if row["status"] == "publish":
                    clear_caches(s)
                    s.goto(row["path"] or "/")
                else:
                    s.goto(f"/?page_id={pid}&preview=true")
                bg = s.page.evaluate(FIRST_BG)
                want = [_rgb(v) for v in theme["background"].values()]
                row["first_section_bg"] = bg
                row["verified"] = bg in want or bg is None
                row["result"] = "changed" if row["verified"] else "changed, check first section"
                results.append(row)
                log.event("page", **{k: v for k, v in row.items() if k != "detail"})
        finally:
            s.close()
    log.write_json("results.json", results)
    log.close()
    for r in results:
        print(f"{r['id']:<5} {r.get('status') or '':<8} {r['result']:<32} {r.get('changes', ''):<4} {r['path']}")
    total = {}
    for r in results:
        for k, v in (r.get("detail") or {}).items():
            total[k] = total.get(k, 0) + v
    print("\nBy setting:")
    for k, v in sorted(total.items(), key=lambda x: -x[1]):
        print(f"  {v:>4}  {k}")
    print(f"\nRun folder: {log.dir}")
    return 0
