"""Headed Chromium session: login, screenshots, and a read-only guard that blocks saves."""
from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, Request, Route

from ..config import USER_AGENT, Site
from ..runlog import RunLog

VIEWPORTS = {"desktop": {"width": 1440, "height": 900}, "mobile": {"width": 390, "height": 844}}

# admin-ajax actions that only read or export. Anything matching WRITE_HINTS is blocked in read-only mode.
WRITE_HINTS = re.compile(
    r"save|update|delete|remove|trash|import|upload|install|activate|deactivate|publish|reset|"
    r"customize_save|clear|insert|create|duplicate",
    re.I,
)
# Divi refreshes its own builder-definition cache when the Visual Builder opens; no site content changes.
SAFE_AJAX = {"heartbeat", "et_fb_update_builder_assets"}
EXPORT_AJAX = re.compile(r"portability.*export|export.*portability", re.I)
BLOCKED_POST_PATHS = ("/wp-admin/options.php", "/wp-admin/post.php", "/wp-admin/customize.php")
# Media > Add New uploads each file to this endpoint; allowed only when a plan includes MEDIA_UPLOAD.
MEDIA_UPLOAD = "media_upload"


class LoginError(Exception):
    pass


class Session:
    """read_only=True blocks every write. Write mode still blocks everything except `allowed_writes`
    (admin-ajax actions the approved plan needs), so a plan can never trigger an unplanned save."""

    def __init__(self, pw: Playwright, site: Site, log: RunLog, read_only: bool = True, headless: bool = False,
                 allowed_writes: frozenset[str] = frozenset()):
        self.site, self.log, self.read_only = site, log, read_only
        self.allowed_writes = frozenset() if read_only else allowed_writes
        self.browser: Browser = pw.chromium.launch(headless=headless, slow_mo=150)
        self.context: BrowserContext = self.browser.new_context(
            user_agent=USER_AGENT,
            viewport=VIEWPORTS["desktop"],
            accept_downloads=True,
        )
        self.context.route("**/*", self._guard)
        self.page: Page = self.context.new_page()
        self.blocked: list[dict] = []

    # --- read-only guard -------------------------------------------------
    def _guard(self, route: Route, request: Request) -> None:
        url = urlparse(request.url)
        same_site = url.netloc == urlparse(self.site.url).netloc
        if not same_site:
            return route.continue_()
        if request.method in ("GET", "HEAD", "OPTIONS"):
            # WordPress action links (duplicate, trash, delete, activate, logout) carry _wpnonce.
            query = parse_qs(url.query)
            if "_wpnonce" not in query:
                return route.continue_()
            action = (query.get("action") or [""])[0]
            bulk2 = (query.get("action2") or [""])[0]
            if action in ("", "-1") and bulk2 in ("", "-1"):
                return route.continue_()  # list-table search/filter form: no action chosen
            if action in ("", "-1"):
                action = bulk2
            post = (query.get("post") or [""])[0]
            if action in self.allowed_writes or f"{action}@{post}" in self.allowed_writes:
                self.log.event("write_allowed", action=action, method="GET", post=post)
                return route.continue_()
            entry = {"method": "GET", "path": url.path, "reason": f"action link '{action}' (post {post}) not in plan"}
            self.blocked.append(entry)
            self.log.event("blocked", **entry)
            return route.abort()

        reason = None
        if url.path.endswith("/wp-login.php"):
            return route.continue_()
        body = request.post_data or ""
        if "customize_changeset_uuid" in url.query + body and "/wp-admin/" not in url.path:
            return route.continue_()  # Customizer preview render; saving only happens via customize_save
        if url.path.endswith("/wp-admin/async-upload.php"):
            if MEDIA_UPLOAD in self.allowed_writes:
                self.log.event("write_allowed", action=MEDIA_UPLOAD)
                return route.continue_()
            reason = "media upload not in plan"
        elif url.path.endswith("/wp-admin/post.php") and f"post_edit@{self._post_id(body)}" in self.allowed_writes:
            # Classic edit screen (Update/Publish, Yoast box): allowed only for the one post in the plan.
            self.log.event("write_allowed", action="post_edit", post_id=self._post_id(body))
            return route.continue_()
        elif url.path.startswith(BLOCKED_POST_PATHS):
            reason = "write endpoint"
        elif "/wp-json/" in url.path or "rest_route" in url.query:
            reason = "REST write"
        elif url.path.endswith("/admin-ajax.php"):
            action = self._ajax_action(request)
            if action in self.allowed_writes:
                self.log.event("write_allowed", action=action)
                return route.continue_()
            # "action@123" allows the action only for post 123 (e.g. Visual Builder saves to one draft).
            post_ids = {w.split("@", 1)[1] for w in self.allowed_writes if w.startswith(action + "@")}
            if post_ids:
                pid = self._post_id(body)
                if pid in post_ids:
                    self.log.event("write_allowed", action=action, post_id=pid)
                    return route.continue_()
                reason = f"ajax write '{action}' for post {pid} not allowed (only {sorted(post_ids)})"
                entry = {"method": request.method, "path": url.path, "reason": reason}
                self.blocked.append(entry)
                self.log.event("blocked", **entry)
                return route.abort()
            if action in SAFE_AJAX or EXPORT_AJAX.search(action) or not WRITE_HINTS.search(action):
                self.log.event("post_allowed", action=action)
                return route.continue_()
            reason = f"ajax write action '{action}' not in plan"
        else:
            reason = "unknown POST"

        entry = {"method": request.method, "path": url.path, "reason": reason}
        self.blocked.append(entry)
        self.log.event("blocked", **entry)
        route.abort()

    @staticmethod
    def _post_id(body: str) -> str | None:
        form = parse_qs(body)
        # post_id (Visual Builder), post_ID (Quick Edit), id (media save-attachment, which also sends post_id=0)
        for key in ("post_id", "post_ID", "id"):
            if form.get(key) and form[key][0] != "0":
                return form[key][0]
        m = re.search(r'name="post_id"\r?\n\r?\n(\d+)', body)
        return m.group(1) if m else None

    @staticmethod
    def _ajax_action(request: Request) -> str:
        query = parse_qs(urlparse(request.url).query)
        if "action" in query:
            return query["action"][0]
        body = request.post_data or ""
        form = parse_qs(body)
        if "action" in form:
            return form["action"][0]
        match = re.search(r'name="action"\r?\n\r?\n([^\r\n]+)', body)
        return match.group(1) if match else ""

    # --- navigation ------------------------------------------------------
    def goto(self, path_or_url: str, wait: str = "networkidle", timeout: int = 60_000) -> None:
        url = path_or_url if path_or_url.startswith("http") else self.site.url + path_or_url
        self.log.event("goto", url=url)
        resp = self.page.goto(url, wait_until=wait, timeout=timeout)
        if resp is not None and resp.status >= 400:
            self.log.event("http_error", url=url, status=resp.status)

    def login(self, manual_wait_s: int = 180) -> None:
        self.goto("/wp-login.php", wait="domcontentloaded")
        self.page.fill("#user_login", self.site.user)
        self.page.fill("#user_pass", self.site.password)
        self.log.event("click", target="#wp-submit", note="log in")
        self.page.click("#wp-submit")
        try:
            self.page.wait_for_url(re.compile(r"/wp-admin/"), timeout=20_000)
        except Exception:
            # 2FA, captcha or a security plugin step: let the human finish it in the headed window.
            self.log.event("login_waiting_for_human", seconds=manual_wait_s)
            try:
                self.page.wait_for_url(re.compile(r"/wp-admin/"), timeout=manual_wait_s * 1000)
            except Exception as exc:
                self.screenshot("login-failed")
                raise LoginError("Did not reach wp-admin. See login-failed.png in the run folder.") from exc
        self.page.wait_for_selector("#wpadminbar", timeout=30_000)
        who = self.page.locator("#wp-admin-bar-my-account .display-name").first.inner_text(timeout=5_000)
        self.log.event("logged_in", display_name=who)

    # --- capture ---------------------------------------------------------
    def load_lazy(self) -> None:
        """Scroll to the bottom and back so lazy-loaded images render before a full-page capture."""
        self.page.evaluate(
            """async () => { for (let y = 0; y < document.body.scrollHeight; y += 600) {
                window.scrollTo(0, y); await new Promise(r => setTimeout(r, 120)); } window.scrollTo(0, 0); }"""
        )
        self.page.wait_for_timeout(800)

    def screenshot(self, name: str, full_page: bool = True) -> str:
        path = self.log.shots / f"{name}.png"
        self.page.screenshot(path=str(path), full_page=full_page)
        self.log.event("screenshot", file=f"screenshots/{path.name}")
        return str(path)

    def set_viewport(self, kind: str) -> None:
        self.page.set_viewport_size(VIEWPORTS[kind])

    def close(self) -> None:
        self.context.close()
        self.browser.close()
