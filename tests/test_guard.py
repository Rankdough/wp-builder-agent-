"""Read-only guard: saves must be blocked, reads and exports allowed."""
from types import SimpleNamespace

import pytest

from wpagent.browser.session import Session
from wpagent.config import Site

SITE = Site("t", "https://www.example.com", "u", "p", ("/",), False)


class FakeRoute:
    def __init__(self):
        self.result = None

    def continue_(self):
        self.result = "continued"

    def abort(self):
        self.result = "aborted"


def make_session():
    s = Session.__new__(Session)
    s.site, s.read_only, s.blocked, s.allowed_writes = SITE, True, [], frozenset()
    s.log = SimpleNamespace(event=lambda *a, **k: None)
    return s


def req(method, path, body=""):
    return SimpleNamespace(method=method, url=f"https://www.example.com{path}", post_data=body)


@pytest.mark.parametrize(
    "method,path,body,expected",
    [
        ("GET", "/wp-admin/options.php", "", "continued"),
        ("POST", "/wp-login.php", "log=u", "continued"),
        ("POST", "/wp-admin/admin-ajax.php", "action=heartbeat", "continued"),
        ("POST", "/wp-admin/admin-ajax.php", "action=et_core_portability_export", "continued"),
        ("POST", "/wp-admin/admin-ajax.php", "action=et_fb_retrieve_builder_data", "continued"),
        ("POST", "/wp-admin/admin-ajax.php", "action=et_fb_update_builder_assets", "continued"),
        ("POST", "/wp-admin/admin-ajax.php", "action=et_fb_ajax_drop_autosave", "aborted"),
        ("POST", "/wp-admin/admin-ajax.php", "action=et_fb_ajax_save", "aborted"),
        ("POST", "/wp-admin/admin-ajax.php", "action=customize_save", "aborted"),
        ("POST", "/wp-admin/admin-ajax.php", "action=install-plugin", "aborted"),
        ("POST", "/wp-admin/admin-ajax.php?action=et_theme_builder_api_save", "", "aborted"),
        ("POST", "/wp-admin/options.php", "a=1", "aborted"),
        ("POST", "/wp-admin/post.php", "a=1", "aborted"),
        ("POST", "/wp-json/wp/v2/pages/5", "{}", "aborted"),
        ("POST", "/wp-admin/admin.php?page=et_divi_options", "a=1", "aborted"),
    ],
)
def test_guard(method, path, body, expected):
    s, route = make_session(), FakeRoute()
    s._guard(route, req(method, path, body))
    assert route.result == expected


def write_session(allowed):
    s = make_session()
    s.read_only, s.allowed_writes = False, frozenset(allowed)
    return s


def test_write_mode_allows_only_planned_actions():
    s = write_session({"customize_save"})
    for body, expected in [
        ("action=customize_save", "continued"),
        ("action=save_epanel", "aborted"),
        ("action=install-plugin", "aborted"),
        ("action=et_fb_ajax_save", "aborted"),
    ]:
        route = FakeRoute()
        s._guard(route, req("POST", "/wp-admin/admin-ajax.php", body))
        assert route.result == expected, body


def test_write_mode_still_blocks_write_endpoints():
    s, route = write_session({"customize_save"}), FakeRoute()
    s._guard(route, req("POST", "/wp-admin/options.php", "a=1"))
    assert route.result == "aborted"


def test_read_only_ignores_allowlist():
    s = make_session()
    s.allowed_writes = frozenset()
    route = FakeRoute()
    s._guard(route, req("POST", "/wp-admin/admin-ajax.php", "action=customize_save"))
    assert route.result == "aborted"


@pytest.mark.parametrize("path,expected", [
    ("/wp-admin/post.php?post=5&action=edit", "continued"),
    ("/wp-admin/admin.php?page=et_divi_options", "continued"),
    ("/wp-admin/admin.php?action=duplicate_post_new_draft&post=5&_wpnonce=abc", "aborted"),
    ("/wp-admin/post.php?post=5&action=trash&_wpnonce=abc", "aborted"),
    ("/wp-admin/plugins.php?action=activate&plugin=x&_wpnonce=abc", "aborted"),
    ("/wp-login.php?action=logout&_wpnonce=abc", "aborted"),
    ("/wp-admin/edit.php?s=GSC&post_type=page&_wpnonce=abc&action=-1&action2=-1", "continued"),
    ("/wp-admin/edit.php?post_type=page&_wpnonce=abc&action=-1&action2=trash&post[]=5", "aborted"),
    ("/wp-admin/edit.php?post_type=page&_wpnonce=abc&action=trash&post[]=5", "aborted"),
])
def test_get_action_links(path, expected):
    s, route = make_session(), FakeRoute()
    s._guard(route, req("GET", path))
    assert route.result == expected


def test_get_action_link_allowed_when_planned():
    s, route = write_session({"duplicate_post_new_draft"}), FakeRoute()
    s._guard(route, req("GET", "/wp-admin/admin.php?action=duplicate_post_new_draft&post=5&_wpnonce=abc"))
    assert route.result == "continued"


@pytest.mark.parametrize("body,expected", [
    ("action=et_fb_ajax_save&post_id=3798&options=x", "continued"),
    ("action=et_fb_ajax_save&post_id=3692&options=x", "aborted"),
    ("action=et_fb_ajax_save&options=x", "aborted"),
    ('--b\r\nContent-Disposition: form-data; name="action"\r\n\r\net_fb_ajax_save\r\n--b\r\n'
     'Content-Disposition: form-data; name="post_id"\r\n\r\n3798\r\n--b--', "continued"),
])
def test_post_scoped_write(body, expected):
    s, route = write_session({"et_fb_ajax_save@3798"}), FakeRoute()
    s._guard(route, req("POST", "/wp-admin/admin-ajax.php", body))
    assert route.result == expected


@pytest.mark.parametrize("path,expected", [
    ("/wp-admin/post.php?post=3798&action=trash&_wpnonce=abc", "continued"),
    ("/wp-admin/post.php?post=3692&action=trash&_wpnonce=abc", "aborted"),
    ("/wp-admin/post.php?post=3798&action=delete&_wpnonce=abc", "aborted"),
])
def test_trash_scoped_to_one_post(path, expected):
    s, route = write_session({"trash@3798"}), FakeRoute()
    s._guard(route, req("GET", path))
    assert route.result == expected


def test_customizer_preview_render_allowed():
    s, route = make_session(), FakeRoute()
    s.allowed_writes = frozenset()
    s._guard(route, req("POST", "/?customize_changeset_uuid=abc", "wp_customize=on"))
    assert route.result == "continued"
