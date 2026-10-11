"""Read-only: compare two pages as rendered (logged in, so drafts can be previewed).
Checks visible text, links, images, page height; saves desktop + mobile screenshots of both.
Usage (add --site <name>): compare_pages.py <path_a> <path_b> <out_dir>"""
import difflib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.browser.session import Session
from wpagent.config import script_site
from wpagent.runlog import RunLog

READ = r"""() => {
  const main = document.querySelector('#main-content') || document.body;
  main.querySelectorAll('.et_pb_toggle_content').forEach(e => e.style.display = 'block');
  const lines = main.innerText.split('\n').map(s => s.replace(/\s+/g, ' ').trim()).filter(Boolean);
  return {
    lines,
    links: [...main.querySelectorAll('a[href]')].map(a => (a.innerText.trim() || '[img]') + ' -> ' + a.getAttribute('href')),
    images: [...main.querySelectorAll('img')].map(i => i.getAttribute('src').split('/').pop() + ' alt=' + i.alt),
    height: Math.round(main.getBoundingClientRect().height),
    jsonld: [...document.querySelectorAll('script[type="application/ld+json"]')].map(s => { try { return Object.keys(JSON.parse(s.textContent)).join(','); } catch (e) { return 'INVALID'; } })
  };
}"""

site = script_site()
a_path, b_path, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
log = RunLog(site.name, "compare")
res = {}
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=True)
    try:
        s.login()
        for label, path in (("a", a_path), ("b", b_path)):
            for vp in ("desktop", "mobile"):
                s.set_viewport(vp)
                s.goto(path, wait="load")
                s.page.wait_for_timeout(2500)
                s.load_lazy()
                s.page.screenshot(path=str(out / f"{label}-{vp}.png"), full_page=True)
                res[f"{label}-{vp}"] = s.page.evaluate(READ)
    finally:
        s.close()
        log.close()

report = {}
for vp in ("desktop", "mobile"):
    a, b = res[f"a-{vp}"], res[f"b-{vp}"]
    report[vp] = {
        "text_identical": a["lines"] == b["lines"],
        "text_diff": [l for l in difflib.unified_diff(a["lines"], b["lines"], lineterm="", n=0)][:40],
        "links_only_in_a": sorted(set(a["links"]) - set(b["links"])),
        "links_only_in_b": sorted(set(b["links"]) - set(a["links"])),
        "images_only_in_a": sorted(set(a["images"]) - set(b["images"])),
        "images_only_in_b": sorted(set(b["images"]) - set(a["images"])),
        "height": [a["height"], b["height"]],
        "jsonld": [a["jsonld"], b["jsonld"]],
    }
(out / "compare.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
print(json.dumps(report, indent=1, ensure_ascii=False))
