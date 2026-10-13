"""Our component CSS block replaces its earlier version and never touches other CSS."""
from wpagent.commands.theme_css import BLOCK_END, merge_block

V1 = "/* wp-builder-agent: reusable components. Added 2026-10-09. */\n.rd-pills li{border-radius:999px}"
V2 = "/* wp-builder-agent: reusable components v2 */\n.rd-pills li{border-radius:6px}\n" + BLOCK_END


def test_append_to_empty():
    assert merge_block("", V2) == V2 + "\n"


def test_replace_v1_without_end_marker():
    out = merge_block(V1 + "\n", V2)
    assert "999px" not in out and out.strip() == V2


def test_replace_v2_keeps_other_css_before_and_after():
    before = ".mine{color:red}\n\n" + V2 + "\n.after{color:blue}\n"
    v3 = V2.replace("6px", "4px")
    out = merge_block(before, v3)
    assert out.startswith(".mine{color:red}") and ".after{color:blue}" in out and "4px" in out and "6px" not in out
