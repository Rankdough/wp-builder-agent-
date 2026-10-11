"""Builder adapter interface. Divi first; Elementor, Bricks and Gutenberg implement the same methods later."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..browser.session import Session

# Highest rung first. The planner must use the first rung that works and log why higher ones were skipped.
EDIT_LADDER = (
    "theme_options_or_customizer",
    "global_colours_or_presets",
    "theme_builder_template",
    "library_layout_or_global_module",
    "module_settings",
    "module_custom_css",  # last resort: explicit approval + logged reason
    "theme_custom_css",   # last resort: explicit approval + logged reason
)
CSS_RUNGS = {"module_custom_css", "theme_custom_css"}


class BuilderAdapter(ABC):
    name: str

    def __init__(self, session: Session):
        self.s = session

    @abstractmethod
    def detect(self) -> dict:
        """Read builder/theme name and version from wp-admin."""

    @abstractmethod
    def snapshot_admin(self) -> None:
        """Screenshot the builder's global settings screens, read-only."""

    @abstractmethod
    def export_backup(self) -> list[str]:
        """Export settings via the builder's own export UI. Returns saved file paths."""

    # M2+: inspect(task), plan_targets(task), apply(plan), verify(plan)
