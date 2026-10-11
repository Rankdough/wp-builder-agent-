"""Read-only: how is a page built? Divi modules vs raw code. Usage: analyse_page.py <url> <screenshot.png>"""
import json
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.config import USER_AGENT

JS = r"""() => {
  const main = document.querySelector('#main-content') || document.body;
  const skip = new Set(['et_pb_module', 'et_pb_bg_layout_light', 'et_pb_bg_layout_dark', 'et_pb_text_align_left',
                        'et_pb_section_parallax', 'et_pb_with_background', 'et_section_regular', 'et_pb_row_empty']);
  const count = {};
  main.querySelectorAll('.et_pb_section, .et_pb_row, .et_pb_module').forEach(m => {
    const t = [...m.classList].find(c => /^et_pb_[a-z_]+$/.test(c) && !skip.has(c));
    if (t) count[t] = (count[t] || 0) + 1;
  });
  const big = sel => [...main.querySelectorAll(sel)].map(c => ({
    visible_chars: c.innerText.length, html_chars: c.innerHTML.length,
    style_tags: c.querySelectorAll('style').length, script_tags: c.querySelectorAll('script').length,
    elements_inside: c.querySelectorAll('*').length,
    first_text: c.innerText.trim().slice(0, 80)
  })).sort((a, b) => b.html_chars - a.html_chars);
  const custom = new Set();
  main.querySelectorAll('*').forEach(e => e.classList.forEach(c => {
    if (!/^(et_|et-|wp-|menu|clearfix|sub-menu|current|page_item|nav|screen-reader|mobile_|lazy|entry|post|hentry|type-|status-|format-|has-|ui-)/.test(c)) custom.add(c);
  }));
  return {
    divi_builder_layout: document.body.classList.contains('et_pb_pagebuilder_layout'),
    theme_builder_template: [...document.body.classList].filter(c => /et-tb/.test(c)),
    module_counts: count,
    code_modules: big('.et_pb_code'),
    largest_text_modules: big('.et_pb_text').slice(0, 5),
    style_tags_in_content: main.querySelectorAll('.et_pb_section style').length,
    script_tags_in_content: main.querySelectorAll('.et_pb_section script').length,
    elements_with_inline_style: main.querySelectorAll('.et_pb_section [style]').length,
    custom_classes: custom.size, custom_class_examples: [...custom].slice(0, 30),
    total_elements_in_content: main.querySelectorAll('.et_pb_section *').length
  };
}"""

url, shot = sys.argv[1], sys.argv[2]
with sync_playwright() as pw:
    b = pw.chromium.launch()
    p = b.new_page(user_agent=USER_AGENT, viewport={"width": 1440, "height": 900})
    r = p.goto(url, wait_until="load", timeout=60000)
    p.wait_for_timeout(3000)
    print("status", r.status)
    print(json.dumps(p.evaluate(JS), indent=1))
    p.screenshot(path=shot, full_page=True)
    b.close()
