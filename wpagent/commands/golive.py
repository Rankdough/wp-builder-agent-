"""`wpagent golive <rebuild_dir> <live_id> <draft_id> --confirm-site <name>`:
put a verified rebuild onto the live page through the Visual Builder, then trash the draft.
Divi's own pre-import backup of the live page is downloaded first (restore = import it back)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

from ..adapters.divi.vb import VisualBuilder
from ..adapters.wp.cache import clear_caches
from ..adapters.wp.pages import trash_draft
from ..browser.session import Session
from ..config import Site, global_colors
from ..layout.render import portability_json, render
from ..layout.spec import PageSpec, missing_text, straighten_quotes, validate_spec
from ..runlog import RunLog

CURLY = re.compile("[‘’“”]")


def run(site: Site, rebuild_dir: str, live_id: int, draft_id: int, confirm_site: str | None,
        headless: bool = False) -> int:
    if confirm_site != site.name:
        print(f"Production write: pass --confirm-site {site.name}")
        return 2
    d = Path(rebuild_dir)
    spec = PageSpec.model_validate_json((d / "spec.json").read_text(encoding="utf-8"))
    source = json.loads((d / "source-dump.json").read_text(encoding="utf-8"))
    if not any(CURLY.search(n.get("text") or "") for n in source["nodes"]):
        spec = straighten_quotes(spec)
    validate_spec(spec, f"{site.url}/wp-content/uploads/")
    missing = missing_text(source['nodes'], spec)
    if missing:
        print('Stopped: original text missing from the rebuild:')
        for m in missing:
            print('  -', m[:120])
        return 5

    log = RunLog(site.name, "golive")
    log.write_json("spec.json", json.loads(spec.model_dump_json()))
    colors = global_colors(site.name)
    import_file = log.dir / "import-layout.json"
    import_file.write_text(portability_json(render(spec), live_id, colors), encoding="utf-8")
    log.event("start", live=live_id, draft=draft_id)

    allowed = frozenset({f"et_fb_ajax_save@{live_id}", "et_core_portability_import",
                         "et_fb_process_imported_content", "wpfc_delete_cache", "wpfc_delete_cache_and_minified",
                         f"trash@{draft_id}"})
    with sync_playwright() as pw:
        s = Session(pw, site, log, read_only=False, headless=headless, allowed_writes=allowed)
        try:
            s.login()
            vb = VisualBuilder(s, live_id)
            vb.open()
            backup = vb.import_layout(import_file, log.backup)
            vb.save_published()
            s.screenshot("live-after-save", full_page=False)
            clear_caches(s)
            trash_draft(s, draft_id)
        finally:
            s.close()
    log.event("done", backup=str(backup))
    log.close()
    print(f"\nLive page {live_id} updated. Draft {draft_id} moved to Trash.")
    print(f"Restore point (Divi export of the old live page): {backup}")
    return 0
