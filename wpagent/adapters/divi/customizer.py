"""Change Divi Theme Customizer settings through the Customizer's own controls, then Publish."""
from __future__ import annotations

from ...browser.session import Session


def _control_id(setting: str) -> str:
    return "#customize-control-" + setting.replace("[", "-").replace("]", "")


def _norm(value) -> str:
    return "" if value in (None, False) else str(value).strip().lower()


class Customizer:
    def __init__(self, session: Session):
        self.s = session

    def open(self) -> None:
        s = self.s
        s.goto("/wp-admin/customize.php")
        s.page.wait_for_selector("#customize-controls", timeout=60_000)
        s.page.wait_for_function("() => window.wp && wp.customize && wp.customize.control", timeout=60_000)

    def read(self, setting: str):
        return self.s.page.evaluate("(id) => wp.customize(id) ? wp.customize(id).get() : null", setting)

    def set(self, setting: str, value: str) -> None:
        """Navigate to the control (like clicking through the panels) and type the value into it."""
        s, page = self.s, self.s.page
        page.evaluate("(id) => wp.customize.control(id).focus()", setting)
        control = page.locator(_control_id(setting))
        control.wait_for(state="visible", timeout=15_000)
        s.log.event("control", setting=setting, value=value)

        number = control.locator("input.et-pb-range-input")
        swatch = control.locator("button.wp-color-result")
        if number.count():
            number.fill(value)
            number.press("Tab")
        elif swatch.count():
            swatch.click()
            hex_input = control.locator("input.wp-color-picker, .wp-picker-input-wrap input[type=text]").first
            hex_input.wait_for(state="visible", timeout=5_000)
            hex_input.fill(value)
            hex_input.press("Enter")
            swatch.click()  # close the picker
        else:
            field = control.locator("[data-customize-setting-link]").first
            if field.evaluate("e => e.tagName") == "SELECT":
                field.select_option(value)
            else:
                field.fill(value)
                field.press("Tab")

        page.wait_for_timeout(500)
        got = self.read(setting)
        if _norm(got) != _norm(value):
            raise RuntimeError(f"{setting}: control shows {got!r} after typing {value!r}")

    def publish(self) -> None:
        s = self.s
        save = s.page.locator("#save")
        if save.is_disabled():
            raise RuntimeError("Publish button is disabled: the Customizer saw no change")
        s.log.event("click", target="#save", note="Publish Customizer")
        save.click()
        s.page.wait_for_function(
            "() => { const b = document.querySelector('#save'); return b && b.disabled && /published/i.test(b.value); }",
            timeout=60_000,
        )
        s.log.event("published")
