"""WordPress Pages screen actions, done through the list table like a human."""
from __future__ import annotations

import re

from ...browser.session import Session

NEW_DRAFT = "duplicate_post_new_draft"


def clone_as_draft(s: Session, page_id: int) -> int:
    """Hover the page row and click Duplicate Post's 'New Draft'. Returns the new draft's id."""
    resp = s.context.request.get(f"{s.site.url}/wp-json/wp/v2/pages/{page_id}?_fields=title")
    if not resp.ok:
        raise RuntimeError(f"Could not read page {page_id} title (HTTP {resp.status})")
    title = re.sub(r"<[^>]+>", "", resp.json()["title"]["rendered"])
    s.goto(f"/wp-admin/edit.php?post_type=page")
    search = s.page.locator("#post-search-input")
    search.fill(title)
    s.log.event("click", target="#search-submit", note=f"search pages for {title!r}")
    s.page.click("#search-submit")
    s.page.wait_for_load_state("networkidle")
    row = s.page.locator(f"#post-{page_id}")
    try:
        row.wait_for(timeout=10_000)
        row.hover()
        link = row.locator(".row-actions .edit_as_new_draft a")
        s.log.event("click", target=".edit_as_new_draft a", page_id=page_id, note="Duplicate Post: New Draft")
        link.click()
    except Exception:
        # Not on the first page of search results: use the admin bar link on the page itself.
        s.goto(f"/?page_id={page_id}")
        # Top-level "Duplicate Post" item links to the same New Draft action as its "Copy to a new draft" child.
        bar = s.page.locator(f"#wp-admin-bar-duplicate-post > a[href*='action={NEW_DRAFT}'][href*='post={page_id}&']").first
        bar.wait_for(timeout=15_000)
        s.log.event("click", target="admin bar 'Duplicate Post' (New Draft)", page_id=page_id, note="Duplicate Post: New Draft")
        bar.click()
    s.page.wait_for_url(re.compile(r"post\.php\?.*post=\d+"), timeout=60_000)
    new_id = int(re.search(r"post=(\d+)", s.page.url).group(1))
    if new_id == page_id:
        raise RuntimeError("Landed on the original page, not a new draft")
    s.log.event("cloned", source=page_id, draft=new_id)
    return new_id


def trash_draft(s: Session, page_id: int) -> None:
    """Move a draft to Trash from the Drafts list (reversible for 30 days). Never deletes permanently."""
    s.goto("/wp-admin/edit.php?post_type=page&post_status=draft")
    row = s.page.locator(f"#post-{page_id}")
    row.wait_for(timeout=15_000)
    if "Draft" not in row.inner_text():
        raise RuntimeError(f"Page {page_id} is not a draft; refusing to trash")
    row.hover()
    s.log.event("click", target=".row-actions .trash a", page_id=page_id, note="Move draft to Trash")
    row.locator(".row-actions .trash a").click()
    s.page.wait_for_load_state("networkidle")
    s.log.event("trashed", page_id=page_id)


def page_status(s: Session, page_id: int) -> dict:
    s.goto(f"/wp-admin/edit.php?post_type=page&post_status=draft")
    row = s.page.locator(f"#post-{page_id}")
    if not row.count():
        return {"id": page_id, "status": "not in drafts"}
    return {"id": page_id, "status": "draft", "title": row.locator(".row-title").inner_text()}
