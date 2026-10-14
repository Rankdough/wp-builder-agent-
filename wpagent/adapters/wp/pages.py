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


def quick_edit(s: Session, page_id: int, title: str, slug: str) -> None:
    """Pages list > Quick Edit: change a draft's title and slug (saves via admin-ajax inline-save@<id>)."""
    s.goto("/wp-admin/edit.php?post_type=page&post_status=draft")
    row = s.page.locator(f"#post-{page_id}")
    row.wait_for(timeout=15_000)
    row.hover()
    s.log.event("click", target=".editinline", page_id=page_id, note="Quick Edit")
    row.locator("button.editinline").click()
    editor = s.page.locator(f"#edit-{page_id}")
    editor.locator("input[name=post_title]").fill(title)
    editor.locator("input[name=post_name]").fill(slug)
    s.log.event("click", target="Quick Edit Update", page_id=page_id, title=title, slug=slug)
    editor.locator("button.save").click()
    s.page.locator(f"#post-{page_id} .row-title").filter(has_text=title).wait_for(timeout=30_000)
    s.log.event("quick_edited", page_id=page_id, title=title, slug=slug)


def set_seo_and_publish(s: Session, page_id: int, seo_title: str, meta_desc: str, keyphrase: str | None = None,
                        publish: bool = True) -> None:
    """Classic edit screen: type into Yoast's SEO title / meta description (and focus keyphrase), check Yoast
    took the values, then click Publish (or Save Draft). Needs post_edit@<page_id> in the allowed writes."""
    s.goto(f"/wp-admin/post.php?post={page_id}&action=edit")
    s.page.wait_for_timeout(3000)
    fields = (("#yoast-google-preview-title-metabox", "#yoast_wpseo_title", seo_title),
              ("#yoast-google-preview-description-metabox", "#yoast_wpseo_metadesc", meta_desc))
    for editor, hidden, value in fields:
        box = s.page.locator(f"{editor} [contenteditable=true]").first
        if not box.count():
            box = s.page.locator(editor)
        box.click()
        s.page.keyboard.press("Control+A")
        s.page.keyboard.press("Delete")
        s.page.keyboard.type(value, delay=5)
        s.page.wait_for_timeout(800)
        got = s.page.locator(hidden).input_value()
        if got.strip() != value:
            raise RuntimeError(f"Yoast field {hidden} holds {got!r}, expected {value!r}")
        s.log.event("yoast_field_set", field=hidden)
    if keyphrase:
        kp = s.page.locator("#focus-keyword-input-metabox")
        kp.fill(keyphrase)
        s.log.event("yoast_field_set", field="focus keyphrase")
    button = "#publish" if publish else "#save-post"
    s.log.event("click", target=button, page_id=page_id)
    s.page.locator(button).click()
    s.page.wait_for_url(re.compile(rf"post={page_id}.*message="), timeout=60_000)
    s.log.event("published" if publish else "saved", page_id=page_id)


def create_draft_page(s: Session, title: str, content: str) -> int:
    """Pages > Add New (classic editor): type the title, paste the content into the Text tab, click Save Draft.
    The new page's id is read from the screen first and is the only post this session may save."""
    s.goto("/wp-admin/post-new.php?post_type=page")
    page_id = int(s.page.locator("#post_ID").input_value())
    s.allowed_writes = s.allowed_writes | {f"post_edit@{page_id}"}
    s.page.locator("#title").fill(title)
    if s.page.locator("#content-html").count():
        s.log.event("click", target="#content-html", note="editor Text tab")
        s.page.locator("#content-html").click()
    s.page.locator("textarea#content").fill(content)
    s.log.event("click", target="#save-post", page_id=page_id, note="Save Draft")
    s.page.locator("#save-post").click()
    try:
        s.page.wait_for_url(re.compile(rf"post={page_id}.*message="), timeout=60_000)
    except Exception:
        # Seen on rankdough.com (Divi 4.27.4): WordPress autosaved the new page and the Save Draft click sent no
        # request. Accept it only if the page really is a draft holding the content; otherwise fail loudly.
        resp = s.context.request.get(f"{s.site.url}/wp-json/wp/v2/pages/{page_id}?context=edit&_fields=status,content",
                                     headers={"X-WP-Nonce": s.page.evaluate("wpApiSettings.nonce")})
        saved = resp.json() if resp.ok else {}
        if saved.get("status") != "draft" or len(saved.get("content", {}).get("raw", "")) != len(content):
            raise RuntimeError(f"Save Draft did not complete for page {page_id}: HTTP {resp.status}, {str(saved)[:200]}")
        s.log.event("saved_by_autosave", page_id=page_id)
    s.log.event("draft_created", page_id=page_id)
    return page_id
