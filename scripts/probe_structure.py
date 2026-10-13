"""Read-only: summarise a page's Divi structure (sections, rows, card columns, module types, buttons, icons).
Usage (add --site <name>): probe_structure.py <path>"""
import json
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.browser.session import Session
from wpagent.config import script_site
from wpagent.runlog import RunLog

JS = r"""() => {
  const main = document.querySelector('#main-content');
  const out = [];
  main.querySelectorAll(':scope .et_pb_section').forEach((sec, si) => {
    const rows = [];
    sec.querySelectorAll(':scope > .et_pb_row').forEach(row => {
      const cols = Array.from(row.querySelectorAll(':scope > .et_pb_column')).map(c => {
        const cs = getComputedStyle(c);
        const mods = Array.from(c.querySelectorAll(':scope > .et_pb_module')).map(m =>
          Array.from(m.classList).find(x => /^et_pb_[a-z_]+$/.test(x) && !/module|with_border|bg_layout|text_align|button_module_wrapper/.test(x)) || m.className.slice(0, 30));
        return {card: cs.backgroundColor !== 'rgba(0, 0, 0, 0)', border: cs.borderTopWidth, radius: cs.borderTopLeftRadius, mods};
      });
      rows.push(cols);
    });
    out.push({section: si, cls: Array.from(sec.classList).filter(x => /et_pb_section_\d/.test(x)).join(''),
              heading: (sec.querySelector('h1,h2') || {}).innerText || '', rows});
  });
  return {
    sections: out,
    header: Array.from(document.querySelectorAll('#top-header, #main-header, #main-footer, #et-footer-nav, #footer-bottom')).map(e => e.id),
    buttons: document.querySelectorAll('#main-content .et_pb_button').length,
    blurb_icons: document.querySelectorAll('#main-content .et_pb_blurb .et-pb-icon').length,
    testimonials: document.querySelectorAll('#main-content .et_pb_testimonial').length,
    toggles: document.querySelectorAll('#main-content .et_pb_toggle').length,
    code_modules: document.querySelectorAll('#main-content .et_pb_code').length
  };
}"""

site = script_site()
path = sys.argv[1]
log = RunLog(site.name, "probe-structure")
with sync_playwright() as pw:
    s = Session(pw, site, log, read_only=True, headless=True)
    try:
        s.login()
        s.goto(path, wait="load")
        s.page.wait_for_timeout(2000)
        d = s.page.evaluate(JS)
    finally:
        s.close()
        log.close()
for sec in d["sections"]:
    print(f"S{sec['section']} {sec['cls']:<18} {sec['heading'][:50]!r}")
    for cols in sec["rows"]:
        print("    row:", " | ".join(("CARD " if c["card"] else "") + ",".join(c["mods"]) for c in cols))
print(json.dumps({k: v for k, v in d.items() if k != "sections"}))
