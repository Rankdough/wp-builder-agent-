"""`wpagent plan "<task>"`: read-only. Inspect the site, ask Claude for a change plan, validate, save it."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from ..browser.session import Session
from ..config import Site, site_profile
from ..planner.schema import ChangePlan, PlanError, validate_plan
from ..runlog import RunLog
from ..verify.styles import FrontEnd
from .common import button_globals, inspect_buttons, page_list, print_plan, read_customizer


def run(site: Site, task: str, plan_file: str | None = None, headless: bool = False) -> int:
    log = RunLog(site.name, "plan")
    log.event("start", site=site.name, task=task, mode="read-only")
    with sync_playwright() as pw:
        s = Session(pw, site, log, read_only=True, headless=headless)
        front = FrontEnd(s.browser, site)
        try:
            pages = page_list(s)
            buttons = inspect_buttons(front, pages)
            s.login()
            customizer = read_customizer(s)
        finally:
            front.close()
            s.close()

    context = {
        "site_profile": site_profile(site.name),
        "pages_checked": pages,
        "customizer_button_globals": button_globals(customizer),
        "customizer_settings": {k: v for k, v in customizer.items() if k.startswith("et_divi[")},
        "buttons_by_page": buttons,
    }
    log.write_json("context.json", context)

    if plan_file:
        plan = ChangePlan.model_validate_json(Path(plan_file).read_text(encoding="utf-8"))
        plan.task = task
        log.event("plan_loaded", file=plan_file)
    else:
        from ..planner.planner import make_plan
        plan = make_plan(task, context, run_dir=str(log.dir))
        log.event("plan_created", feasible=plan.feasible, rung=plan.rung, changes=len(plan.changes))

    log.write_json("plan.json", json.loads(plan.model_dump_json()))
    log.write_json("customizer-before.json", customizer)
    print_plan(plan)
    try:
        validate_plan(plan, customizer)
    except PlanError as exc:
        log.event("plan_rejected", error=str(exc))
        print(f"Plan rejected by validation: {exc}")
        log.close()
        return 3
    log.close()
    if plan.feasible:
        print("Nothing has been changed. To apply this exact plan after approval:")
        print(f'  .venv\\Scripts\\python -m wpagent apply "{log.dir}" --confirm-site {site.name}')
    return 0
