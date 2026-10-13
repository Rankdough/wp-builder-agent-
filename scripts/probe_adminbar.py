"""Read-only: list admin bar menu items (id, text, href with nonce redacted) on a front-end page.
Usage (add --site <name>): probe_adminbar.py <path>"""
import re
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.browser.session import Session
from wpagent.config import script_site
from wpagent.runlog import RunLog

JS = r"""() => Array.from(document.querySelectorAll('#wpadminbar li')).map(li => {
  const a = li.querySelector(':scope > a, :scope > .ab-item');
  return {id: li.id, text: a ? a.textContent.trim() : '', href: a && a.getAttribute ? (a.getAttribute('href') || '') : ''};
})"""

site = script_site()
path = sys.argv[1]
log = RunLog(site.name, "probe-adminbar")
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=True, headless=True)
    try:
        s.login()
        s.goto(path)
        for item in s.page.evaluate(JS):
            if re.search(r"duplicate|draft|rewrite|clone", item["id"] + item["text"], re.I):
                print(item["id"], "|", item["text"], "|", re.sub(r"_wpnonce=[0-9a-f]+", "_wpnonce=…", item["href"]))
    finally:
        s.close()
        log.close()
