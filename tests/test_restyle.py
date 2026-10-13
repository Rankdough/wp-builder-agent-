"""Restyle only changes Divi settings by role, never module content."""
from wpagent.layout.restyle import NAVY_RED, restyle_layout, role_of


def test_roles():
    assert role_of("background_color") == "background"
    assert role_of("open_toggle_background_color") == "background"
    assert role_of("text_text_color") == "text"
    assert role_of("header_2_text_color") == "text"
    assert role_of("border_color_all") == "border"
    assert role_of("button_border_color") == "border"
    assert role_of("button_bg_color") == "button_bg"
    assert role_of("button_border_radius") == "button_radius"
    assert role_of("background_color_gradient_stops") is None
    assert role_of("admin_label") is None


def test_black_background_becomes_navy_but_black_text_stays():
    raw = ('[et_pb_section background_color="#000000"][et_pb_text text_text_color="#000000" '
           'background_color="#14171b" border_color_all="#23272d"]<p style="color:#000000">x</p>[/et_pb_text][/et_pb_section]')
    new, counts = restyle_layout(raw, NAVY_RED)
    assert '[et_pb_section background_color="#0a1120"]' in new
    assert 'text_text_color="#000000"' in new
    assert 'background_color="#0f1c2e"' in new and 'border_color_all="#1e3350"' in new
    assert '<p style="color:#000000">x</p>' in new  # content untouched
    assert counts == {"background:#000000->#0a1120": 1, "background:#14171b->#0f1c2e": 1, "border:#23272d->#1e3350": 1}


def test_red_and_code_module_svg_untouched():
    raw = ('[et_pb_button button_bg_color="#e02b20" button_border_radius="3px"][/et_pb_button]'
           '[et_pb_code]<svg><rect fill="#000000" stroke="#26292f"/></svg>[/et_pb_code]')
    new, counts = restyle_layout(raw, NAVY_RED)
    assert 'button_bg_color="#e02b20"' in new and 'button_border_radius="8px"' in new
    assert '<rect fill="#000000" stroke="#26292f"/>' in new
    assert counts == {"button_radius:3px->8px": 1}


def test_idempotent():
    raw = '[et_pb_section background_color="#000000"][/et_pb_section]'
    once, _ = restyle_layout(raw, NAVY_RED)
    twice, counts = restyle_layout(once, NAVY_RED)
    assert once == twice and counts == {}


def test_black_shadow_stays_invisible():
    new, counts = restyle_layout('[et_pb_column box_shadow_color="#000000" box_shadow_color_hover="#000000"][/et_pb_column]', NAVY_RED)
    assert new.count("#0a1120") == 2 and counts == {"shadow:#000000->#0a1120": 2}
