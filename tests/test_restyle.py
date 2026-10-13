"""Restyle only changes Divi settings by role, never module content."""
from wpagent.layout.restyle import CARD, LINE, NAVY_RED, PAGE, restyle_layout, role_of


def test_roles():
    assert role_of("background_color") == "background"
    assert role_of("open_toggle_background_color") == "background"
    assert role_of("text_text_color") == "text"
    assert role_of("header_2_text_color") == "text"
    assert role_of("icon_color") == "icon"
    assert role_of("border_color_all") == "border"
    assert role_of("button_border_color") == "border"
    assert role_of("button_bg_color") == "button_bg"
    assert role_of("button_border_radius") == "button_radius"
    assert role_of("background_color_gradient_stops") is None
    assert role_of("admin_label") is None


def test_black_background_becomes_navy_but_black_text_stays():
    raw = ('[et_pb_section background_color="#000000"][et_pb_text text_text_color="#000000"]'
           '<p style="color:#000000">x</p>[/et_pb_text][/et_pb_section]')
    new, counts = restyle_layout(raw, NAVY_RED)
    assert f'[et_pb_section background_color="{PAGE}"]' in new
    assert 'text_text_color="#000000"' in new
    assert '<p style="color:#000000">x</p>' in new  # content untouched
    assert counts == {f"background:#000000->{PAGE}": 1}


def test_cards_get_border_and_rounding():
    raw = '[et_pb_column type="1_3" background_color="#14171b" border_radii="on|0px|0px|0px|0px"]x[/et_pb_column]'
    new, counts = restyle_layout(raw, NAVY_RED)
    assert f'background_color="{CARD}"' in new and f'border_color_all="{LINE}"' in new
    assert 'border_radii="on|16px|16px|16px|16px"' in new and 'border_width_all="1px"' in new
    assert counts[f"background:#14171b->{CARD}"] == 1 and counts["card:et_pb_column"] == 1


def test_sections_are_not_cards():
    new, counts = restyle_layout('[et_pb_section background_color="#14171b"][/et_pb_section]', NAVY_RED)
    assert "border_radii" not in new and "card:et_pb_section" not in counts


def test_buttons_icons_red_and_code_svg():
    raw = ('[et_pb_button custom_button="on" button_bg_color="#e02b20"][/et_pb_button]'
           '[et_pb_blurb icon_color="#ffffff" header_text_color="#ffffff"][/et_pb_blurb]'
           '[et_pb_code]<svg><rect fill="#000000" stroke="#26292f"/></svg>[/et_pb_code]')
    new, counts = restyle_layout(raw, NAVY_RED)
    assert 'button_bg_color="#e02b20"' in new and 'button_border_radius="8px"' in new
    assert 'icon_color="#f87171"' in new and 'header_text_color="#ffffff"' in new
    assert '<rect fill="#000000" stroke="#26292f"/>' in new
    assert counts == {"button:radius": 1, "icon:#ffffff->#f87171": 1}


def test_black_shadow_stays_invisible():
    new, counts = restyle_layout('[et_pb_row box_shadow_color="#000000"][/et_pb_row]', NAVY_RED)
    assert f'box_shadow_color="{PAGE}"' in new


def test_idempotent_and_upgrades_first_pilot_values():
    raw = '[et_pb_section background_color="#0a1120"][et_pb_column background_color="#0f1c2e"]x[/et_pb_column][/et_pb_section]'
    once, _ = restyle_layout(raw, NAVY_RED)
    twice, counts = restyle_layout(once, NAVY_RED)
    assert PAGE in once and CARD in once and once == twice and counts == {}
