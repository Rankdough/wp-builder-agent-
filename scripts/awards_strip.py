"""Awards & Recognition on mobile: hide the image row on phones (Divi 'Disable on phone') and add a phone-only row
with the awards in the same scrolling strip as the brand logos (reuses the page's existing rd-marquee styles).
Desktop/tablet unchanged. Dry run unless --confirm-site. Usage (add --site <name>): awards_strip.py <page_id> [--confirm-site X]"""
import re
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.adapters.divi.vb import VisualBuilder
from wpagent.adapters.wp.cache import clear_caches
from wpagent.browser.session import Session
from wpagent.config import global_colors, script_site
from wpagent.layout.render import portability_json
from wpagent.runlog import RunLog

U = "https://www.rankdough.com/wp-content/uploads"
# Phone display size: 38px tall (about 20% above the brand logos); width keeps each image's aspect ratio.
AWARDS = [(f"{U}/2025/02/dma.png", "Digital Media Awards logo", 89, 38),
          (f"{U}/2025/02/esa.png", "European Search Awards logo", 127, 38),
          (f"{U}/2025/02/dra.png", "The Drum Awards logo", 93, 38),
          (f"{U}/2026/08/mastering-inhouse-seo-dark-bg.png", "Mastering In-House SEO book", 110, 38)]
FETCH = """async (id) => (await (await fetch(`/wp-json/wp/v2/pages/${id}?context=edit&_fields=status,content`,
    {headers: {'X-WP-Nonce': wpApiSettings.nonce}})).json())"""


def logo(src, alt, w, h, hidden=False):
    aria = ' aria-hidden="true"' if hidden else ""
    # Inline sizes override the shared phone rule (140px box, image scaled to 72%) for these logos only.
    return (f'<div class="rd-logo" style="width:auto;padding:0 18px"><img{aria} src="{src}" alt="{alt}" width="{w}" '
            f'height="{h}" loading="lazy" style="width:{w}px;height:{h}px;max-width:none;transform:none"></div>')


def transform(raw: str) -> str:
    starts = [m.start() for m in re.finditer(r"\[et_pb_section[\s\]]", raw)]
    secs = [raw[a:b] for a, b in zip(starts, starts[1:] + [len(raw)])]
    i = next(k for k, s in enumerate(secs) if "Awards &amp; Recognition" in s or "Awards & Recognition" in s)
    sec = secs[i]
    track = "".join(logo(*a) for a in AWARDS) + "".join(logo(*a, hidden=True) for a in AWARDS)
    if "rd-awards-strip" in sec:  # already added: resize the logos in place
        new, n = re.subn(r'(<div class="rd-marquee rd-row1 rd-awards-strip"><div class="rd-track">).*?(</div></div>\[/et_pb_code\])',
                         lambda m: m.group(1) + track + m.group(2), sec, flags=re.S)
        if n != 1:
            raise SystemExit("Awards strip found but not in the expected form")
        secs[i] = new
        return raw[:starts[0]] + "".join(secs)
    row_tag = re.search(r'\[et_pb_row column_structure="1_4,1_4,1_4,1_4"[^\]]*\]', sec)
    if not row_tag or "dma.png" not in sec[row_tag.end():]:
        raise SystemExit("Awards image row not found as expected")
    new_tag = row_tag.group(0)[:-1] + ' disabled_on="on|off|off"]'  # phone|tablet|desktop: hide on phone only
    row_end = sec.find("[/et_pb_row]", row_tag.end()) + len("[/et_pb_row]")
    strip = ('[et_pb_row admin_label="Awards strip (phone only)" disabled_on="off|on|on" _builder_version="4.27.4" '
             'custom_padding="10px||10px|||"][et_pb_column type="4_4" _builder_version="4.27.4"]'
             '[et_pb_code admin_label="Awards strip" _builder_version="4.27.4"]'
             f'<div class="rd-marquee rd-row1 rd-awards-strip"><div class="rd-track">{track}</div></div>'
             '[/et_pb_code][/et_pb_column][/et_pb_row]')
    sec = sec[:row_tag.start()] + new_tag + sec[row_tag.end():row_end] + strip + sec[row_end:]
    secs[i] = sec
    return raw[:starts[0]] + "".join(secs)


site = script_site()
args = [a for a in sys.argv[1:] if not a.startswith("--confirm-site")]
confirm = sys.argv[sys.argv.index("--confirm-site") + 1] if "--confirm-site" in sys.argv else None
if confirm:
    args.remove(confirm)
page_id, live = int(args[0]), confirm == site.name
log = RunLog(site.name, "awards-strip" if live else "awards-strip-dry")
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=not live, headless=True,
                allowed_writes=frozenset({f"et_fb_ajax_save@{page_id}", "et_core_portability_import",
                                          "et_fb_process_imported_content", "wpfc_delete_cache",
                                          "wpfc_delete_cache_and_minified"}))
    try:
        s.login()
        s.goto("/wp-admin/")
        page = s.page.evaluate(FETCH, page_id)
        raw = page["content"]["raw"]
        new = transform(raw)
        (log.backup / f"{page_id}-before.txt").write_text(raw, encoding="utf-8")
        (log.dir / f"{page_id}-after.txt").write_text(new, encoding="utf-8")
        added = len(new) - len(raw)
        if not live:
            print(f"Dry run: layout +{added} chars (phone-only strip row, image row hidden on phone). Nothing written.")
        else:
            f = log.dir / "import.json"
            f.write_text(portability_json(new, page_id, global_colors(site.name)), encoding="utf-8")
            vb = VisualBuilder(s, page_id)
            vb.open()
            vb.import_layout(f, log.backup)
            (vb.save_draft if page["status"] == "draft" else vb.save_published)()
            if page["status"] == "publish":
                clear_caches(s)
            print(f"Saved page {page_id}: awards strip added for phones. Backup in {log.backup}")
    finally:
        s.close()
        log.close()
