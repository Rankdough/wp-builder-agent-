"""Read-only: dump the structure, text, links, images and script of a page built inside a Divi Code module.
Usage: dump_code_module.py <url> <out.json>"""
import json
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.config import USER_AGENT

JS = r"""() => {
  const root = document.querySelector('.et_pb_code_inner');
  if (!root) return null;
  const nodes = [];
  const walk = (n, depth) => {
    for (const c of n.children) {
      if (c.tagName === 'STYLE' || c.tagName === 'SCRIPT') continue;
      const own = [...c.childNodes].filter(x => x.nodeType === 3).map(x => x.textContent.trim()).join(' ').trim();
      const cs = getComputedStyle(c);
      nodes.push({
        depth, tag: c.tagName.toLowerCase(), cls: String(c.className || ''),
        text: own.slice(0, 300),
        href: c.getAttribute('href') || undefined,
        src: c.getAttribute('src') || undefined, alt: c.getAttribute('alt') || undefined,
        color: cs.color, bg: cs.backgroundColor, font_size: cs.fontSize, font_weight: cs.fontWeight,
        radius: cs.borderRadius, border: cs.borderTopWidth + ' ' + cs.borderTopColor
      });
      walk(c, depth + 1);
    }
  };
  walk(root, 0);
  return {
    nodes,
    style: [...root.querySelectorAll('style')].map(s => s.textContent).join('\n'),
    script: [...root.querySelectorAll('script')].map(s => s.textContent).join('\n'),
    title: document.title,
    meta_description: (document.querySelector('meta[name=description]') || {}).content || null
  };
}"""

url, out = sys.argv[1], sys.argv[2]
with sync_playwright() as pw:
    b = pw.chromium.launch()
    p = b.new_page(user_agent=USER_AGENT, viewport={"width": 1440, "height": 900})
    p.goto(url, wait_until="load", timeout=60000)
    p.wait_for_timeout(2000)
    data = p.evaluate(JS)
    b.close()
open(out, "w", encoding="utf-8").write(json.dumps(data, indent=1, ensure_ascii=False))
print(f"{len(data['nodes'])} nodes, style {len(data['style'])} chars, script {len(data['script'])} chars -> {out}")
