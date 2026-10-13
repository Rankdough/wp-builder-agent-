"""Build a page from a spec JSON into a DRAFT (replacing its content), optionally with a draft-only CSS file.
Usage (add --site <name>): build_demo.py <draft_id> <spec.json> [<file.css>]"""
import sys
from pathlib import Path

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.adapters.divi.vb import VisualBuilder
from wpagent.browser.session import Session
from wpagent.config import global_colors, script_site
from wpagent.layout.render import portability_json, render
from wpagent.layout.spec import PageSpec, validate_spec
from wpagent.runlog import RunLog

FETCH = """async (id) => (await (await fetch(`/wp-json/wp/v2/pages/${id}?context=edit&_fields=status,content`,
    {headers: {'X-WP-Nonce': wpApiSettings.nonce}})).json())"""

site = script_site()
draft_id, spec_path = int(sys.argv[1]), Path(sys.argv[2])
css = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split()) if len(sys.argv) > 3 else ""
if "[" in css or "]" in css:
    raise SystemExit("CSS must not contain square brackets")
spec = PageSpec.model_validate_json(spec_path.read_text(encoding="utf-8"))
validate_spec(spec, f"{site.url}/wp-content/uploads/")
layout = render(spec)
if css:
    layout += ('[et_pb_section fb_built="1" admin_label="Draft-only component CSS" custom_padding="0px||0px|||"]'
               '[et_pb_row custom_padding="0px||0px|||"][et_pb_column type="4_4"][et_pb_code]'
               f"<style>{css}</style>[/et_pb_code][/et_pb_column][/et_pb_row][/et_pb_section]")

log = RunLog(site.name, "build-demo")
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
        (log.backup / f"{draft_id}-before.txt").write_text(page["content"]["raw"], encoding="utf-8")
        f = log.dir / "import.json"
        f.write_text(portability_json(layout, draft_id, global_colors(site.name)), encoding="utf-8")
        vb = VisualBuilder(s, draft_id)
        vb.open()
        vb.import_layout(f, log.backup)
        vb.save_draft()
        print(f"Built draft {draft_id} from {spec_path.name}" + (f" with {len(css)} chars of draft-only CSS" if css else ""))
    finally:
        s.close()
        log.close()
