"""Test CSS on ONE draft page: add (or replace) a zero-padding section at the end of the page holding one Code
module with a <style> block. Drafts only. Usage (add --site <name>): page_css_test.py <draft_id> <file.css> [--remove]"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.adapters.divi.vb import VisualBuilder
from wpagent.browser.session import Session
from wpagent.config import global_colors, script_site
from wpagent.layout.render import portability_json
from wpagent.runlog import RunLog

LABEL = "Dashboard style test CSS"
FETCH = """async (id) => (await (await fetch(`/wp-json/wp/v2/pages/${id}?context=edit&_fields=status,content`,
    {headers: {'X-WP-Nonce': wpApiSettings.nonce}})).json())"""
BLOCK = re.compile(r'\[et_pb_section[^\]]*admin_label="' + re.escape(LABEL) + r'".*?\[/et_pb_section\]', re.S)

site = script_site()
remove = "--remove" in sys.argv
args = [a for a in sys.argv[1:] if a != "--remove"]
draft_id = int(args[0])
css = "" if remove else " ".join(Path(args[1]).read_text(encoding="utf-8").split())
if "[" in css or "]" in css:
    raise SystemExit("CSS must not contain square brackets (they break Divi shortcodes)")
section = ("" if remove else
           f'[et_pb_section fb_built="1" admin_label="{LABEL}" _builder_version="4.27.4" custom_padding="0px||0px|||" '
           f'custom_margin="0px||0px|||"][et_pb_row custom_padding="0px||0px|||" custom_margin="0px||0px|||" '
           f'_builder_version="4.27.4"][et_pb_column type="4_4" _builder_version="4.27.4"][et_pb_code '
           f'_builder_version="4.27.4" custom_margin="0px||0px|||"]<style>{css}</style>[/et_pb_code]'
           f'[/et_pb_column][/et_pb_row][/et_pb_section]')

log = RunLog(site.name, "page-css-test")
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=False, headless=True,
                allowed_writes=frozenset({f"et_fb_ajax_save@{draft_id}", "et_core_portability_import",
                                          "et_fb_process_imported_content"}))
    try:
        s.login()
        s.goto("/wp-admin/")
        page = s.page.evaluate(FETCH, draft_id)
        if page["status"] != "draft":
            raise SystemExit(f"Page {draft_id} is {page['status']}, not a draft: refusing")
        raw = BLOCK.sub("", page["content"]["raw"])
        new = raw + section
        (log.backup / f"{draft_id}-before.txt").write_text(page["content"]["raw"], encoding="utf-8")
        f = log.dir / "import.json"
        f.write_text(portability_json(new, draft_id, global_colors(site.name)), encoding="utf-8")
        vb = VisualBuilder(s, draft_id)
        vb.open()
        vb.import_layout(f, log.backup)
        vb.save_draft()
        print(("Removed" if remove else f"Added {len(css)} chars of CSS") + f" on draft {draft_id}")
    finally:
        s.close()
        log.close()
