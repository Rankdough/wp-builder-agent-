"""Build the WP Builder Agent landing page in a draft copied from the GSC Connector page (same design, new copy).
A person would duplicate the page and rewrite it; this does the same: upload the screenshots (Media > Add New),
swap each text, link and image in the copied layout (every swap must match exactly once), import it through the
Visual Builder, Save Draft, then set the title and slug with Quick Edit. Dry run unless --confirm-site.
Usage (add --site <name>): landing_page.py <draft_id> [--confirm-site X]"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.adapters.divi.vb import VisualBuilder
from wpagent.adapters.wp.media import set_alt_text, upload_image
from wpagent.adapters.wp.pages import quick_edit
from wpagent.browser.session import MEDIA_UPLOAD, Session
from wpagent.config import ROOT, global_colors, script_site
from wpagent.layout.render import portability_json
from wpagent.runlog import RunLog

REPO = "https://github.com/Rankdough/wp-builder-agent-"
URL = "https://www.rankdough.com/tools/wp-builder-agent/"
TITLE, SLUG = "WP Builder Agent", "wp-builder-agent"
SHOTS = {
    "hero": (ROOT / "runs" / "lp" / "wp-builder-agent-divi-visual-builder.png",
             "WP Builder Agent rebuild of a hand-coded page, open in the Divi Visual Builder as native modules"),
    "example": (ROOT / "runs" / "lp" / "wp-builder-agent-mobile-logos-before-after.png",
                "Award logos on mobile before and after the WP Builder Agent change: stacked large logos, then a scrolling strip"),
}
FAQ = [
    ("Is the WP Builder Agent free?",
     "Yes, under the MIT licence. You only pay Anthropic for Claude: a plan costs a few cents, and rebuilding a long "
     "page costs about $0.30."),
    ("Can it break my live site?",
     "Every write needs you to confirm the site name. It takes a backup first and only allows the saves the plan "
     "needs. Page rebuilds go into a draft before anything goes live."),
    ("Can Rank Dough see my site?",
     "No. It runs on your computer with your own WordPress login and your own API key."),
    ("Does it work with Elementor or Gutenberg?",
     "Not yet. It's built and tested on Divi 4."),
    ("Does it add CSS?",
     "Only as a last resort, logged with the reason, in one place: Theme Options."),
]
CARD = ('[et_pb_text _builder_version="4.27.4" _module_preset="default" text_text_color="#ffffff" '
        'background_color="#14171b" custom_padding="28px|28px|28px|28px|false|false" border_radii="on|16px|16px|16px|16px" '
        'border_width_all="1px" border_color_all="#23272d" border_style_all="solid" global_colors_info="{}"]')


def p(text):
    return f"<p>{text}</p>"


def swaps(hero_src, example_src):
    """(old, new) pairs applied to the copied GSC layout. Each old string must occur exactly once."""
    s = [
        ("<li>Self-hosted</li>", "<li>Runs on your computer</li>"),
        ("<h1>GSC Connector for Claude</h1><p>A free Google Search Console MCP connector. Ask Claude about your clicks, "
         "rankings and indexing in plain English, in the chat where your work already lives.</p><p>It runs on your own "
         "free Supabase account with your own Google login, so your data stays with you.</p>",
         "<h1>WP Builder Agent</h1>" + p("A free agent that edits your WordPress site from the back end, the way a "
         "careful developer would.") + p("It works through Divi's Visual Builder, Theme Options and the Customizer, "
         "not by injecting CSS into your templates.")),
        ('src="https://www.rankdough.com/wp-content/uploads/2026/10/gsc-connector-claude-search-console-dashboard.png" '
         'alt="Search Console dashboard built in Claude from GSC connector data: clicks, impressions, CTR and position '
         'over 16 months" title_text="Search Console dashboard built in Claude from GSC connector data: clicks, '
         'impressions, CTR and position over 16 months"',
         f'src="{hero_src}" alt="{SHOTS["hero"][1]}" title_text="{SHOTS["hero"][1]}"'),
        ("<p>A Search Console dashboard Claude built in one chat, from connector data.</p>",
         p("A hand-coded page rebuilt by the agent as native Divi modules, editable in the builder.")),
        ("<h2>Why Did We Build the GSC Connector for Claude?</h2><p>Because we needed it for client work. When we built "
         "it in October 2026, Claude's browser app had no Search Console connector.</p>",
         "<h2>Why Did We Build the WP Builder Agent?</h2>" + p("I'd been using Claude to update rankdough.com straight "
         "from the chat. It was quick and the front end looked right. Under the hood it was cowboy work: CSS injected "
         "into templates to force the look, because Claude couldn't operate the page builder.") + p("Most WordPress "
         "sites run on one. We needed changes made the way a person makes them, so the next person can still edit "
         "the page.")),
        ('title="No connector"', 'title="CSS on top of CSS"'),
        ("<p>Getting Search Console data into Claude meant exporting CSVs and uploading them, every time.</p>",
         p("Every quick fix adds another block of code. Six months later nobody knows which rule does what.")),
        ('title="Data in the wrong place"', 'title="Pages nobody can edit"'),
        ("<p>Rankings sat in Google. Client history and decisions sat in Claude. We wanted both in one chat.</p>",
         p("Whole pages pasted into one Code module. They look fine and can't be changed in the builder.")),
        ('title="Paid tools for free data"', 'title="No feel for the builder"'),
        ("<p>Google gives Search Console data away free. The third-party connectors we tried needed paid plans.</p>",
         p("AI tools write code. They don't work through Theme Options, presets and modules the way you do.")),
        ("<h2>What Is the GSC Connector For?</h2><p>Answering questions about your Search Console data without leaving "
         "Claude. You ask; Claude picks one of eight Search Console tools and replies with the numbers.</p>",
         "<h2>What Does the WP Builder Agent Do?</h2>" + p("It logs into your WordPress admin in a visible browser and "
         "makes the change through the same screens you'd use. Global settings first, then templates and presets, "
         "then the module itself. CSS is the last resort, and the agent has to log why it needs it.")),
        ("<p>What were my top queries over the last 28 days?</p>",
         p("Rebuild a hand-coded page as native Divi sections and modules, in a draft")),
        ("<p>Which pages dropped against the previous 28 days?</p>",
         p("Make draft copies of pages, then put a checked draft live")),
        ("<p>Is this URL indexed, and which canonical did Google pick?</p>",
         p("Change fonts, colours and buttons site-wide through the Customizer, with a one-step rollback")),
        ("<p>Which of these 20 URLs has Google skipped, and why?</p>",
         p("Apply one change across the whole site, like a new style on 25 page headers")),
        ("<p>When did Google last read my sitemap?</p>",
         p("Build reusable components to match a design you ask it to copy")),
        ("<p>Which countries and devices bring my clicks?</p>",
         p("Take a backup first, then check the result as a logged-out visitor")),
        ("<p>Performance data lags about three days. That delay comes from Google, not the connector.</p>",
         p("Coming next: blog posts, categories, image uploads and plugin installs, each one done only after you "
           "approve it.")),
        ("<h2>What Can You Do With It Today?</h2><p>Download it, set it up once, then ask Claude about any property your "
         "Google account can see.</p>",
         "<h2>Can You Try It Today?</h2>" + p("Yes. Download it, add your site and a WordPress login, then give it a "
         "task in plain English.")),
        ('<li><h3>Download it</h3><p>Get the code from <a href="https://github.com/Rankdough/gsc-for-claude">GitHub</a>. '
         "It is free under the MIT licence.</p></li><li><h3>Set it up in about 30 minutes</h3><p>Follow the five steps "
         "in the README: Google Cloud, a refresh token, Supabase, deploy, then add it to Claude as a custom connector."
         '</p></li><li><h3>Ask your first question</h3><p>Open a new chat, switch on GSC, and ask: "List my Search '
         'Console sites."</p></li>',
         f'<li><h3>Download it</h3><p>Get the code from <a href="{REPO}">GitHub</a>. It\'s free under the MIT '
         "licence.</p></li><li><h3>Set it up once</h3><p>Python, one command for the browser, and your site details "
         "in a private settings file.</p></li><li><h3>Ask for a change</h3><p>It shows you the plan first, and only "
         "writes to the site when you type the site name to confirm.</p></li>"),
        ("<p>Everything here is free.</p><ul><li>Google account with Search Console access</li><li>Free Supabase "
         "account</li><li>Node 18 or newer</li><li>No Docker</li><li>No server</li><li>No credit card</li></ul>",
         p("Tested on Divi 4.27.4. Divi 5 isn't supported yet.") + "<ul><li>WordPress with Divi 4</li><li>Python "
         "3.12</li><li>An Anthropic API key</li><li>A WordPress user for the agent</li></ul>"),
        ("<h2>GSC Connector for Claude: FAQs</h2>", "<h2>WP Builder Agent: FAQs</h2>"),
        ("<h2>Want us to read your Search Console data?</h2>", "<h2>Want a second pair of eyes on your site?</h2>"),
    ]
    s += [(f'button_url="https://github.com/Rankdough/gsc-for-claude" button_text="Download free on GitHub"',
           f'button_url="{REPO}" button_text="Download free on GitHub"')]
    return s


def faq_block(raw):
    """Replace the four GSC toggles with the agent FAQ, keeping the first toggle's open state and styling."""
    toggles = list(re.finditer(r"\[et_pb_toggle ([^\]]*)\](.*?)\[/et_pb_toggle\]", raw, re.S))
    if len(toggles) != 4:
        raise SystemExit(f"Expected 4 FAQ toggles, found {len(toggles)}")
    first, rest = toggles[0].group(1), toggles[1].group(1)
    out = []
    for i, (q, a) in enumerate(FAQ):
        attrs = re.sub(r'title="[^"]*"', f'title="{q}"', first if i == 0 else rest)
        out.append(f"[et_pb_toggle {attrs}]{p(a)}[/et_pb_toggle]")
    return raw[:toggles[0].start()] + "".join(out) + raw[toggles[-1].end():]


def example_row(raw, example_src):
    """After the six cards: a two-column row with a real example and its before/after screenshot."""
    anchor = "[/et_pb_section]"
    sec_start = raw.index('admin_label="What it is for"')
    end = raw.index(anchor, sec_start)
    row = ('[et_pb_row column_structure="1_2,1_2" _builder_version="4.27.4" _module_preset="default" max_width="1120px" '
           'custom_padding="40px|0px|0px|0px|false|false" global_colors_info="{}"][et_pb_column type="1_2" '
           '_builder_version="4.27.4" _module_preset="default" global_colors_info="{}"][et_pb_text '
           '_builder_version="4.27.4" _module_preset="default" text_text_color="#b8bec6" text_font_size="17px" '
           'text_line_height="1.65em" header_3_text_color="#ffffff" header_3_font_size="22px" global_colors_info="{}"]'
           "<h3>A real change on our own site</h3>" + p("The award logos on our home page were too big on phones. The "
           "agent switched the desktop row off for phones in Divi's own settings and added a phone-only scrolling strip, "
           "the same as our client logos.") + p("No new CSS. The desktop page didn't change.") + "[/et_pb_text]"
           '[/et_pb_column][et_pb_column type="1_2" _builder_version="4.27.4" _module_preset="default" '
           'global_colors_info="{}"]'
           f'[et_pb_image src="{example_src}" alt="{SHOTS["example"][1]}" title_text="{SHOTS["example"][1]}" '
           '_builder_version="4.27.4" _module_preset="default" border_radii="on|16px|16px|16px|16px" '
           'border_width_all="1px" border_color_all="#23272d" global_colors_info="{}"][/et_pb_image]'
           "[/et_pb_column][/et_pb_row]")
    return raw[:end] + row + raw[end:]


def schema(hero_src):
    data = {"@context": "https://schema.org", "@graph": [
        {"@type": "SoftwareApplication", "name": TITLE, "alternateName": ["wp-builder-agent"], "url": URL,
         "downloadUrl": REPO, "image": hero_src, "applicationCategory": "DeveloperApplication",
         "operatingSystem": "Windows", "license": "https://opensource.org/licenses/MIT", "isAccessibleForFree": True,
         "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR"},
         "publisher": {"@type": "Organization", "name": "Rankdough", "url": "https://www.rankdough.com/"},
         "author": {"@type": "Person", "name": "Roman Sadowski"}},
        {"@type": "SoftwareSourceCode", "name": "wp-builder-agent", "codeRepository": REPO,
         "programmingLanguage": "Python", "license": "https://opensource.org/licenses/MIT"},
        {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer",
                                                                                              "text": a}}
                                            for q, a in FAQ]}]}
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + "</script>"


def transform(raw, hero_src, example_src):
    if "GSC Connector for Claude" not in raw:
        raise SystemExit("Draft is not a copy of the GSC Connector page")
    for old, new in swaps(hero_src, example_src):
        n = raw.count(old)
        if n < 1:
            raise SystemExit(f"Not found in layout: {old[:80]!r}")
        raw = raw.replace(old, new)
    raw = faq_block(raw)
    raw = example_row(raw, example_src)
    raw = re.sub(r'<script type="application/ld\+json">.*?</script>', lambda m: schema(hero_src), raw, flags=re.S)
    left = [w for w in ("GSC", "Search Console", "Supabase", "gsc-for-claude") if w in raw]
    if left:
        raise SystemExit(f"Old page text still in layout: {left}")
    text = re.sub(r'<script type="application/ld\+json">.*?</script>', "", raw, flags=re.S)  # JSON-LD lives in a Code module
    if re.search(r"\[(?!/?et_pb_)", text):
        raise SystemExit("Square bracket in text would break the Divi layout")
    return raw


FETCH = """async (id) => (await (await fetch(`/wp-json/wp/v2/pages/${id}?context=edit&_fields=status,content`,
    {headers: {'X-WP-Nonce': wpApiSettings.nonce}})).json())"""

site = script_site()
args = [a for a in sys.argv[1:] if not a.startswith("--confirm-site")]
confirm = sys.argv[sys.argv.index("--confirm-site") + 1] if "--confirm-site" in sys.argv else None
if confirm:
    args.remove(confirm)
draft_id, live = int(args[0]), confirm == site.name
log = RunLog(site.name, "landing-page" if live else "landing-page-dry")
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=not live, headless=True, allowed_writes=frozenset({
        MEDIA_UPLOAD, f"et_fb_ajax_save@{draft_id}", "et_core_portability_import", "et_fb_process_imported_content",
        f"inline-save@{draft_id}"}))
    try:
        s.login()
        s.goto("/wp-admin/")
        page = s.page.evaluate(FETCH, draft_id)
        if page["status"] != "draft":
            raise SystemExit(f"Page {draft_id} is {page['status']}, not a draft: refusing")
        raw = page["content"]["raw"]
        (log.backup / f"{draft_id}-before.txt").write_text(raw, encoding="utf-8")
        if live:
            media = {k: upload_image(s, path) for k, (path, _) in SHOTS.items()}
            src = {k: m["source_url"] for k, m in media.items()}
        else:
            src = {k: f"{site.url}/wp-content/uploads/YYYY/MM/{path.name}" for k, (path, _) in SHOTS.items()}
        new = transform(raw, src["hero"], src["example"])
        (log.dir / f"{draft_id}-after.txt").write_text(new, encoding="utf-8")
        if not live:
            print(f"Dry run: layout {len(raw)} -> {len(new)} chars, 2 screenshots to upload. Nothing written.")
        else:
            for k, m in media.items():
                s.allowed_writes = s.allowed_writes | {f"save-attachment@{m['id']}"}
                set_alt_text(s, m["id"], SHOTS[k][1])
            f = log.dir / "import.json"
            f.write_text(portability_json(new, draft_id, global_colors(site.name)), encoding="utf-8")
            vb = VisualBuilder(s, draft_id)
            vb.open()
            vb.import_layout(f, log.backup)
            vb.save_draft()
            quick_edit(s, draft_id, TITLE, SLUG)
            print(f"Draft {draft_id} built: {site.url}/?page_id={draft_id}&preview=true  Run folder: {log.dir}")
    finally:
        s.close()
        log.close()
