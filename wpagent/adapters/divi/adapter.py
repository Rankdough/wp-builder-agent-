"""Divi 4 adapter. M1: detect, read-only admin snapshots, backups via Divi's own Portability export."""
from __future__ import annotations

from playwright.sync_api import Locator, TimeoutError as PWTimeout

from ..base import BuilderAdapter

SCREENS = {
    "theme-options": "/wp-admin/admin.php?page=et_divi_options",
    "theme-builder": "/wp-admin/admin.php?page=et_theme_builder",
    "customizer": "/wp-admin/customize.php",
    "divi-library": "/wp-admin/edit.php?post_type=et_pb_layout",
    "plugins": "/wp-admin/plugins.php",
}

# Divi 4.27.4 Portability selectors, confirmed on a live site, Oct 2026.
# Theme Options and Customizer use the classic core modal; Theme Builder uses its React modal.
CORE_PORTABILITY = {
    "trigger": ("[data-et-core-modal*='portability']", "a.et-core-portability-link"),
    "modal": (".et-core-modal-overlay.et-core-active",),
    "export_tab": ("a[href='#et-core-portability-export']",),
    "export_button": ("a[data-et-core-portability-export]",),
}
PORTABILITY = {
    "theme-options": CORE_PORTABILITY,
    "customizer": CORE_PORTABILITY,
    "theme-builder": {
        "trigger": ("button[data-tip='Portability']",),
        "modal": (".et-tb-portability-modal",),
        "export_tab": ("button[role='tab'][data-key='export']",),
        "export_button": (".et-tb-branded-modal__actions .et-common-button--primary",),
    },
}


class DiviAdapter(BuilderAdapter):
    name = "divi"

    def __init__(self, session):
        super().__init__(session)
        self.selectors_used: dict[str, str] = {}
        # Leaving the Visual Builder can raise "unsaved changes"; accepting means leave without saving.
        self.s.page.on("dialog", lambda d: d.accept())

    # --- detect ----------------------------------------------------------
    def detect(self) -> dict:
        self.s.goto("/wp-admin/themes.php")
        info = self.s.page.evaluate(
            """() => {
                const t = (window._wpThemeSettings && window._wpThemeSettings.themes) || [];
                const a = t.find(x => x.active) || {};
                return {theme: a.name || null, version: a.version || null, parent: a.parent || null};
            }"""
        )
        wp_version = self.s.page.evaluate(
            "() => (document.querySelector('#footer-upgrade')||{}).innerText || null"
        )
        info["wp_footer"] = wp_version
        self.s.log.event("detect", **info)
        return info

    # --- snapshots -------------------------------------------------------
    def snapshot_admin(self) -> None:
        s = self.s
        s.set_viewport("desktop")
        for name, path in SCREENS.items():
            s.goto(path)
            if name == "customizer":
                s.page.wait_for_selector("#customize-controls", timeout=60_000)
                s.page.wait_for_timeout(3_000)
            if name == "theme-builder":
                s.page.wait_for_timeout(4_000)  # React app renders after load
            s.screenshot(f"admin-{name}", full_page=name not in ("customizer", "theme-builder"))
            if name == "theme-options":
                tabs = s.page.locator("#epanel-mainmenu a, #et_pb_epanel_mainmenu a").all_inner_texts()
                s.log.event("theme_options_tabs", tabs=[t.strip() for t in tabs if t.strip()])
            if name == "plugins":
                s.log.write_json("plugins.json", self._read_plugins())

    def _read_plugins(self) -> list[dict]:
        return self.s.page.evaluate(
            """() => [...document.querySelectorAll('#the-list tr[data-plugin]')].map(r => ({
                slug: r.dataset.slug || null,
                file: r.dataset.plugin,
                name: (r.querySelector('.plugin-title strong')||{}).innerText || null,
                version: ((r.querySelector('.plugin-version-author-uri')||{}).innerText||'').split('|')[0].replace('Version','').trim() || null,
                active: r.classList.contains('active'),
                update_available: !!document.querySelector(`tr.plugin-update-tr[data-plugin="${r.dataset.plugin}"]`),
            }))"""
        )

    def snapshot_visual_builder(self, path: str) -> None:
        s = self.s
        sep = "&" if "?" in path else "?"
        s.goto(f"{path}{sep}et_fb=1&PageSpeed=off", wait="load", timeout=90_000)
        try:
            s.page.wait_for_selector("#et-fb-app, #et-fb-app-frame, .et-fb-page-settings-bar", timeout=60_000)
            # The app mounts before the layout loads; wait until no preloader/spinner is visible.
            s.page.wait_for_function(
                """() => ![...document.querySelectorAll('[class*=preload],[class*=loader],[id*=loading]')]
                    .some(e => e.offsetParent && e.getBoundingClientRect().width > 0)""",
                timeout=60_000,
            )
            s.page.wait_for_timeout(2_000)
            self.selectors_used["visual_builder_ready"] = "#et-fb-app + no visible preloader"
        except PWTimeout:
            loaders = s.page.evaluate(
                """() => [...document.querySelectorAll('[class*=preload],[class*=loader],[id*=loading]')]
                    .filter(e => e.offsetParent).map(e => e.id || e.className).slice(0, 5)"""
            )
            s.log.event("vb_not_ready", path=path, visible_loaders=loaders)
        s.screenshot("admin-visual-builder", full_page=False)

    # --- backups via Divi Portability -------------------------------------
    def export_backup(self) -> list[str]:
        """Theme Builder: Divi's own export (no save involved). Theme Options and Customizer: Divi's
        export re-saves settings first, so on live we record every field read-only instead."""
        saved = []
        steps = (
            ("theme-options", self._record_theme_options),
            ("theme-builder", lambda: self._portability_export("theme-builder")),
            ("customizer", self._record_customizer),
        )
        if self.s.site.is_staging:
            steps = tuple((label, lambda l=label: self._portability_export(l)) for label in SCREENS if label in PORTABILITY)
        for label, step in steps:
            try:
                saved.append(step())
            except Exception as exc:  # keep going; M1 reports which exports need selector work
                self.s.log.event("export_failed", screen=label, error=str(exc)[:300])
                self.s.screenshot(f"export-failed-{label}", full_page=False)
        return saved

    def export_backup_for_write(self) -> list[str]:
        """Before a write run: Divi's own exports where the plan's write allowlist covers them
        (Customizer export re-publishes unchanged settings via customize_save; Theme Builder has no save).
        Theme Options stays a read-only record so save_epanel never needs to be allowed."""
        saved = []
        steps = (
            ("theme-options", self._record_theme_options),
            ("theme-builder", lambda: self._portability_export("theme-builder")),
            ("customizer", lambda: self._portability_export("customizer")),
        )
        for label, step in steps:
            try:
                saved.append(step())
            except Exception as exc:
                self.s.log.event("export_failed", screen=label, error=str(exc)[:300])
                raise RuntimeError(f"Backup failed for {label}; no changes made") from exc
        return saved

    def _record_theme_options(self) -> str:
        """Screenshot every Theme Options tab and save every form field's value. No Save click."""
        s = self.s
        s.goto(SCREENS["theme-options"])
        fields = s.page.evaluate(
            """() => [...document.querySelectorAll('#epanel input, #epanel select, #epanel textarea')]
                .filter(e => e.name && !['submit', 'button'].includes(e.type) && !/nonce|_wp_http_referer/.test(e.name))
                .map(e => ({name: e.name, type: e.type,
                            value: e.type === 'checkbox' ? e.checked : e.value}))"""
        )
        if not fields:
            raise RuntimeError("No Theme Options fields found under #epanel")
        tabs = s.page.locator("#epanel-mainmenu a")
        for i in range(tabs.count()):
            tab = tabs.nth(i)
            name = tab.inner_text().strip().lower() or f"tab{i}"
            tab.click()  # tab switch only, no save
            s.page.wait_for_timeout(500)
            s.screenshot(f"backup-theme-options-{name}")
        path = s.log.write_json("backup/theme-options-fields.json", fields)
        s.log.event("backup_saved", screen="theme-options", file="backup/theme-options-fields.json", fields=len(fields))
        return str(path)

    def _record_customizer(self) -> str:
        """Save every Customizer setting value from the Customizer's own JS state. No Publish click."""
        s = self.s
        s.goto(SCREENS["customizer"])
        s.page.wait_for_selector("#customize-controls", timeout=60_000)
        s.page.wait_for_function("() => window.wp && wp.customize && wp.customize.settings", timeout=60_000)
        values = s.page.evaluate(
            """() => { const out = {}; wp.customize.each((setting, id) => { out[id] = setting.get(); }); return out; }"""
        )
        path = s.log.write_json("backup/customizer-settings.json", values)
        s.log.event("backup_saved", screen="customizer", file="backup/customizer-settings.json", settings=len(values))
        return str(path)

    def _first_visible(self, candidates, key: str, scope=None, timeout: int = 15_000) -> Locator:
        root = scope or self.s.page
        deadline = self.s.page.evaluate("Date.now()") + timeout
        while self.s.page.evaluate("Date.now()") < deadline:
            for sel in candidates:
                loc = root.locator(sel).first
                if loc.count() and loc.is_visible():
                    self.selectors_used[key] = sel
                    return loc
            self.s.page.wait_for_timeout(500)
        raise RuntimeError(f"No visible match for {key}: {candidates}")

    def _portability_export(self, label: str) -> str:
        s = self.s
        s.goto(SCREENS[label])
        if label == "customizer":
            s.page.wait_for_selector("#customize-controls", timeout=60_000)
        if label == "theme-builder":
            s.page.wait_for_timeout(4_000)

        sel = PORTABILITY[label]
        trigger = self._first_visible(sel["trigger"], f"{label}.portability_trigger")
        s.log.event("click", target=self.selectors_used[f"{label}.portability_trigger"], note="open Portability")
        trigger.click()

        modal = self._first_visible(sel["modal"], f"{label}.portability_modal")
        try:
            tab = self._first_visible(sel["export_tab"], f"{label}.export_tab", scope=modal, timeout=3_000)
            tab.click()
        except RuntimeError:
            pass  # Export is already the active tab

        button = self._first_visible(sel["export_button"], f"{label}.export_button", scope=modal)
        s.log.event("click", target=self.selectors_used[f"{label}.export_button"], screen=label,
                    note="Divi Portability export (read-only)")
        with s.page.expect_download(timeout=120_000) as dl_info:
            button.click()
        download = dl_info.value
        dest = s.log.backup / f"{label}-{download.suggested_filename}"
        download.save_as(dest)
        s.log.event("backup_saved", screen=label, file=f"backup/{dest.name}", bytes=dest.stat().st_size)
        return str(dest)
