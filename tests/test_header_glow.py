"""Header glow only touches the first section's opening tag."""
from wpagent.commands.header_glow import add_glow

GLOW = {"color": "#e02b20", "opacity": 0.28, "position": "top right", "fade_at_percent": 55}
BODY = '[et_pb_row][et_pb_column type="4_4"][et_pb_text]Hi[/et_pb_text][/et_pb_column][/et_pb_row][/et_pb_section]'


def test_adds_gradient_to_first_section_only():
    raw = '[et_pb_section fb_built="1" background_color="#000000"]' + BODY + '[et_pb_section background_color="#000000"]x[/et_pb_section]'
    new, status = add_glow(raw, GLOW)
    assert status == "change"
    first, rest = new.split("]", 1)
    assert 'use_background_color_gradient="on"' in first and 'background_color="#000000"' in first
    assert rest == raw.split("]", 1)[1]
    assert new.count("use_background_color_gradient") == 1


def test_skips():
    assert add_glow('[et_pb_section background_color="#ffffff"]' + BODY, GLOW)[1].startswith("skip: header background")
    assert add_glow('[et_pb_section background_color="#000000" background_image="x.jpg"]' + BODY, GLOW)[1] == "skip: section has a background image"
    assert add_glow('[et_pb_section background_color="#000000" use_background_color_gradient="on"]' + BODY, GLOW)[1] == "skip: already has a gradient"
    assert add_glow("<p>classic content</p>", GLOW)[1] == "skip: no Divi section"
