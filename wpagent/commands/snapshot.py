"""M1: log in, snapshot front-end pages and Divi admin screens, export backups. Read-only."""
from __future__ import annotations

import re
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from ..adapters.divi.adapter import DiviAdapter
from ..browser.session import Session
from ..config import Site
from ..runlog import RunLog


def _latest_post_path(session: Session) -> str | None:
    resp = session.context.request.get(f"{session.site.url}/feed/")
    if not resp.ok:
        session.log.event("feed_error", status=resp.status)
        return None
    match = re.search(r"<item>.*?<link>([^<]+)</link>", resp.text(), re.S)
    return urlparse(match.group(1).strip()).path if match else None


def _slug(path: str) -> str:
    return path.strip("/").replace("/", "_") or "home"


def run(site: Site, headless: bool = False) -> int:
    log = RunLog(site.name, "snapshot")
    log.event("start", site=site.name, url=site.url, staging=site.is_staging, mode="read-only")
    with sync_playwright() as pw:
        s = Session(pw, site, log, read_only=True, headless=headless)
        try:
            pages = list(site.pages)
            latest = _latest_post_path(s)
            if latest and latest not in pages:
                pages.append(latest)

            # Front end, logged out, so screenshots show what visitors see.
            for path in pages:
                for vp in ("desktop", "mobile"):
                    s.set_viewport(vp)
                    s.goto(path)
                    s.load_lazy()
                    s.screenshot(f"front-{_slug(path)}-{vp}")
            s.set_viewport("desktop")

            s.login()
            divi = DiviAdapter(s)
            detected = divi.detect()
            divi.snapshot_admin()
            divi.snapshot_visual_builder(pages[0])
            backups = divi.export_backup()

            summary = {
                "site": site.url,
                "staging": site.is_staging,
                "detected": detected,
                "pages": pages,
                "backups": [b.split("\\")[-1] for b in backups],
                "selectors_used": divi.selectors_used,
                "blocked_requests": s.blocked,
            }
            log.write_json("summary.json", summary)
            log.event("done", run_dir=str(log.dir), backups=len(backups), blocked=len(s.blocked))
            return 0
        finally:
            s.close()
            log.close()
