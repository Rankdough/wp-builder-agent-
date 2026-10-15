"""Redesign draft 3926 (Content That Gets Cited) to the GPT layout Roman picked, in the page's own colours
(navy, blue, red, green). Keeps the Divi sections and rewrites the HTML/CSS inside the page's existing Code modules.
Every piece of the page's text is kept word for word (checked before saving). The header form becomes a card
built from the page's own FAQ answer; the same form stays at the bottom of the page.
Dry run unless --confirm-site. Usage (add --site <name>): cgc_redesign.py <draft_id> [--confirm-site X]"""
import html as H
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.adapters.divi.vb import VisualBuilder
from wpagent.browser.session import Session
from wpagent.config import global_colors, script_site
from wpagent.layout.render import portability_json
from wpagent.runlog import RunLog

CSS = """
.rdm{max-width:1120px;margin:0 auto;font-family:Lexend,sans-serif;color:#cbd5e1;--acc:59,130,246}
.rdm--red{--acc:239,68,68}.rdm--green{--acc:34,197,94}.rdm--blue{--acc:59,130,246}
.rdm h2{color:#fff!important;font-size:38px;line-height:1.15;letter-spacing:-.02em;margin:0;padding:0;font-weight:600}
.rdm h3{color:#fff!important;font-size:17px;line-height:1.35;margin:0 0 8px;padding:0;font-weight:600}
.rdm p{margin:0;padding:0}
.rdm .lead{color:#94a3b8;font-size:16px;line-height:1.7}
.rdm a.link{color:rgb(var(--acc))!important;text-decoration:underline;text-underline-offset:3px}
.rdm .mark{display:block;width:28px;height:2px;background:rgb(var(--acc));margin:0 0 18px}
.rdm .head{display:grid;grid-template-columns:1fr 1fr;gap:40px;align-items:end;margin:0 0 44px}
.rdm .head h2{max-width:13ch}
.rdm .cells{display:grid;grid-template-columns:repeat(3,1fr);border:1px solid #1d283a;border-radius:14px;overflow:hidden;counter-reset:rdc}
.rdm .cell{padding:28px;border-right:1px solid #1d283a;border-bottom:1px solid #1d283a;background:rgba(15,23,41,.55);counter-increment:rdc}
.rdm .cell:nth-child(3n){border-right:0}.rdm .cell:nth-last-child(-n+3){border-bottom:0}
.rdm .cell::before{content:counter(rdc,decimal-leading-zero);display:block;color:rgb(var(--acc));font:600 12px/1 "IBM Plex Mono",monospace;letter-spacing:.12em;margin:0 0 16px}
.rdm .cell p,.rdm .card p,.rdm .rule p{color:#94a3b8;font-size:14.5px;line-height:1.65}
.rdm .split{display:grid;grid-template-columns:5fr 7fr;gap:56px;align-items:start}
.rdm .split .lead{margin-top:18px}
.rdm .rules{list-style:none;margin:0;padding:0!important;counter-reset:rdr;border-top:1px solid rgba(148,163,184,.18)}
.rdm .rule{display:grid;grid-template-columns:44px 1fr;gap:16px;padding:22px 0;border-bottom:1px solid rgba(148,163,184,.18);counter-increment:rdr}
.rdm .rule::before{content:counter(rdr);width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;color:rgb(var(--acc));background:rgba(var(--acc),.12);border:1px solid rgba(var(--acc),.45)}
.rdm .num{display:inline-block;color:rgb(var(--acc));font:600 11px/1 "IBM Plex Mono",monospace;letter-spacing:.12em;text-transform:uppercase;margin:0 0 10px}
.rdm .cards{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.rdm .card{background:#0f1729;border:1px solid rgba(var(--acc),.22);border-radius:14px;padding:26px;transition:border-color .2s}
.rdm .card:hover{border-color:rgba(var(--acc),.6)}
.rdm .card .num::after{content:" \\2197"}
.rdm .proof{display:grid;grid-template-columns:auto 1fr 1.2fr;gap:44px;align-items:center}
.rdm .stat{color:rgb(var(--acc));font-size:84px;font-weight:700;line-height:.9;letter-spacing:-.04em;margin:6px 0 0}
.rdm .proof h2{font-size:26px}
.rdm details{border-bottom:1px solid rgba(148,163,184,.18);margin:0}
.rdm details:first-of-type{border-top:1px solid rgba(148,163,184,.18)}
.rdm summary{list-style:none;cursor:pointer;display:flex;justify-content:space-between;align-items:center;gap:16px;padding:20px 0}
.rdm summary::-webkit-details-marker{display:none}
.rdm summary h3{margin:0;font-size:16px}
.rdm summary:after{content:"+";flex:none;color:rgb(var(--acc));font-size:22px;line-height:1;transition:transform .2s}
.rdm details[open] summary:after{transform:rotate(45deg)}
.rdm details p{color:#94a3b8;font-size:15px;line-height:1.7;padding:0 0 22px}
.rdm .hcard{position:relative;margin:30px 0 0;padding:22px 24px;border-radius:16px;background:linear-gradient(160deg,#111c33,#0b1324);border:1px solid #1d283a;box-shadow:0 30px 70px rgba(0,0,0,.5),0 0 0 1px rgba(59,130,246,.06),0 0 80px rgba(59,130,246,.12);transform:rotate(-2deg)}
.rdm .hcard-top{display:flex;justify-content:space-between;align-items:center;color:#64748b;font:600 10px/1 "IBM Plex Mono",monospace;letter-spacing:.14em;text-transform:uppercase;padding:0 0 16px;border-bottom:1px solid #1d283a;margin:0 0 18px}
.rdm .dots{display:flex;gap:6px}.rdm .dots i{width:7px;height:7px;border-radius:50%;background:#1d283a}.rdm .dots i:first-child{background:rgb(var(--acc))}
.rdm .hcard-q{color:#64748b;font-size:12px;margin:0 0 8px}
.rdm .hcard-a{color:#fff;font-size:20px;line-height:1.35;font-weight:600;margin:0 0 12px}
.rdm .hcard-b{color:#94a3b8;font-size:13.5px;line-height:1.6}
.rdm .hcard-foot{display:flex;justify-content:space-between;gap:12px;margin:22px 0 0;padding:14px 0 0;border-top:1px solid #1d283a;font-size:12px;color:#64748b}
.rdm .hcard-foot b{color:rgb(var(--acc));font-weight:600}
@media (max-width:980px){.rdm .head,.rdm .split,.rdm .proof{grid-template-columns:1fr;gap:20px}.rdm .cells,.rdm .cards{grid-template-columns:1fr 1fr}
.rdm .cell:nth-child(3n){border-right:1px solid #1d283a}.rdm .cell:nth-child(2n){border-right:0}.rdm .cell:nth-last-child(-n+3){border-bottom:1px solid #1d283a}.rdm .cell:nth-last-child(-n+2){border-bottom:0}}
@media (max-width:767px){.rdm .cells,.rdm .cards{grid-template-columns:1fr}.rdm .cell{border-right:0!important;border-bottom:1px solid #1d283a!important}.rdm .cell:last-child{border-bottom:0!important}
.rdm h2{font-size:28px}.rdm .stat{font-size:64px}.rdm .hcard{transform:none}}
"""


def blocks(raw):
    return list(re.finditer(r"(\[et_pb_code[^\]]*\])(.*?)(\[/et_pb_code\])", raw, re.S))


def parts(body):
    """Pull the page's own text out of a Code module: h2, lead, and (h3, p, label) items."""
    h2 = re.search(r"<h2>(.*?)</h2>", body, re.S)
    lead = re.search(r'<p class="lead"[^>]*>(.*?)</p>', body, re.S)
    return (h2.group(1) if h2 else None), (lead.group(1) if lead else None)


def items(body, cls):
    return re.findall(rf'<div class="{cls}">(?:<span class="num">(.*?)</span>)?<h3>(.*?)</h3><p>(.*?)</p></div>', body, re.S)


def problem(body):
    h2, lead = parts(body)
    cells = "".join(f'<div class="cell"><h3>{t}</h3><p>{p}</p></div>' for _, t, p in items(body, "card risk"))
    return (f'<div class="rdm rdm--red"><div class="head"><div><span class="mark"></span><h2>{h2}</h2></div>'
            f'<p class="lead">{lead}</p></div><div class="cells">{cells}</div></div>')


def rules(body):
    h2, lead = parts(body)
    li = "".join(f'<li class="rule"><div><span class="num">{n}</span><h3>{t}</h3><p>{p}</p></div></li>'
                 for n, t, p in items(body, "card"))
    return (f'<div class="rdm rdm--blue"><div class="split"><div><span class="mark"></span><h2>{h2}</h2>'
            f'<p class="lead">{lead}</p></div><ol class="rules">{li}</ol></div></div>')


def included(body):
    h2, lead = parts(body)
    cards = "".join(f'<div class="card"><span class="num">{n}</span><h3>{t}</h3><p>{p}</p></div>'
                    for n, t, p in items(body, "card"))
    return (f'<div class="rdm rdm--green"><div class="head"><div><span class="mark"></span><h2>{h2}</h2></div>'
            f'<p class="lead">{lead}</p></div><div class="cards">{cards}</div></div>')


def proof(body):
    label = re.search(r'<span class="num">(.*?)</span>', body).group(1)
    stat = re.search(r'<p class="stat">(.*?)</p>', body).group(1)
    h2, lead = parts(body)
    return (f'<div class="rdm rdm--green"><div class="proof"><div><span class="num">{label}</span>'
            f'<p class="stat">{stat}</p></div><h2>{h2}</h2><p class="lead">{lead}</p></div></div>')


def faq(body):
    h2, lead = parts(body)
    details = "".join(re.findall(r"<details.*?</details>", body, re.S))
    jsonld = re.search(r'<script type="application/ld\+json">.*?</script>', body, re.S).group(0)
    return (f'<div class="rdm rdm--blue"><div class="split"><div><span class="mark"></span><h2>{h2}</h2>'
            f'<p class="lead">{lead}</p></div><div>{details}</div></div></div>{jsonld}')


def hero_card(faq_body):
    q, a = re.search(r"<summary><h3>(What is answer-first content\?)</h3></summary><p>(.*?)</p>", faq_body, re.S).groups()
    first, rest = a.split(", before explaining. ", 1)
    return ('<div class="rdm rdm--blue"><div class="hcard"><div class="hcard-top"><span>Answer-first content</span>'
            '<span class="dots"><i></i><i></i><i></i></span></div>'
            f'<p class="hcard-q">{q}</p><p class="hcard-a">{first}, before explaining.</p>'
            f'<p class="hcard-b">{rest}</p>'
            '<div class="hcard-foot"><span>Rule 1: Answer first</span><b>Built for Google and AI</b></div></div></div>')


def words(raw):
    t = re.sub(r"<style.*?</style>|<script.*?</script>", " ", raw, flags=re.S)
    t = re.sub(r"\[/?et_pb_[^\]]*\]|\[form[^\]]*\]", " ", t)
    t = re.sub(r"</?span[^>]*>", "", t)  # colouring one word splits a heading into spans; read it as one line
    return " ".join(H.unescape(re.sub(r"<[^>]+>", " ", t)).split())


def segments(raw):
    """Each text run between tags in the page (headings, paragraphs, labels, link texts)."""
    t = re.sub(r"<style.*?</style>|<script.*?</script>", " ", raw, flags=re.S)
    t = re.sub(r"\[/?et_pb_[^\]]*\]|\[form[^\]]*\]", "|", t)
    return [s for s in (" ".join(H.unescape(x).split()) for x in re.split(r"<[^>]+>|\|", t)) if s]


def transform(raw):
    b = blocks(raw)
    if len(b) != 7 or "[form" not in b[0].group(2) or "[form" not in b[6].group(2):
        raise SystemExit("Page layout is not the expected 7 Code modules")
    bodies = [m.group(2) for m in b]
    new = {0: hero_card(bodies[5]), 1: f"<style>{' '.join(CSS.split())}</style>" + problem(bodies[1]),
           2: rules(bodies[2]), 3: included(bodies[3]), 4: proof(bodies[4]), 5: faq(bodies[5])}
    out, last = [], 0
    for i, m in enumerate(b):
        out.append(raw[last:m.start()] + m.group(1) + new.get(i, m.group(2)) + m.group(3))
        last = m.end()
    raw2 = "".join(out) + raw[last:]
    raw2 = raw2.replace('<span style="color: #ffffff;">Content That Gets Cited: Answer-First Pages Built for Google and AI</span>',
                        '<span style="color: #ffffff;">Content That Gets </span><span style="color: #3c83f6;">Cited</span>'
                        '<span style="color: #ffffff;">: Answer-First Pages Built for Google and AI</span>', 1)
    raw2 = re.sub(r'(admin_label="(?:Problem|Rules|Included|FAQ|Proof)"[^\]]*?custom_padding=")[^"]*(")',
                  r"\g<1>96px||96px|||\g<2>", raw2)
    return raw2


FETCH = """async (id) => (await (await fetch(`/wp-json/wp/v2/pages/${id}?context=edit&_fields=status,content`,
    {headers: {'X-WP-Nonce': wpApiSettings.nonce}})).json())"""

site = script_site()
args = [a for a in sys.argv[1:] if not a.startswith("--confirm-site")]
confirm = sys.argv[sys.argv.index("--confirm-site") + 1] if "--confirm-site" in sys.argv else None
if confirm:
    args.remove(confirm)
draft_id, live = int(args[0]), confirm == site.name
log = RunLog(site.name, "cgc-redesign" if live else "cgc-redesign-dry")
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
        after = words(new)
        missing = [seg for seg in segments(raw) if seg not in after]
        if missing:
            raise SystemExit("Text would be lost: " + " | ".join(missing[:10]))
        if new.count('[form id="824"]') != 1 or new.count("application/ld+json") != 1:
            raise SystemExit("Form or schema count changed unexpectedly")
        (log.backup / f"{draft_id}-before.txt").write_text(raw, encoding="utf-8")
        (log.dir / f"{draft_id}-after.txt").write_text(new, encoding="utf-8")
        print(f"All {len(segments(raw))} text pieces kept. Header form -> card (form kept at the bottom). "
              f"{len(raw)} -> {len(new)} chars.")
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
