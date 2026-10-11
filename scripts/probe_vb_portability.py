"""Read-only: open the VB Portability window and list its visible containers, tabs, inputs and buttons."""
import json, sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from wpagent.adapters.divi.vb import VisualBuilder, SETTINGS_BAR
from wpagent.browser.session import Session
from wpagent.config import script_site
from wpagent.runlog import RunLog

DUMP = r"""() => {
  const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(e).visibility !== 'hidden'; };
  const modals = [...document.querySelectorAll('[class*="modal"]')].filter(vis).map(m => String(m.className).slice(0, 140));
  const ctrls = [...document.querySelectorAll('a, button, input, label')].filter(vis).filter(e => {
      const r = e.getBoundingClientRect(); return r.top > 150 && r.top < 750 && r.left > 300 && r.left < 1150; })
    .map(e => ({tag: e.tagName, cls: String(e.className).slice(0, 100), text: (e.innerText || e.value || '').trim().slice(0, 50),
                href: e.getAttribute('href'), type: e.getAttribute('type'), name: e.getAttribute('name'),
                data: Object.keys(e.dataset).join(',')}));
  return {modals, ctrls};
}"""
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=True)
    try:
site = script_site(); log = RunLog(site.name, "probe-vb-port")
        s.login(); vb = VisualBuilder(s, int(sys.argv[1])); vb.open()
        f = s.page.locator("#et-fb-app-frame").element_handle().content_frame()
        for name, root in (("top", s.page), ("frame", f)):
            b = root.locator("button:has(.et-fb-icon--portability)")
            print(name, "portability buttons:", b.count(), [b.nth(i).is_visible() for i in range(b.count())])
        vb.ui_click(s.page.locator("button:has(.et-fb-icon--portability)").first, "portability")
        s.page.wait_for_timeout(2500)
        s.screenshot("port-open", full_page=False)
        M = ".et-fb-tooltip-modal--portability"
        MDUMP = """(sel) => { const m = document.querySelector(sel); return [...m.querySelectorAll('a, button, input, label, select')].map(e => ({tag: e.tagName, cls: String(e.className).slice(0, 90), text: (e.innerText || e.value || '').trim().slice(0, 60), type: e.getAttribute('type'), name: e.getAttribute('name'), checked: e.checked, visible: e.getBoundingClientRect().width > 0})); }"""
        print("=== EXPORT tab ==="); print(json.dumps(s.page.evaluate(MDUMP, M), indent=0))
        vb.ui_click(s.page.locator(M + " a.modules_library").first, "Import tab"); s.page.wait_for_timeout(1500)
        s.screenshot("port-import-tab", full_page=False)
        print("=== IMPORT tab ==="); print(json.dumps(s.page.evaluate(MDUMP, M), indent=0))
    finally:
        s.close(); log.close()
