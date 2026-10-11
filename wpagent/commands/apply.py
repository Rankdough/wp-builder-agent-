"""`wpagent apply <plan_run_dir> --confirm-site <name>`: back up, apply the approved plan, verify.
`wpagent rollback <apply_run_dir> --confirm-site <name>`: put the old values back the same way."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from ..adapters.divi.adapter import DiviAdapter
from ..adapters.divi.customizer import Customizer
from ..adapters.wp.cache import clear_caches
from ..browser.session import Session
from ..config import Site
from ..planner.schema import ChangePlan, VerifyCheck, validate_plan
from ..runlog import RunLog
from ..verify.styles import FrontEnd, run_checks
from .common import CUSTOMIZER_WRITES, read_customizer


class ConfirmError(Exception):
    pass


def _confirm(site: Site, confirm_site: str | None) -> None:
    if confirm_site != site.name:
        raise ConfirmError(f"Production write: pass --confirm-site {site.name} to confirm the target site")


def _measure(front: FrontEnd, checks: list[VerifyCheck]) -> list[dict]:
    """Current computed values for each check, so rollback can prove the site is back to this state."""
    out, current = [], None
    for c in checks:
        if c.page != current:
            front.open(c.page)
            current = c.page
        out.append({"page": c.page, "selector": c.selector, "css_property": c.css_property,
                    "expected": front.computed(c.selector, c.css_property) or ""})
    return out


def _execute(site: Site, log: RunLog, changes: list[tuple[str, str]], checks: list[VerifyCheck],
             plan: ChangePlan | None, headless: bool) -> tuple[list[dict], list[dict]]:
    with sync_playwright() as pw:
        s = Session(pw, site, log, read_only=False, headless=headless, allowed_writes=CUSTOMIZER_WRITES)
        front = FrontEnd(s.browser, site)
        try:
            before = _measure(front, checks)
            s.login()
            # Backup: Divi's own export (allowed now, it re-saves unchanged settings) + a field record.
            DiviAdapter(s).export_backup_for_write()
            current = read_customizer(s)
            log.write_json("backup/customizer-settings.json", current)
            if plan is not None:
                validate_plan(plan, current)  # values must still match what was approved

            c = Customizer(s)
            c.open()
            for setting, value in changes:
                c.set(setting, value)
            c.publish()
            clear_caches(s)

            results = run_checks(front, checks)
            for r in results:
                log.event("verify", **r)
            front.open(checks[0].page)
            front.page.screenshot(path=str(log.shots / "after.png"), full_page=False)
            return before, results
        finally:
            front.close()
            s.close()


def apply(site: Site, plan_dir: str, confirm_site: str | None, headless: bool = False) -> int:
    _confirm(site, confirm_site)
    plan = ChangePlan.model_validate_json((Path(plan_dir) / "plan.json").read_text(encoding="utf-8"))
    if not plan.feasible:
        print("Plan is not feasible; nothing to apply.")
        return 3
    log = RunLog(site.name, "apply")
    log.write_json("plan.json", json.loads(plan.model_dump_json()))
    log.event("start", site=site.name, plan_dir=plan_dir, changes=len(plan.changes))
    changes = [(c.setting, c.new_value) for c in plan.changes]
    before, results = _execute(site, log, changes, plan.verify, plan, headless)
    log.write_json("before-measurements.json", before)
    log.write_json("verify.json", results)
    ok = all(r["pass"] for r in results)
    log.event("done", verified=ok, run_dir=str(log.dir))
    log.close()
    print(f"\nVerification: {'PASS' if ok else 'FAIL'} ({sum(r['pass'] for r in results)}/{len(results)} checks)")
    print(f'Rollback: .venv\\Scripts\\python -m wpagent rollback "{log.dir}" --confirm-site {site.name}')
    return 0 if ok else 4


def rollback(site: Site, apply_dir: str, confirm_site: str | None, headless: bool = False) -> int:
    _confirm(site, confirm_site)
    d = Path(apply_dir)
    plan = ChangePlan.model_validate_json((d / "plan.json").read_text(encoding="utf-8"))
    before = json.loads((d / "before-measurements.json").read_text(encoding="utf-8"))
    log = RunLog(site.name, "rollback")
    log.event("start", site=site.name, apply_dir=apply_dir)
    changes = [(c.setting, c.old_value) for c in reversed(plan.changes)]
    checks = [VerifyCheck(**b) for b in before]
    _, results = _execute(site, log, changes, checks, None, headless)
    log.write_json("verify.json", results)
    ok = all(r["pass"] for r in results)
    log.event("done", verified=ok, run_dir=str(log.dir))
    log.close()
    print(f"\nRollback verification: {'PASS' if ok else 'FAIL'} ({sum(r['pass'] for r in results)}/{len(results)})")
    return 0 if ok else 4
