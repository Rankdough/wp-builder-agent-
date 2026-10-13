"""Media > Add New: upload an image through WordPress's own uploader, then set its alt text the way a person would
(Media Library > attachment details). Needs MEDIA_UPLOAD and save-attachment@<id> in the session's allowed writes."""
from __future__ import annotations

import re
from pathlib import Path

from ...browser.session import Session

ALLOWED_TYPES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MAX_BYTES = 5 * 1024 * 1024


def check_file(path: Path) -> None:
    if path.suffix.lower() not in ALLOWED_TYPES:
        raise ValueError(f"{path.name}: only {sorted(ALLOWED_TYPES)} images are uploaded")
    if path.stat().st_size > MAX_BYTES:
        raise ValueError(f"{path.name}: larger than 5 MB, resize it first")


def find_existing(s: Session, path: Path) -> dict | None:
    """Same file name already in the library: reuse it instead of uploading a duplicate."""
    resp = s.context.request.get(f"{s.site.url}/wp-json/wp/v2/media?search={path.stem}&_fields=id,source_url")
    for m in resp.json() if resp.ok else []:
        if re.search(rf"/{re.escape(path.stem)}(-\d+)?\.{path.suffix[1:]}$", m["source_url"]):
            return m
    return None


def upload_image(s: Session, path: Path) -> dict:
    """Returns {"id", "source_url"} of the new (or existing) attachment."""
    check_file(path)
    existing = find_existing(s, path)
    if existing:
        s.log.event("media_exists", file=path.name, id=existing["id"])
        return existing
    s.goto("/wp-admin/media-new.php")
    s.log.event("file_chosen", file=path.name, note="Media > Add New")
    s.page.locator("#plupload-upload-ui input[type=file]").set_input_files(str(path))
    item = s.page.locator("#media-items .media-item").last
    item.locator("a.edit-attachment").wait_for(timeout=90_000)
    href = item.locator("a.edit-attachment").get_attribute("href")
    att_id = int(re.search(r"post=(\d+)", href).group(1))
    resp = s.context.request.get(f"{s.site.url}/wp-json/wp/v2/media/{att_id}?_fields=id,source_url")
    media = resp.json()
    s.log.event("uploaded", file=path.name, id=att_id, url=media["source_url"])
    return media


def set_alt_text(s: Session, att_id: int, alt: str) -> None:
    """Media Library grid > attachment details > Alternative Text (saves on change via save-attachment)."""
    s.goto(f"/wp-admin/upload.php?item={att_id}")
    box = s.page.locator("#attachment-details-two-column-alt-text, .attachment-details textarea[data-setting=alt]").first
    box.wait_for(timeout=30_000)
    box.fill(alt)
    box.press("Tab")
    s.page.wait_for_timeout(2000)
    s.log.event("alt_text_set", id=att_id)
