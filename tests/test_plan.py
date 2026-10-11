"""Plan validation and style normalisation."""
import pytest

from wpagent.planner.schema import Change, ChangePlan, PlanError, VerifyCheck, validate_plan
from wpagent.verify.styles import normalize

CUSTOMIZER = {
    "et_divi[all_buttons_bg_color]": "rgba(0,0,0,0)",
    "et_divi[all_buttons_border_radius]": "3",
    "et_divi[all_buttons_border_radius_hover]": False,
}
VERIFY = [VerifyCheck(page="/", selector=".et_pb_button_0", css_property="border-radius", expected="6px")]


def plan(*changes, rung="theme_options_or_customizer", verify=VERIFY, feasible=True):
    return ChangePlan(task="t", feasible=feasible, rung=rung, changes=list(changes), verify=verify)


def change(setting="et_divi[all_buttons_border_radius]", old="3", new="6"):
    return Change(action="customizer_set", setting=setting, old_value=old, new_value=new, reason="r")


def test_valid_plan_passes():
    validate_plan(plan(change()), CUSTOMIZER)


def test_false_setting_reads_as_empty_old_value():
    validate_plan(plan(change("et_divi[all_buttons_border_radius_hover]", "", "6")), CUSTOMIZER)


@pytest.mark.parametrize("bad,msg", [
    (plan(change(old="4")), "old value"),
    (plan(change(setting="et_divi[made_up]")), "Unknown"),
    (plan(change(setting="custom_css")), "Unknown"),
    (plan(change(new="6px;}body{display:none")), "code"),
    (plan(change(), change()), "twice"),
    (plan(change(), rung="theme_custom_css"), "CSS"),
    (plan(change(), verify=[]), "verification"),
    (plan(), "no changes"),
    (plan(change(), feasible=False), "Infeasible"),
])
def test_bad_plans_rejected(bad, msg):
    with pytest.raises(PlanError, match=msg):
        validate_plan(bad, CUSTOMIZER)


def test_css_rung_allowed_with_explicit_flag():
    validate_plan(plan(change(), rung="module_custom_css"), CUSTOMIZER, allow_css=True)


@pytest.mark.parametrize("a,b", [
    ("#ff8a3d", "rgb(255, 138, 61)"),
    ("#FFF", "rgb(255, 255, 255)"),
    ("rgba(255,138,61,1)", "rgb(255, 138, 61)"),
    ("rgba(0, 0, 0, 0)", "rgba(0,0,0,0)"),
    (" 6px ", "6px"),
])
def test_normalize(a, b):
    assert normalize(a) == normalize(b)


def test_cost_usd():
    from types import SimpleNamespace
    from wpagent.planner.usage import cost_usd
    u = SimpleNamespace(input_tokens=1_000_000, output_tokens=100_000, cache_read_input_tokens=0, cache_creation_input_tokens=0)
    assert round(cost_usd("claude-opus-5-5", u), 2) == 6.00  # $4 in + $2 out
