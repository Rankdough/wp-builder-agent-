"""Template rule check: in every two-column row (rd-level), both columns end at the same height, and a framed graphic
fills at least 60% of its frame (if not, the text beside it is too long: trim it). Read-only.
Usage (add --site <name>): check_levels.py <path or ?page_id=N&preview=true>"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.browser.session import Session
from wpagent.config import script_site
from wpagent.runlog import RunLog

JS = """() => [...document.querySelectorAll('.rd-level')].map(row => {
  const cols = [...row.querySelectorAll(':scope > .et_pb_column')];
  const h = cols.map(c => Math.round(c.getBoundingClientRect().height));
  const img = row.querySelector('.et_pb_image img'); let fill = null;
  if (img) { const c = img.closest('.et_pb_column'); fill = Math.round(img.getBoundingClientRect().height / c.getBoundingClientRect().height * 100); }
  return {section: (row.closest('.et_pb_section').querySelector('h1,h2') || {innerText: '?'}).innerText.slice(0, 40), heights: h, fill}; })"""
site = script_site()
target = sys.argv[1]
log = RunLog(site.name, "check-levels")
bad = 0
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=True, headless=True)
    try:
        s.login()
        s.goto(target if target.startswith("/") else "/" + target)
        s.load_lazy()
        s.page.wait_for_timeout(800)
        for r in s.page.evaluate(JS):
            level = max(r["heights"]) - min(r["heights"]) <= 4
            filled = r["fill"] is None or r["fill"] >= 60
            ok = level and filled
            bad += not ok
            note = "" if ok else (" NOT LEVEL" if not level else f" graphic fills {r['fill']}% of its frame: trim the text")
            print(f"{'OK ' if ok else 'FIX'} {r['section']}: columns {r['heights']}{'' if r['fill'] is None else f', graphic {r[chr(102)+chr(105)+chr(108)+chr(108)]}%'}{note}")
    finally:
        s.close()
        log.close()
sys.exit(1 if bad else 0)
