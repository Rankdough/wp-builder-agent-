"""Draft 3926 (Content That Gets Cited, navy): colour-code each section with the task-board badge palette.
Adds a modifier class to each section's existing .rdm wrapper and a short rule block to the page's own existing
<style> (scoped to .rdm, nothing site-wide). Visible text must not change. Dry run unless --confirm-site.
Usage (add --site <name>): cgc_accents.py <draft_id> [--confirm-site X]"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.adapters.divi.vb import VisualBuilder
from wpagent.browser.session import Session
from wpagent.config import global_colors, script_site
from wpagent.layout.render import portability_json
from wpagent.layout.restyle import visible_text
from wpagent.runlog import RunLog

# Task-board badge colours: Urgent red, High amber, on-time green, Medium blue, purple due dates.
ACCENTS = {"red": "239,68,68", "amber": "245,158,11", "green": "34,197,94", "blue": "59,130,246",
           "purple": "168,85,247"}
SECTIONS = [("Why Most Content Never Gets Cited", "red"), ("How We Write Content That Gets Cited", "blue"),
            ("What Is Included in Our Content Service", "amber"), ("TrackBarn: 455", "green"),
            ("Frequently Asked Questions", "purple")]
CSS = ("".join(f".rdm--{k}{{--acc:{v}}}" for k, v in ACCENTS.items()) +
       ".rdm .num{color:rgb(var(--acc,59,130,246));background:rgba(var(--acc,59,130,246),.12);"
       "border:1px solid rgba(var(--acc,59,130,246),.45);border-radius:6px;padding:5px 9px}"
       ".rdm .card{border-color:rgba(var(--acc,29,40,58),.28)}"
       ".rdm .card.risk{border-color:rgba(var(--acc,239,68,68),.35);border-left:3px solid rgb(var(--acc,239,68,68))}"
       ".rdm a.link{color:rgb(var(--acc,59,130,246))!important}"
       ".rdm .stat{color:rgb(var(--acc,255,255,255))}"
       ".rdm details[open]{border-color:rgb(var(--acc,59,130,246))}"
       ".rdm summary:after{color:rgb(var(--acc,59,130,246))}")
MARK = "/* section accents */"
FETCH = """async (id) => (await (await fetch(`/wp-json/wp/v2/pages/${id}?context=edit&_fields=status,content`,
    {headers: {'X-WP-Nonce': wpApiSettings.nonce}})).json())"""


def transform(raw: str) -> str:
    if MARK in raw:
        raw = re.sub(re.escape(MARK) + r".*?(?=</style>)", "", raw, flags=re.S)  # re-run: replace the old block
        raw = re.sub(r'class="rdm rdm--[a-z]+"', 'class="rdm"', raw)
    mods = list(re.finditer(r"(\[et_pb_code[^\]]*\])(.*?)(\[/et_pb_code\])", raw, re.S))
    out, last = [], 0
    for m in mods:
        body = m.group(2)
        acc = next((c for h, c in SECTIONS if h in body), None)
        if acc:
            if body.count('class="rdm"') != 1:
                raise SystemExit(f"Expected one .rdm wrapper in the {acc} section")
            body = body.replace('class="rdm"', f'class="rdm rdm--{acc}"')
        out.append(raw[last:m.start()] + m.group(1) + body + m.group(3))
        last = m.end()
    new = "".join(out) + raw[last:]
    if new.count("</style>") != 1:
        raise SystemExit("Expected exactly one <style> block on the page")
    new = new.replace("</style>", MARK + CSS + "</style>")
    found = [c for h, c in SECTIONS if f"rdm--{c}" in new]
    if len(found) != len(SECTIONS):
        raise SystemExit(f"Only found sections: {found}")
    return new


site = script_site()
args = [a for a in sys.argv[1:] if not a.startswith("--confirm-site")]
confirm = sys.argv[sys.argv.index("--confirm-site") + 1] if "--confirm-site" in sys.argv else None
if confirm:
    args.remove(confirm)
draft_id, live = int(args[0]), confirm == site.name
log = RunLog(site.name, "cgc-accents" if live else "cgc-accents-dry")
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=not live, headless=True, allowed_writes=frozenset({
        f"et_fb_ajax_save@{draft_id}", "et_core_portability_import", "et_fb_process_imported_content"}))
    try:
        s.login()
        s.goto("/wp-admin/")
        page = s.page.evaluate(FETCH, draft_id)
        if page["status"] != "draft":
            raise SystemExit(f"Page {draft_id} is {page['status']}, not a draft: refusing")
        raw = page["content"]["raw"]
        new = transform(raw)
        if visible_text(new) != visible_text(raw):
            raise SystemExit("Visible text would change: stopped")
        (log.backup / f"{draft_id}-before.txt").write_text(raw, encoding="utf-8")
        (log.dir / f"{draft_id}-after.txt").write_text(new, encoding="utf-8")
        print(f"5 sections colour-coded, {len(CSS)} chars added to the page's own style block. Visible text unchanged.")
        if live:
            f = log.dir / "import.json"
            f.write_text(portability_json(new, draft_id, global_colors(site.name)), encoding="utf-8")
            vb = VisualBuilder(s, draft_id)
            vb.open()
            vb.import_layout(f, log.backup)
            vb.save_draft()
            print(f"Draft {draft_id} saved. Run folder: {log.dir}")
    finally:
        s.close()
        log.close()
