"""Divi 4 Visual Builder actions through its own UI: page Portability export/import and Save Draft.
Selectors confirmed on Divi 4.27.4 (live site, Oct 2026)."""
from __future__ import annotations

import re
from pathlib import Path

from ...browser.session import Session

APP_FRAME = "#et-fb-app-frame"
SETTINGS_BAR = ".et-fb-page-settings-bar"
PORTABILITY_BTN = "button:has(.et-fb-icon--portability)"
MODAL = ".et-fb-tooltip-modal--portability"
EXPORT_TAB, IMPORT_TAB = f"{MODAL} a.modules_all", f"{MODAL} a.modules_library"
ACTION_BTN = f"{MODAL} a.et-fb-save-library-button"
FILE_INPUT = f"{MODAL} input.et-fb-import-file"
CHECKBOX = MODAL + " input[name='et_fb_multiple_checkboxes[{i}]']"  # 0 replace, 1 backup, 2 presets
SAVE_DRAFT = "button.et-fb-button--save-draft"


class VisualBuilder:
    def __init__(self, session: Session, page_id: int):
        self.s, self.page_id = session, page_id
        self.s.page.on("dialog", lambda d: d.accept())

    def ui_click(self, locator, label: str) -> None:
        """Click a builder control. Divi's preview iframe overlaps its own toolbar, so when a real
        mouse click is intercepted, deliver the click event to that same control (logged)."""
        try:
            locator.click(timeout=3_000)
            self.s.log.event("click", target=label)
        except Exception:
            locator.dispatch_event("click")
            self.s.log.event("click", target=label, via="dispatch (iframe overlaps toolbar)")

    def open(self) -> None:
        s = self.s
        s.goto(f"/?page_id={self.page_id}&et_fb=1&PageSpeed=off", wait="load", timeout=90_000)
        s.page.wait_for_selector(APP_FRAME, timeout=60_000)
        s.page.wait_for_selector(PORTABILITY_BTN, state="attached", timeout=60_000)
        s.page.wait_for_timeout(5_000)

    def open_portability(self, tab: str) -> None:
        s = self.s
        if not s.page.locator(MODAL).is_visible():
            self.ui_click(s.page.locator(PORTABILITY_BTN).first, "Portability")
            s.page.locator(MODAL).wait_for(timeout=15_000)
        self.ui_click(s.page.locator(EXPORT_TAB if tab == "export" else IMPORT_TAB).first, f"{tab} tab")
        s.page.wait_for_timeout(800)

    def export_layout(self, dest: Path) -> Path:
        s = self.s
        self.open_portability("export")
        with s.page.expect_download(timeout=120_000) as dl:
            self.ui_click(s.page.locator(ACTION_BTN).filter(has_text="Export").first, "Export Divi Builder Layout")
        dl.value.save_as(dest)
        s.log.event("exported", file=str(dest), bytes=dest.stat().st_size)
        return dest

    def import_layout(self, src: Path, backup_dir: Path) -> Path:
        """Import a layout JSON with 'Replace Existing Content' and 'Download Backup Before Importing' on,
        'Import Presets' off. Returns the downloaded backup file."""
        s = self.s
        self.open_portability("import")
        s.page.locator(FILE_INPUT).set_input_files(str(src))
        s.log.event("file_chosen", file=src.name)
        for i, want in ((0, True), (1, True), (2, False)):
            box = s.page.locator(CHECKBOX.format(i=i))
            if box.is_checked() != want:
                self.ui_click(box, f"checkbox {i} -> {want}")
        with s.page.expect_download(timeout=120_000) as dl:
            self.ui_click(s.page.locator(ACTION_BTN).filter(has_text="Import").first, "Import Divi Builder Layout")
        backup = backup_dir / f"pre-import-backup-{dl.value.suggested_filename}"
        dl.value.save_as(backup)
        s.log.event("backup_saved", file=str(backup))
        s.page.locator(MODAL).wait_for(state="hidden", timeout=120_000)
        s.page.wait_for_timeout(5_000)
        s.log.event("imported", file=src.name)
        return backup

    def save_published(self) -> None:
        """Save changes to an already-published page. Refuses if the button says Publish (i.e. a draft)."""
        s = self.s
        btn = s.page.locator("button.et-fb-button--publish").first
        label = (btn.get_attribute("data-tip") or btn.inner_text() or "").strip()
        if label != "Save":
            raise RuntimeError(f"Expected a 'Save' button on a published page, found {label!r}; not clicking")
        self.ui_click(btn, "Save (published page)")
        s.page.wait_for_timeout(6_000)
        s.log.event("saved_published", page_id=self.page_id)

    def save_draft(self) -> None:
        """Save Draft only. Never Publish."""
        s = self.s
        btn = s.page.locator(SAVE_DRAFT)
        if not btn.count():
            raise RuntimeError("No 'Save Draft' button: page may not be a draft; refusing to Publish")
        self.ui_click(btn.first, "Save Draft")
        s.page.wait_for_timeout(6_000)
        s.log.event("saved_draft", page_id=self.page_id)


SAVE_LIBRARY_BTN = "button:has(.et-fb-icon--save)"
LIBRARY_ACTION = "et_fb_save_layout"  # the one write Save to Library makes (Divi 4.27.4)


def save_to_library(vb: VisualBuilder, name: str) -> None:
    """Page settings bar > Save to Library: type the layout name, click Save To Library. Needs LIBRARY_ACTION allowed.
    Saves the whole page as one library layout (not each section/row/module separately)."""
    s = vb.s
    vb.ui_click(s.page.locator(SAVE_LIBRARY_BTN).first, "Save to Library")
    modal = s.page.locator(".et-fb-tooltip-modal, .et-fb-modal").filter(has=s.page.locator("a.et-fb-save-library-button")).first
    modal.wait_for(timeout=15_000)
    modal.locator("input.et-fb-settings-option-input").first.fill(name)
    with s.page.expect_response(lambda r: "admin-ajax.php" in r.url and r.request.method == "POST"
                                and LIBRARY_ACTION in (r.request.post_data or ""), timeout=60_000) as resp:
        vb.ui_click(modal.locator("a.et-fb-save-library-button").first, "Save To Library")
    body = resp.value.text()
    m = re.search(r'"post_id":(\d+)', body)  # Divi replies with the new library layout's id
    ok = resp.value.ok and bool(m)
    s.log.event("saved_to_library", name=name, ok=ok, status=resp.value.status, layout_id=m and int(m.group(1)))
    if not ok:
        raise RuntimeError(f"Save to Library failed: HTTP {resp.value.status} {resp.value.text()[:200]}")
