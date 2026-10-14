"""Layout spec validation and Divi rendering."""
import json

import pytest

from wpagent.layout.render import portability_json, render
from wpagent.layout.spec import PageSpec, SpecError, validate_spec


def spec(*modules, structure="4_4", ncols=1):
    cols = [{"modules": list(modules)}] + [{"modules": []} for _ in range(ncols - 1)]
    return PageSpec.model_validate({"sections": [{"admin_label": "Hero", "background_color": "#14171b",
                                                  "padding_top": 80, "rows": [{"structure": structure, "columns": cols}]}]})


TEXT = {"type": "text", "html": "<h1>GSC Connector</h1><p>Ask <a href=\"https://x.com\">Claude</a>.</p>",
        "text_color": "#ffffff", "h1_size": 56}
BUTTON = {"type": "button", "text": "Download free on GitHub", "url": "https://github.com/Rankdough/gsc-for-claude",
          "bg_color": "#e02b20", "text_color": "#ffffff", "border_radius": 6}
CODE = {"type": "code", "jsonld": json.dumps({"@context": "https://schema.org", "@graph": [{"@type": "FAQPage"}]})}


def test_valid_spec_renders_native_modules():
    s = spec(TEXT, BUTTON, CODE)
    validate_spec(s)
    out = render(s)
    assert out.startswith("[et_pb_section ") and out.endswith("[/et_pb_section]")
    assert 'column_structure="4_4"' in out and 'type="4_4"' in out
    assert 'header_font_size="56px"' in out and 'text_text_color="#ffffff"' in out
    assert 'button_bg_color="#e02b20"' in out and 'custom_button="on"' in out
    assert '<script type="application/ld+json">{"@context": "https://schema.org", "@graph": [{"@type": "FAQPage"}]}</script>' in out
    assert "style=" not in out and "class=" not in out


@pytest.mark.parametrize("bad,msg", [
    ({"type": "text", "html": "<div class='x'>hi</div>"}, "not allowed"),
    ({"type": "text", "html": "<p style='color:red'>hi</p>"}, "not allowed"),
    ({"type": "text", "html": "<p>see [et_pb_code]</p>"}, "brackets"),
    ({"type": "text", "html": "<style>p{}</style>"}, "not allowed"),
    ({"type": "text", "html": "<a href='javascript:alert(1)'>x</a>"}, "javascript"),
    ({"type": "button", "text": "Go", "url": "javascript:x"}, "url"),
    ({"type": "image", "src": "https://evil.example/x.png", "alt": "x"}, "media library"),
    ({"type": "code", "jsonld": "{not json"}, "valid JSON"),
    ({"type": "code", "jsonld": '{"a": "</script><script>alert(1)"}'}, "script"),
])
def test_bad_modules_rejected(bad, msg):
    with pytest.raises(SpecError, match=msg):
        validate_spec(spec(bad), media_base="https://www.example.com/wp-content/uploads/")


def test_only_one_code_module():
    with pytest.raises(SpecError, match="only one"):
        validate_spec(spec(CODE, CODE))


def test_column_count_must_match_structure():
    with pytest.raises(SpecError, match="needs 2 columns"):
        validate_spec(spec(TEXT, structure="1_2,1_2", ncols=1))


def test_attribute_values_are_encoded():
    s = spec({"type": "button", "text": 'Say "hi"', "url": "https://x.com/?a=1"})
    with pytest.raises(SpecError):
        validate_spec(s)  # quotes in button text rejected
    out = render(spec({"type": "image", "src": "https://www.example.com/wp-content/uploads/a.png", "alt": 'a "b" [c]'}))
    assert 'alt="a %22b%22 %91c%93"' in out


def test_portability_json_shape():
    d = json.loads(portability_json("[et_pb_section][/et_pb_section]", 3798, []))
    assert d["context"] == "et_builder" and d["data"] == {"3798": "[et_pb_section][/et_pb_section]"}
    assert set(d) == {"context", "data", "presets", "global_colors", "images", "thumbnails"}


def test_new_fields_render():
    s = PageSpec.model_validate({"sections": [{"admin_label": "Setup", "css_id": "setup", "rows": [
        {"structure": "4_4", "max_width": 1120, "columns": [{"modules": [
            {"type": "button", "text": "Download", "url": "https://x.com", "bg_color": "#e02b20", "show_arrow": True},
            {"type": "toggle", "title": "Is it free?", "body_html": "<p>Yes.</p>"}]}]}]}]})
    validate_spec(s)
    out = render(s)
    assert 'module_id="setup"' in out and 'max_width="1120px"' in out
    assert 'button_use_icon="on"' in out and 'button_on_hover="off"' in out and 'title_level="h3"' in out


def test_straighten_quotes_keeps_jsonld():
    from wpagent.layout.spec import straighten_quotes
    s = spec({"type": "text", "html": "<p>Claude’s “app”</p>"},
             {"type": "code", "jsonld": json.dumps({"name": "It’s"}, ensure_ascii=False)})
    out = straighten_quotes(s)
    mods = out.sections[0].rows[0].columns[0].modules
    assert mods[0].html == "<p>Claude's \"app\"</p>"
    assert "’" in mods[1].jsonld


def test_glow_renders_native_gradient():
    s = PageSpec.model_validate({"sections": [{"admin_label": "Hero", "background_color": "#000000",
        "glow": {"color": "#e02b20", "opacity": 0.28, "position": "top right", "fade_at_percent": 55},
        "rows": [{"structure": "4_4", "columns": [{"modules": [{"type": "text", "html": "<p>x</p>"}]}]}]}]})
    out = render(s)
    assert 'use_background_color_gradient="on"' in out and 'background_color_gradient_type="circular"' in out
    assert 'background_color_gradient_stops="rgba(224,43,32,0.28) 0%|rgba(0,0,0,0) 55%"' in out
    assert 'background_color="#000000"' in out


def test_row_gutter_and_equal_heights():
    s = PageSpec.model_validate({"sections": [{"admin_label": "Cards", "rows": [
        {"structure": "1_3,1_3,1_3", "gutter": 2, "equal_heights": True, "padding": [11, 0, 11, 0],
         "columns": [{"modules": [{"type": "text", "html": "<p>a</p>"}]}] * 3}]}]})
    out = render(s)
    assert 'use_custom_gutter="on"' in out and 'gutter_width="2"' in out and 'make_equal="on"' in out
    assert 'custom_padding="11px|0px|11px|0px|false|false"' in out


def test_component_classes_only_from_allowlist():
    out = render(spec({"type": "text", "css_class": "rd-pills rd-pills--red", "html": "<ul><li>Free tool</li></ul>"}))
    assert 'module_class="rd-pills rd-pills--red"' in out
    with pytest.raises(Exception):
        spec({"type": "text", "css_class": "my-random-class", "html": "<p>x</p>"})


def test_missing_text_detects_dropped_words():
    from wpagent.layout.spec import missing_text
    src = [{"text": "The connectors we tried needed paid plans or never finished authorising."},
           {"text": "Get the code from . It is free under the MIT licence."}]
    full = spec({"type": "text", "html": "<p>The connectors we tried needed paid plans or never finished authorising.</p>"
                                          "<p>Get the code from <a href='https://x.com'>GitHub</a>. It is free under the MIT licence.</p>"})
    cut = spec({"type": "text", "html": "<p>The connectors we tried needed paid plans.</p>"
                                         "<p>Get the code from <a href='https://x.com'>GitHub</a>. It is free under the MIT licence.</p>"})
    assert missing_text(src, full) == []
    assert missing_text(src, cut) == ["The connectors we tried needed paid plans or never finished authorising."]


def test_button_url_schemes():
    import pytest
    from wpagent.layout.spec import PageSpec, SpecError, validate_spec

    def spec(url):
        return PageSpec.model_validate({"sections": [{"admin_label": "s", "rows": [{"structure": "4_4", "columns": [
            {"modules": [{"type": "button", "text": "Email us", "url": url}]}]}]}]})
    validate_spec(spec("mailto:info@example.com?subject=Hi%20there"))
    for bad in ("javascript:alert(1)", "mailto:a b", "data:text/html,x"):
        with pytest.raises(SpecError):
            validate_spec(spec(bad))
