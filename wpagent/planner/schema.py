"""Change plan schema. The planner must return this; code validates it before anything is applied."""
from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field

from ..adapters.base import CSS_RUNGS, EDIT_LADDER

Rung = Literal[EDIT_LADDER]  # type: ignore[valid-type]
SETTING_ID = re.compile(r"^[a-z0-9_]+(\[[a-z0-9_]+\])?$")


class Change(BaseModel):
    action: Literal["customizer_set"]
    setting: str = Field(description="Customizer setting id, e.g. et_divi[all_buttons_bg_color]")
    old_value: str = Field(description="Current value exactly as given in the context")
    new_value: str
    reason: str


class VerifyCheck(BaseModel):
    page: str = Field(description="Front-end path starting with /")
    selector: str = Field(description="CSS selector of the element to measure, e.g. .et_pb_button_0")
    css_property: str = Field(description="Computed style property, e.g. background-color, border-radius")
    expected: str = Field(description="Expected computed value, e.g. #ff8a3d or 6px")


class ChangePlan(BaseModel):
    task: str
    feasible: bool = Field(description="False if the task cannot be done with the supported actions")
    rung: Optional[Rung] = None
    skipped_rungs: list[str] = Field(default_factory=list, description="Why each higher rung was not used")
    changes: list[Change] = Field(default_factory=list)
    verify: list[VerifyCheck] = Field(default_factory=list)
    pages_affected: list[str] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list, description="What else changes, and what will NOT change")
    blocked_reason: Optional[str] = None


class PlanError(Exception):
    pass


def validate_plan(plan: ChangePlan, customizer: dict, allow_css: bool = False) -> None:
    """Reject plans that touch unknown settings, misstate current values or use CSS without approval."""
    if not plan.feasible:
        if plan.changes:
            raise PlanError("Infeasible plan must not contain changes")
        return
    if not plan.changes:
        raise PlanError("Feasible plan has no changes")
    if plan.rung in CSS_RUNGS and not allow_css:
        raise PlanError(f"Plan uses CSS rung '{plan.rung}'; needs explicit --allow-css approval")
    if not plan.verify:
        raise PlanError("Plan has no verification checks")
    seen = set()
    for c in plan.changes:
        if not SETTING_ID.match(c.setting):
            raise PlanError(f"Invalid setting id: {c.setting!r}")
        if c.setting not in customizer:
            raise PlanError(f"Unknown Customizer setting: {c.setting}")
        if c.setting in seen:
            raise PlanError(f"Setting changed twice: {c.setting}")
        seen.add(c.setting)
        current = "" if customizer[c.setting] in (None, False) else str(customizer[c.setting])
        if current != c.old_value:
            raise PlanError(f"{c.setting}: plan says old value {c.old_value!r}, site has {current!r}")
        if re.search(r"[<>{};]", c.new_value):
            raise PlanError(f"{c.setting}: new value looks like code: {c.new_value!r}")
    for v in plan.verify:
        if not v.page.startswith("/"):
            raise PlanError(f"Verify page must be a path: {v.page!r}")
