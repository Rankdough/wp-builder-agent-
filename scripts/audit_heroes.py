"""Read-only: list every published page and post, and describe its first (header) section's background.
Usage (add --site <name>): audit_heroes.py <out.json>"""
import json
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.config import USER_AGENT, script_site

HERO = r"""() => {
  const main = document.querySelector('#main-content') || document.body;
  const sec = main.querySelector('.et_pb_section');
  const tb = [...document.body.classList].filter(c => /et-tb-has-template|et-tb-has-header|et-tb-has-body/.test(c));
  if (!sec) return {divi: false, tb};
  const c = getComputedStyle(sec);
  return {divi: true, tb, cls: [...sec.classList].filter(x => /et_pb_section_\d|specialty|fullwidth/.test(x)).join(' '),
          bg_color: c.backgroundColor, bg_image: c.backgroundImage.slice(0, 140),
          height: Math.round(sec.getBoundingClientRect().height),
          heading: (sec.querySelector('h1') || {}).innerText || null};
}"""

site = script_site()
items = []
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(user_agent=USER_AGENT, viewport={"width": 1440, "height": 900})
    for kind in ("pages", "posts"):
        page_no = 1
        while True:
            r = ctx.request.get(f"{site.url}/wp-json/wp/v2/{kind}?per_page=100&page={page_no}&_fields=id,link,title,status")
            if not r.ok:
                break
            batch = r.json()
            items += [{"kind": kind[:-1], "id": x["id"], "url": x["link"], "title": x["title"]["rendered"]} for x in batch]
            if len(batch) < 100:
                break
            page_no += 1
    p = ctx.new_page()
    for it in items:
        try:
            p.goto(it["url"], wait_until="load", timeout=45000)
            it.update(p.evaluate(HERO))
        except Exception as exc:
            it["error"] = str(exc)[:120]
    b.close()

json.dump(items, open(sys.argv[1], "w", encoding="utf-8"), indent=1, ensure_ascii=False)
glow = lambda i: "radial-gradient" in (i.get("bg_image") or "") or "url(" in (i.get("bg_image") or "")
print(f"{len(items)} items ({sum(i['kind']=='page' for i in items)} pages, {sum(i['kind']=='post' for i in items)} posts)")
for i in items:
    print(f"{i['kind']:<4} {i['id']:<5} {'GLOW/IMG' if glow(i) else '-':<8} bg={i.get('bg_color','?'):<22} h={i.get('height','?'):<5} tb={','.join(i.get('tb', []))[:30]:<30} {i['url'].replace(site.url,'')}")
