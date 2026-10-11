"""Read-only: open the VB on a page, expand the bottom page-settings bar, list its buttons."""
import json, sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from wpagent.adapters.divi.vb import VisualBuilder, SETTINGS_BAR
from wpagent.browser.session import Session
from wpagent.config import script_site
from wpagent.runlog import RunLog

LIST = r"""() => [...document.querySelectorAll('button')].filter(b => { const r = b.getBoundingClientRect(); return r.width > 0 && r.top > 700; })
  .map(b => ({icon: (b.querySelector('[class*="et-fb-icon--"]') || {}).className || '', cls: String(b.className).slice(0, 100),
              tip: b.getAttribute('data-tooltip') || b.getAttribute('aria-label') || b.innerText.trim(), x: Math.round(b.getBoundingClientRect().x)}))"""
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=True)
    try:
site = script_site(); log = RunLog(site.name, "probe-vb-bar")
        s.login(); vb = VisualBuilder(s, int(sys.argv[1])); vb.open()
        s.screenshot("bar-0", full_page=False)
        print("=== before ==="); print(json.dumps(s.page.evaluate(LIST), indent=0))
        s.page.locator(SETTINGS_BAR).first.click(); s.page.wait_for_timeout(1000)
        s.screenshot("bar-1", full_page=False)
        print("=== after expand ==="); print(json.dumps(s.page.evaluate(LIST), indent=0))
    finally:
        s.close(); log.close()
