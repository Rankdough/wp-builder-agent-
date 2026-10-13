"""Rebuild the rankdough.com home page copy (a DRAFT) in the dashboard components:
S2 'How it works' -> rd-panel rd-actions; S8 'Verified Client Organic Growth' -> rd-kpi cards + chart images;
every other section -> navy-red restyle; draft-only CSS = component kit + page-scoped extras.
All visible wording is copied verbatim from the source layout. Usage (add --site <name>): home_dashboard_draft.py <draft_id>"""
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.adapters.divi.vb import VisualBuilder
from wpagent.browser.session import Session
from wpagent.config import ROOT, global_colors, script_site
from wpagent.layout.render import portability_json, render
from wpagent.layout.restyle import NAVY_RED, PAGE, restyle_layout
from wpagent.layout.spec import PageSpec, validate_spec
from wpagent.runlog import RunLog

FETCH = """async (id) => (await (await fetch(`/wp-json/wp/v2/pages/${id}?context=edit&_fields=status,content`,
    {headers: {'X-WP-Nonce': wpApiSettings.nonce}})).json())"""
TAG = re.compile(r"\[(et_pb_[a-z_]+)([^\]]*)\]")


def attrs(s):
    return dict(re.findall(r'([a-z0-9_]+)="([^"]*)"', s))


def bodies(sec, tag):
    out = []
    for m in re.finditer(rf"\[{tag}([^\]]*)\]", sec):
        end = sec.find(f"[/{tag}]", m.end())
        out.append((attrs(m.group(1)), sec[m.end():end]))
    return out


def plain(h):
    return html.unescape(re.sub(r"<[^>]+>", "", h)).strip()


def how_it_works(sec):
    texts = [b for _, b in bodies(sec, "et_pb_text")]
    buttons = [a for a, _ in bodies(sec, "et_pb_button")]
    intro = texts[0]
    h2, sub = plain(re.search(r"<h2>(.*?)</h2>", intro, re.S).group(1)), plain(re.search(r"<p>(.*?)</p>", intro, re.S).group(1))
    items = []
    for t, b in zip(texts[1:], buttons):
        step = plain(re.search(r"<strong>(.*?)</strong>", t).group(1))
        title = plain(re.search(r"<h3>(.*?)</h3>", t, re.S).group(1))
        body = plain(re.findall(r"<p>(.*?)</p>", t, re.S)[-1])
        e = html.escape
        items.append(f'<li><h4>{e(title)}</h4><p>{e(body)}</p><em>{e(step)}</em>'
                     f'<a href="{e(b["button_url"])}">{e(b["button_text"])} &rarr;</a></li>')
    return {"admin_label": "How it works (dashboard)", "background_color": PAGE, "padding_top": 70, "padding_bottom": 40, "rows": [
        {"structure": "4_4", "max_width": 1180, "padding": [0, 0, 10, 0], "columns": [{"modules": [
            {"type": "text", "html": f"<h2>{html.escape(h2)}</h2><p>{html.escape(sub)}</p>", "heading_color": "#ffffff", "text_color": "#94a3b8"}]}]},
        {"structure": "4_4", "max_width": 1180, "columns": [{"modules": [
            {"type": "text", "css_class": "rd-panel rd-actions", "html": "<ol>" + "".join(items) + "</ol>"}]}]}]}


def results(sec):
    heading = attrs(re.search(r"\[et_pb_heading([^\]]*)\]", sec).group(1)).get("title", "")
    colours = ["green", "blue", "amber", "purple"]
    cards = []
    for i, (a, _) in enumerate(bodies(sec, "et_pb_blurb")):
        title = html.unescape(a["title"])
        brand, rest = title.split(":", 1)
        number = "+" + re.findall(r"([\d,]+)%", title)[-1] + "%"
        e = html.escape
        label = f'<a href="{e(a["url"])}">{e(brand)}</a>' if a.get("url") else e(brand)
        cards.append({"modules": [
            {"type": "text", "css_class": f"rd-kpi rd-kpi--{colours[i % 4]} rd-ico-chart", "margin_bottom": 12,
             "html": f"<h4>{label}</h4><p><strong>{e(number)}</strong></p><p>{e(rest.strip())}</p>"},
            {"type": "image", "src": a["image"], "alt": title, "border_radius": 12, "border_width": 1, "border_color": "#1e293b"}]})
    rows = [{"structure": "4_4", "max_width": 1180, "padding": [0, 0, 10, 0], "columns": [{"modules": [
        {"type": "text", "html": f"<h2>{html.escape(heading)}</h2>", "heading_color": "#ffffff"}]}]}]
    for i in range(0, len(cards), 2):
        pair = cards[i:i + 2] + ([{"modules": []}] if len(cards[i:i + 2]) == 1 else [])
        rows.append({"structure": "1_2,1_2", "max_width": 1180, "gutter": 2, "equal_heights": True,
                     "padding": [12, 0, 12, 0], "columns": pair})
    return {"admin_label": "Verified client organic growth (dashboard)", "background_color": PAGE,
            "padding_top": 70, "padding_bottom": 70, "rows": rows}


site = script_site()
draft_id = int(sys.argv[1])
log = RunLog(site.name, "home-dashboard")
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
        raw = page["content"]["raw"]
        (log.backup / f"{draft_id}-before.txt").write_text(raw, encoding="utf-8")
        starts = [m.start() for m in re.finditer(r"\[et_pb_section[\s\]]", raw)]
        secs = [raw[a:b] for a, b in zip(starts, starts[1:] + [len(raw)])]
        new_specs = {2: how_it_works(secs[2]), 8: results(secs[8])}
        for i, sec_spec in new_specs.items():
            spec = PageSpec.model_validate({"sections": [sec_spec]})
            validate_spec(spec, f"{site.url}/wp-content/uploads/")
            secs[i] = render(spec)
        restyled, counts = restyle_layout(raw[:starts[0]] + "".join(secs), NAVY_RED)
        extras = (ROOT / "runs" / "css" / "dashboard-test-3887.css").read_text(encoding="utf-8")
        extras = "\n".join(l for l in extras.splitlines() if "et_pb_section_2" not in l and "et_pb_section_8" not in l)
        extras = extras.replace("page-id-3887", f"page-id-{draft_id}")
        kit = (ROOT / "assets" / "dashboard-components.css").read_text(encoding="utf-8")
        css = " ".join((kit + "\n" + extras).split())
        css = re.sub(r"/\*.*?\*/", "", css)
        if "[" in css or "]" in css:
            raise SystemExit("CSS contains square brackets")
        layout = restyled + ('[et_pb_section fb_built="1" admin_label="Draft-only dashboard CSS" custom_padding="0px||0px|||"]'
                             '[et_pb_row custom_padding="0px||0px|||"][et_pb_column type="4_4"][et_pb_code]'
                             f"<style>{css}</style>[/et_pb_code][/et_pb_column][/et_pb_row][/et_pb_section]")
        f = log.dir / "import.json"
        f.write_text(portability_json(layout, draft_id, global_colors(site.name)), encoding="utf-8")
        (log.dir / "layout.txt").write_text(layout, encoding="utf-8")
        vb = VisualBuilder(s, draft_id)
        vb.open()
        vb.import_layout(f, log.backup)
        vb.save_draft()
        print(f"Draft {draft_id}: rebuilt S2 and S8 with components, restyled {sum(counts.values())} settings, "
              f"{len(css)} chars draft-only CSS")
    finally:
        s.close()
        log.close()
