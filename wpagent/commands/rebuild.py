"""`wpagent rebuild <source_path> <draft_id>`: rebuild a code-chunk page as native Divi modules in a draft.
Steps: dump source -> Claude spec -> validate -> render -> import via Portability -> Save Draft.
--spec-only stops before touching the site."""
from __future__ import annotations

import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

from ..adapters.divi.vb import VisualBuilder
from ..browser.session import Session
from ..config import Site, global_colors, site_profile
from ..layout.designer import design_page
from ..layout.render import portability_json, render
from ..layout.spec import PageSpec, missing_text, straighten_quotes, validate_spec
from ..runlog import RunLog

DUMP_JS = (Path(__file__).resolve().parents[2] / "scripts" / "dump_code_module.py")


def _dump(site: Site, source_path: str, out: Path) -> dict:
    import runpy
    import sys
    argv = sys.argv
    sys.argv = [str(DUMP_JS), site.url + source_path, str(out)]
    try:
        runpy.run_path(str(DUMP_JS), run_name="__main__")
    finally:
        sys.argv = argv
    return json.loads(out.read_text(encoding="utf-8"))


def run(site: Site, source_path: str, draft_id: int, confirm_site: str | None, spec_file: str | None = None,
        spec_only: bool = False, headless: bool = False) -> int:
    log = RunLog(site.name, "rebuild")
    log.event("start", source=source_path, draft=draft_id)
    dump = _dump(site, source_path, log.dir / "source-dump.json")

    colors = global_colors(site.name)
    media_base = f"{site.url}/wp-content/uploads/"
    if spec_file:
        spec = PageSpec.model_validate_json(Path(spec_file).read_text(encoding="utf-8"))
    else:
        spec = design_page(dump, colors, run_dir=str(log.dir), profile=site_profile(site.name), media_base=media_base,
                           site=site.name)
    log.write_json("spec.json", json.loads(spec.model_dump_json()))
    if not any(re.search('[‘’“”]', n.get('text') or '') for n in dump['nodes']):
        spec = straighten_quotes(spec)
    validate_spec(spec, media_base)
    missing = missing_text(dump['nodes'], spec)
    if missing:
        print('Stopped: original text missing from the rebuild:')
        for m in missing:
            print('  -', m[:120])
        return 5
    layout = render(spec)
    import_file = log.dir / "import-layout.json"
    import_file.write_text(portability_json(layout, draft_id, colors), encoding="utf-8")
    counts = {}
    for sec in spec.sections:
        for row in sec.rows:
            for col in row.columns:
                for m in col.modules:
                    counts[m.type] = counts.get(m.type, 0) + 1
    log.event("spec_valid", sections=len(spec.sections), modules=counts, notes=len(spec.notes))
    print("\nModules:", counts)
    for n in spec.notes:
        print("  note:", n)
    if spec_only:
        log.close()
        print(f"\nSpec only. Import file: {import_file}")
        return 0

    if confirm_site != site.name:
        print(f"Production write: pass --confirm-site {site.name}")
        return 2
    allowed = frozenset({f"et_fb_ajax_save@{draft_id}", "et_core_portability_import",
                         "et_fb_process_imported_content"})  # import parsing in the builder; saving is Save Draft
    with sync_playwright() as pw:
        s = Session(pw, site, log, read_only=False, headless=headless, allowed_writes=allowed)
        try:
            s.login()
            vb = VisualBuilder(s, draft_id)
            vb.open()
            vb.import_layout(import_file, log.backup)
            s.screenshot("after-import", full_page=False)
            vb.save_draft()
            s.screenshot("after-save", full_page=False)
        finally:
            s.close()
    log.event("done", draft=draft_id)
    log.close()
    print(f"\nImported and saved draft {draft_id}. Run folder: {log.dir}")
    return 0
