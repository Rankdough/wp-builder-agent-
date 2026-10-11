"""Read-only: export a page's layout through the Visual Builder's Portability window.
Usage (add --site <name>): vb_export.py <page_id> <out.json>"""
import sys
from pathlib import Path

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.adapters.divi.vb import VisualBuilder
from wpagent.browser.session import Session
from wpagent.config import script_site
from wpagent.runlog import RunLog

site = script_site()
page_id, out = int(sys.argv[1]), Path(sys.argv[2])
log = RunLog(site.name, "vb-export")
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=True)
    try:
        s.login()
        vb = VisualBuilder(s, page_id)
        vb.open()
        try:
            vb.export_layout(out)
        except Exception:
            s.screenshot("vb-export-failed", full_page=False)
            raise
        print("exported", out, out.stat().st_size, "bytes")
    finally:
        s.close()
        log.close()
