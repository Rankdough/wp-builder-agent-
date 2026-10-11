"""Read-only: fetch a page's raw Divi layout (post content) via the logged-in REST API (GET only).
Usage (add --site <name>): read_layout.py <page_id|front> <out.txt>"""
import re
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.browser.session import Session
from wpagent.config import script_site
from wpagent.runlog import RunLog

site = script_site()
target, out = sys.argv[1], sys.argv[2]
log = RunLog(site.name, "read-layout")
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=True)
    try:
        if target == "front":
            s.goto("/")
            target = re.search(r"page-id-(\d+)", s.page.evaluate("document.body.className")).group(1)
        s.login()
        s.goto("/wp-admin/")
        data = s.page.evaluate(
            """async (id) => { const r = await fetch(`/wp-json/wp/v2/pages/${id}?context=edit&_fields=id,title,content`,
                 {headers: {'X-WP-Nonce': wpApiSettings.nonce}}); return {status: r.status, json: await r.json()}; }""",
            target,
        )
    finally:
        s.close()
        log.close()
raw = data["json"]["content"]["raw"]
open(out, "w", encoding="utf-8").write(raw)
print(f"page {target}: HTTP {data['status']}, {len(raw)} chars -> {out}")
