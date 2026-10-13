"""New components must stay inside their own class and can't carry anything dangerous."""
import pytest

from wpagent.layout.components import registered
from wpagent.layout.newcomponents import ComponentError, NewComponent, check_component


def comp(css, name="rd-score-ring"):
    return NewComponent(name=name, usage="test", css=css)


def test_valid_component():
    check_component(comp(".rd-score-ring{border-radius:50%}.rd-score-ring--red p{color:#f87171}"
                         "@media (max-width:767px){.rd-score-ring{width:80px}}"
                         ".rd-score-ring::after{background:url(\"data:image/svg+xml,%3Csvg%3E%3C/svg%3E\")}"))


@pytest.mark.parametrize("css,msg", [
    ("body{color:red}", "must start with"),
    (".rd-score-ring, .et_pb_button{color:red}", "must start with"),
    (".rd-score-ringx{color:red}", "must start with"),
    (".rd-score-ring a[href]{color:red}", "brackets"),
    ("@import url(x.css);.rd-score-ring{}", "imports"),
    (".rd-score-ring{background:url(https://evil.example/x.png)}", "data:image"),
    (".rd-score-ring{position: fixed}", "fixed"),
])
def test_rejected(css, msg):
    with pytest.raises(ComponentError, match=msg):
        check_component(comp(css))


def test_bad_name_and_existing():
    with pytest.raises(ComponentError, match="names"):
        check_component(comp(".Foo{}", name="Foo"))
    assert "rd-kpi" in registered()
    with pytest.raises(ComponentError, match="already exists"):
        check_component(comp(".rd-kpi{}", name="rd-kpi"))
