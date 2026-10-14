"""Restyle one DRAFT with a colour theme, values only: Divi colour settings by role, header glow gradients, and
colours inside existing Code module CSS. Stops if any visible text would change. Dry run unless --confirm-site.
Usage (add --site <name>): palette_swap.py <draft_id> <theme> [--confirm-site X]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright

from wpagent.adapters.divi.vb import VisualBuilder
from wpagent.browser.session import Session
from wpagent.config import global_colors, script_site
from wpagent.layout.render import portability_json
from wpagent.layout.restyle import THEMES, restyle_layout, swap_code_colours, swap_gradients, visible_text
from wpagent.runlog import RunLog

FETCH = """async (id) => (await (await fetch(`/wp-json/wp/v2/pages/${id}?context=edit&_fields=status,content`,
    {headers: {'X-WP-Nonce': wpApiSettings.nonce}})).json())"""

site = script_site()
args = [a for a in sys.argv[1:] if not a.startswith("--confirm-site")]
confirm = sys.argv[sys.argv.index("--confirm-site") + 1] if "--confirm-site" in sys.argv else None
if confirm:
    args.remove(confirm)
draft_id, theme, live = int(args[0]), THEMES[args[1]], confirm == site.name
log = RunLog(site.name, "palette-swap" if live else "palette-swap-dry")
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
        new, counts = restyle_layout(raw, theme)
        new, n_grad = swap_gradients(new, theme.get("gradient", {}))
        new, n_code = swap_code_colours(new, theme.get("code_css", {}))
        if visible_text(new) != visible_text(raw):
            raise SystemExit("Visible text would change: stopped")
        (log.backup / f"{draft_id}-before.txt").write_text(raw, encoding="utf-8")
        (log.dir / f"{draft_id}-after.txt").write_text(new, encoding="utf-8")
        print(f"Divi settings changed: {sum(counts.values())} {counts}\nGradients: {n_grad}  Code CSS colours: {n_code}"
              f"\nVisible text unchanged: yes")
        if live:
            f = log.dir / "import.json"
            f.write_text(portability_json(new, draft_id, global_colors(site.name)), encoding="utf-8")
            vb = VisualBuilder(s, draft_id)
            vb.open()
            vb.import_layout(f, log.backup)
            vb.save_draft()
            print(f"Draft {draft_id} restyled. Run folder: {log.dir}")
    finally:
        s.close()
        log.close()
