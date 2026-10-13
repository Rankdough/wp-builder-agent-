"""Read-only: count every colour value and border radius used in all Divi page layouts.
Usage (add --site <name>): color_inventory.py <out.json>"""
import collections
import json
import re
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.browser.session import Session
from wpagent.config import script_site
from wpagent.runlog import RunLog

site = script_site()
out = sys.argv[1]
log = RunLog(site.name, "color-inventory")
colors, radii, by_attr, pages = collections.Counter(), collections.Counter(), collections.defaultdict(collections.Counter), {}
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=True, headless=True)
    try:
        s.login()
        s.goto("/wp-admin/")
        items = s.page.evaluate("""async () => { const h = {headers: {'X-WP-Nonce': wpApiSettings.nonce}}; let all = [];
            for (let p = 1; p < 5; p++) { const r = await fetch(`/wp-json/wp/v2/pages?context=edit&per_page=100&page=${p}&_fields=id,link,content`, h);
              if (!r.ok) break; const b = await r.json(); all = all.concat(b); if (b.length < 100) break; } return all; }""")
    finally:
        s.close()
        log.close()
for it in items:
    raw = it["content"]["raw"]
    if "[et_pb_section" not in raw:
        continue
    pages[it["link"]] = 0
    for attr, val in re.findall(r'([a-z0-9_]+)="(#[0-9a-fA-F]{3,8}|rgba?\([^)"]*\))"', raw):
        v = val.lower().replace(" ", "")
        colors[v] += 1
        by_attr[v][attr] += 1
        pages[it["link"]] += 1
    for v in re.findall(r'border_radii(?:_[a-z]+)?="on\|([^"|]*)', raw):
        radii[v] += 1
json.dump({"colors": colors.most_common(), "by_attr": {k: v.most_common(6) for k, v in by_attr.items()},
           "radii": radii.most_common(), "pages": pages}, open(out, "w", encoding="utf-8"), indent=1)
print(f"{len(pages)} Divi pages, {sum(colors.values())} colour settings, {len(colors)} distinct values")
for v, n in colors.most_common(25):
    print(f"  {v:<26} x{n:<5} e.g. {', '.join(a for a, _ in by_attr[v].most_common(3))}")
print("radii:", radii.most_common(10))
