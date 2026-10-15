"""Website SEO Audits page: swap the Hostelworld image for a (blurred) technical audit dashboard screenshot and add a
new section under it (text left, image right) on why the audit matters and what it includes. Native Divi modules
plus the live rd-steps / rd-pills components. Works on a draft or the live page (Save, cache clear).
Dry run unless --confirm-site. Usage (add --site <name>): audits_page.py <page_id> [--confirm-site X]"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.adapters.divi.vb import VisualBuilder
from wpagent.adapters.wp.cache import clear_caches
from wpagent.adapters.wp.media import set_alt_text, upload_image
from wpagent.browser.session import MEDIA_UPLOAD, Session
from wpagent.config import ROOT, global_colors, script_site
from wpagent.layout.render import portability_json
from wpagent.runlog import RunLog

OLD_IMG = "travel-seo-service-case-study.jpg"
SHOTS = {
    "checklist": (ROOT / "runs" / "lp" / "technical-seo-audit-checklist.png",
                  "Technical SEO audit checklist dashboard: sections for crawling, rendering, indexing and site "
                  "architecture, each marked OK, to fix or to find out"),
    "actions": (ROOT / "runs" / "lp" / "technical-seo-audit-actions.png",
                "Technical SEO audit actions dashboard: 267 checks, 120 actions, open tickets by priority and the "
                "top five critical fixes"),
}
V = '_builder_version="4.27.4" _module_preset="default" global_colors_info="{}" theme_builder_area="post_content"'
STEPS = [
    ("250+ checks across 16 areas",
     "Crawling, rendering, indexing, site architecture, international SEO, rankings, backlinks, e-commerce, forms, "
     "content and UX. Each check is marked OK, to fix or to find out."),
    ("Evidence for every finding",
     "We work from your Search Console data, a full site crawl, Ahrefs and a page-by-page check in the browser. "
     "Each issue comes with example URLs and the traffic it touches."),
    ("Fixes ranked by what they're worth",
     "Every action gets a priority from critical to nice to have, with effort, impact and an owner: your team or "
     "ours. Critical means it blocks crawling, indexing or the pages that earn money."),
    ("Ready for Google and AI search",
     "We check that Google and AI crawlers like GPTBot and ClaudeBot can reach your pages, that key content sits "
     "in the raw HTML, and that your schema works."),
    ("A walkthrough, then a live tracker",
     "You get a short summary of the critical issues and a recorded video walkthrough. The action list then "
     "becomes the tracker we work from as fixes go live."),
]
PILLS = ["250+ point checklist", "Prioritised action list", "Example URLs for every issue",
         "Search Console and crawl data", "AI crawler checks", "Video walkthrough", "Live project tracker"]


def new_section(actions_src):
    steps = "".join(f"<li><h3>{t}</h3><p>{p}</p></li>" for t, p in STEPS)
    pills = "".join(f"<li>{p}</li>" for p in PILLS)
    return (
        f'[et_pb_section fb_built="1" admin_label="Why the audit matters" {V} background_color="#000000"]'
        f'[et_pb_row column_structure="3_5,2_5" {V}]'
        f'[et_pb_column type="3_5" {V}]'
        f'[et_pb_text {V} text_text_color="#b8bec6" text_font_size="18px" text_line_height="1.65em" '
        f'header_2_text_color="#ffffff" custom_margin="||26px||false|false"]'
        "<h2>Why Your Site Needs a Technical SEO Audit</h2>"
        "<p>Content and links do little for pages Google can't crawl, index or trust. Our audit finds what holds "
        "your site back, then puts every fix in the order that brings traffic and sales back first.</p>[/et_pb_text]"
        f'[et_pb_text module_class="rd-steps" {V} text_text_color="#d4d8dd" text_font_size="17px" '
        f'header_3_text_color="#ffffff" header_3_font_size="20px" custom_margin="||26px||false|false"]'
        f"<ol>{steps}</ol>[/et_pb_text]"
        f'[et_pb_button button_url="https://www.rankdough.com/contact/" button_text="Get Your Audit" '
        f'button_alignment="left" {V} custom_button="on" button_text_size="16px" button_text_color="#ffffff" '
        f'button_bg_color="#e02b20" button_border_width="0px" button_border_color="#e02b20" '
        f'button_border_radius="8px" button_on_hover="off"][/et_pb_button]'
        "[/et_pb_column]"
        f'[et_pb_column type="2_5" {V}]'
        f'[et_pb_image src="{actions_src}" alt="{SHOTS["actions"][1]}" title_text="{SHOTS["actions"][1]}" {V} '
        f'border_radii="on|14px|14px|14px|14px" border_width_all="1px" border_color_all="#23272d" '
        f'custom_margin="||24px||false|false"][/et_pb_image]'
        f'[et_pb_blurb title="What you get" module_class="rd-pills" {V} header_level="h3" header_text_color="#ffffff" '
        f'header_font_size="20px" body_text_color="#d4d8dd" body_font_size="17px" background_color="#14171b" '
        f'custom_padding="28px|28px|28px|28px|false|false" border_radii="on|16px|16px|16px|16px" '
        f'border_width_all="1px" border_color_all="#23272d" border_style_all="solid"]'
        f"<p>One dashboard you can share with your developers.</p><ul>{pills}</ul>[/et_pb_blurb]"
        "[/et_pb_column][/et_pb_row][/et_pb_section]")


def transform(raw, checklist_src, actions_src):
    if "Why Your Site Needs a Technical SEO Audit" in raw:
        raise SystemExit("New section already on the page")
    img = re.search(rf'\[et_pb_image src="[^"]*{re.escape(OLD_IMG)}" alt="[^"]*" title_text="[^"]*"', raw)
    if not img:
        raise SystemExit("Hostelworld image module not found")
    raw = (raw[:img.start()] + f'[et_pb_image src="{checklist_src}" alt="{SHOTS["checklist"][1]}" '
           f'title_text="{SHOTS["checklist"][1]}"' + raw[img.end():])
    end = raw.index("[/et_pb_section]", raw.index(checklist_src)) + len("[/et_pb_section]")
    return raw[:end] + new_section(actions_src) + raw[end:]


FETCH = """async (id) => (await (await fetch(`/wp-json/wp/v2/pages/${id}?context=edit&_fields=status,content`,
    {headers: {'X-WP-Nonce': wpApiSettings.nonce}})).json())"""

site = script_site()
args = [a for a in sys.argv[1:] if not a.startswith("--confirm-site")]
confirm = sys.argv[sys.argv.index("--confirm-site") + 1] if "--confirm-site" in sys.argv else None
if confirm:
    args.remove(confirm)
page_id, live = int(args[0]), confirm == site.name
log = RunLog(site.name, "audits-page" if live else "audits-page-dry")
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=not live, headless=True, allowed_writes=frozenset({
        MEDIA_UPLOAD, f"et_fb_ajax_save@{page_id}", "et_core_portability_import", "et_fb_process_imported_content",
        "wpfc_delete_cache", "wpfc_delete_cache_and_minified"}))
    try:
        s.login()
        s.goto("/wp-admin/")
        page = s.page.evaluate(FETCH, page_id)
        raw = page["content"]["raw"]
        (log.backup / f"{page_id}-before.txt").write_text(raw, encoding="utf-8")
        if not live:
            new = transform(raw, f"{site.url}/wp-content/uploads/YYYY/MM/a.png", f"{site.url}/wp-content/uploads/YYYY/MM/b.png")
            print(f"Dry run ({page['status']}): image swap + new section, {len(raw)} -> {len(new)} chars. Nothing written.")
        else:
            media = {k: upload_image(s, p) for k, (p, _) in SHOTS.items()}
            for k, m in media.items():
                s.allowed_writes = s.allowed_writes | {f"save-attachment@{m['id']}"}
                set_alt_text(s, m["id"], SHOTS[k][1])
            new = transform(raw, media["checklist"]["source_url"], media["actions"]["source_url"])
            (log.dir / f"{page_id}-after.txt").write_text(new, encoding="utf-8")
            f = log.dir / "import.json"
            f.write_text(portability_json(new, page_id, global_colors(site.name)), encoding="utf-8")
            vb = VisualBuilder(s, page_id)
            vb.open()
            vb.import_layout(f, log.backup)
            (vb.save_draft if page["status"] == "draft" else vb.save_published)()
            if page["status"] == "publish":
                clear_caches(s)
            print(f"Page {page_id} ({page['status']}) updated. Run folder: {log.dir}")
    finally:
        s.close()
        log.close()
