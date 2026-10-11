"""Read-only: find a page in Pages list by slug and print its row actions (nonces redacted)."""
import re
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.browser.session import Session
from wpagent.config import script_site
from wpagent.runlog import RunLog

site = script_site()
slug = sys.argv[1]
log = RunLog(site.name, "probe-row")
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=True)
    try:
        s.login()
        s.goto(f"/wp-admin/edit.php?post_type=page&s={slug.replace('-', '+')}")
        rows = s.page.evaluate(r"""() => [...document.querySelectorAll('#the-list tr')].map(r => ({
            id: r.id, title: (r.querySelector('.row-title')||{}).innerText,
            status: (r.querySelector('.post-state')||{}).innerText || 'published',
            view: (r.querySelector('.row-actions .view a')||{}).href,
            actions: [...r.querySelectorAll('.row-actions span')].map(sp => sp.className + ' :: ' +
                ((sp.querySelector('a')||{}).innerText||'') + ' :: ' + ((sp.querySelector('a')||{}).getAttribute ? sp.querySelector('a').getAttribute('href') : ''))
        }))""")
        for r in rows:
            print(r["id"], "|", r["title"], "|", r["status"], "|", r["view"])
            for a in r["actions"]:
                print("    ", re.sub(r"_wpnonce=[0-9a-f]+", "_wpnonce=…", a))
    finally:
        s.close()
        log.close()
