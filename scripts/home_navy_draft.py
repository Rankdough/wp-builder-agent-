"""Rebuild draft 3919 (Home, Oct 2026 navy palette) as native Divi sections and modules, from the wording in
rankdough-home/wordpress-block.html (Rankdough/fetch-and-smile, branch claude/epic-cannon-e22ahh). The theme keeps its
own header and footer; colours are Divi design settings; no CSS. Draft only. Dry run unless --confirm-site.
Usage (add --site <name>): home_navy_draft.py <draft_id> [--confirm-site X]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.adapters.divi.vb import VisualBuilder
from wpagent.adapters.wp.pages import enable_divi_builder
from wpagent.browser.session import Session
from wpagent.config import global_colors, script_site
from wpagent.layout.render import portability_json, render
from wpagent.layout.spec import PageSpec, validate_spec
from wpagent.runlog import RunLog

# The file's palette (hsl tokens converted to hex).
BG, FG, CARD, MUTED, BLUE, BORDER = "#070c18", "#f1f5f9", "#0f1729", "#94a3b8", "#3c83f6", "#1d283a"
NAVY, NAVY_2, AMBER, ROSE = "#0a2542", "#153456", "#f59f0a", "#f43e5c"
W = 1120


def text(html, **kw):
    return {"type": "text", "html": html, "heading_color": FG, **kw}


def card(html, bg=CARD, pad=28, css_class=None):
    extra = {"css_class": css_class} if css_class else {}
    return {"modules": [text(html, **extra, text_color=MUTED, font_size=15, h3_size=20, background_color=bg,
                             border_width=1, border_color=BORDER, border_style="solid", border_radius=12,
                             padding=[pad, pad, pad, pad])]}


def heading(h2, sub, align=None):
    return {"structure": "4_4", "max_width": W, "padding": [0, 0, 20, 0], "columns": [{"modules": [
        text(f"<h2>{h2}</h2><p>{sub}</p>", text_color=MUTED, font_size=17, h2_size=40, align=align)]}]}


BTN = {"type": "button", "border_radius": 8, "font_size": 15}
SPEC = {"sections": [
    {"admin_label": "Hero", "background_color": NAVY, "padding_top": 96, "padding_bottom": 80,
     "glow": {"color": BLUE, "opacity": 0.18, "position": "top right", "fade_at_percent": 60},
     "rows": [{"structure": "4_4", "max_width": W, "columns": [{"modules": [
         text("<ul><li>SEO + AI search</li></ul>", css_class="rd-pills", text_color=MUTED, font_size=13, margin_bottom=16),
         text(f'<h1>Rank in Google. Get <span style="color:{BLUE}">cited</span> by AI.</h1>', h1_size=64, margin_bottom=16),
         text("<p>Rankdough fixes the technical issues, builds the content and shapes the answers that search "
              "engines and AI assistants pick up. Clear scope. Measured results.</p>",
              text_color=MUTED, font_size=18, margin_bottom=24),
         {**BTN, "text": "Get a free site snapshot", "url": "#contact", "text_color": "#ffffff", "bg_color": BLUE,
          "border_width": 0},
         {**BTN, "text": "See services", "url": "#services", "text_color": FG, "border_color": "#475569",
          "border_width": 1}]}]}]},
    {"admin_label": "Stats (placeholders)", "background_color": CARD, "padding_top": 28, "padding_bottom": 28,
     "rows": [{"structure": "1_3,1_3,1_3", "max_width": W, "columns": [
         {"modules": [text("<h3>00</h3><p>Placeholder: years in SEO</p>", heading_color=BLUE, h3_size=28,
                           text_color=MUTED, font_size=13)]},
         {"modules": [text("<h3>00</h3><p>Placeholder: sites audited</p>", heading_color=AMBER, h3_size=28,
                           text_color=MUTED, font_size=13)]},
         {"modules": [text("<h3>00%</h3><p>Placeholder: average organic uplift</p>", heading_color=ROSE,
                           h3_size=28, text_color=MUTED, font_size=13)]}]}]},
    {"admin_label": "What we do", "css_id": "services", "background_color": BG, "padding_top": 88,
     "padding_bottom": 88, "rows": [
         heading("What we do", "Three services. Each one ties to a number you can track."),
         {"structure": "1_3,1_3,1_3", "max_width": W, "gutter": 2, "equal_heights": True, "padding": [20, 0, 0, 0],
          "columns": [
              card("<ul><li>Foundation</li></ul><h3>Technical SEO audit</h3><p>Crawl, index, speed and "
                   "structure checked against real data. You get a ranked fix list, not a 90-page PDF.</p>", css_class="rd-pills"),
              card('<ul><li>Growth</li></ul><h3><a href="/content-that-gets-cited/">Content and SEO '
                   "strategy</a></h3><p>Keyword research, topic maps and briefs built around what your buyers "
                   "search. Every page has a job.</p>", css_class="rd-pills"),
              card('<ul><li>Next</li></ul><h3><a href="/ai-visibility-programme/">AI search (AEO)</a></h3>'
                   "<p>Structured data, entity clarity and answer-ready content so ChatGPT, Gemini and Perplexity "
                   "can cite you.</p>", css_class="rd-pills")]}]},
    {"admin_label": "How it works", "css_id": "process", "background_color": NAVY, "padding_top": 88,
     "padding_bottom": 88, "rows": [
         heading("How it works", "Four steps. No lock-in."),
         {"structure": "1_4,1_4,1_4,1_4", "max_width": W, "gutter": 2, "equal_heights": True,
          "padding": [20, 0, 0, 0], "columns": [
              card("<p><strong>01</strong></p><h3>Snapshot</h3><p>A free look at your site's biggest gaps.</p>",
                   NAVY_2, 24),
              card("<p><strong>02</strong></p><h3>Plan</h3><p>Priorities ranked by impact and effort.</p>",
                   NAVY_2, 24),
              card("<p><strong>03</strong></p><h3>Build</h3><p>Fixes, content and markup shipped.</p>", NAVY_2, 24),
              card("<p><strong>04</strong></p><h3>Measure</h3><p>Rankings, traffic and AI citations tracked.</p>",
                   NAVY_2, 24)]}]},
    {"admin_label": "See where you stand", "css_id": "contact", "background_color": BG, "padding_top": 96,
     "padding_bottom": 96, "glow": {"color": BLUE, "opacity": 0.2, "position": "top", "fade_at_percent": 70},
     "rows": [heading("See where you stand",
                      "Send your URL. We reply with a short snapshot of your top three issues.", align="center"),
              {"structure": "4_4", "max_width": W, "columns": [{"modules": [
                  {**BTN, "text": "info@rankdough.com", "url": "mailto:info@rankdough.com?subject=Free%20site%20snapshot",
                   "align": "center", "text_color": "#ffffff", "bg_color": BLUE, "border_width": 0}]}]}]},
]}

site = script_site()
args = [a for a in sys.argv[1:] if not a.startswith("--confirm-site")]
confirm = sys.argv[sys.argv.index("--confirm-site") + 1] if "--confirm-site" in sys.argv else None
if confirm:
    args.remove(confirm)
draft_id, live = int(args[0]), confirm == site.name
spec = PageSpec.model_validate(SPEC)
validate_spec(spec, f"{site.url}/wp-content/uploads/")
layout = render(spec)
log = RunLog(site.name, "home-navy" if live else "home-navy-dry")
(log.dir / "layout.txt").write_text(layout, encoding="utf-8")
if not live:
    print(f"Dry run: {len(spec.sections)} sections, {len(layout)} chars of Divi layout. Nothing written.")
    log.close()
    sys.exit(0)
FETCH = """async (id) => (await (await fetch(`/wp-json/wp/v2/pages/${id}?context=edit&_fields=status,content`,
    {headers: {'X-WP-Nonce': wpApiSettings.nonce}})).json())"""
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=False, headless=True, allowed_writes=frozenset({
        f"et_fb_ajax_save@{draft_id}", "et_core_portability_import", "et_fb_process_imported_content", f"post_edit@{draft_id}"}))
    try:
        s.login()
        s.goto("/wp-admin/")
        page = s.page.evaluate(FETCH, draft_id)
        if page["status"] != "draft":
            raise SystemExit(f"Page {draft_id} is {page['status']}, not a draft: refusing")
        (log.backup / f"{draft_id}-before.txt").write_text(page["content"]["raw"], encoding="utf-8")
        f = log.dir / "import.json"
        f.write_text(portability_json(layout, draft_id, global_colors(site.name)), encoding="utf-8")
        enable_divi_builder(s, draft_id)
        vb = VisualBuilder(s, draft_id)
        vb.open()
        vb.import_layout(f, log.backup)
        vb.save_draft()
        print(f"Draft {draft_id} rebuilt natively. Run folder: {log.dir}")
    finally:
        s.close()
        log.close()
