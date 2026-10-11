"""wpagent CLI: snapshot (read-only), plan (read-only), apply and rollback (production writes)."""
from __future__ import annotations

import argparse
import sys

from .config import ConfigError, load_site


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wpagent", description="Edit WordPress through the builder UI, like a human.")
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name: str, help_: str):
        p = sub.add_parser(name, help=help_)
        p.add_argument("--site", required=True, help="Site name, reads SITE_<NAME>_* from .env")
        p.add_argument("--headless", action="store_true", help="Hide the browser (default: visible)")
        return p

    add("snapshot", "Read-only: log in, screenshot pages and Divi screens, back up settings")

    p = add("plan", "Read-only: inspect the site and produce a change plan for a task")
    p.add_argument("task", help='Plain-English task, e.g. "make all buttons #ff8a3d with 6px radius"')
    p.add_argument("--plan-file", help="Use a hand-written plan JSON instead of calling Claude")

    p = add("apply", "Back up, apply an approved plan through the UI, verify")
    p.add_argument("plan_dir", help="Run folder produced by `plan`")
    p.add_argument("--confirm-site", help="Type the site name to confirm a production write")

    p = add("rollback", "Restore the values changed by an `apply` run, then verify")
    p.add_argument("apply_dir", help="Run folder produced by `apply`")
    p.add_argument("--confirm-site", help="Type the site name to confirm a production write")

    p = add("clone", "Duplicate Post 'New Draft' of a page (production write, draft only)")
    p.add_argument("page_id", type=int)
    p.add_argument("--confirm-site", help="Type the site name to confirm a production write")

    p = add("rebuild", "Rebuild a code-chunk page as native Divi modules inside a draft")
    p.add_argument("source_path", help="Front-end path of the page to rebuild, e.g. /tools/x/")
    p.add_argument("draft_id", type=int)
    p.add_argument("--confirm-site", help="Type the site name to confirm a production write")
    p.add_argument("--spec-file", help="Reuse a saved spec.json instead of calling Claude")
    p.add_argument("--spec-only", action="store_true", help="Produce and validate the spec; don't touch the site")

    p = add("golive", "Put a verified rebuild onto the live page and trash the draft")
    p.add_argument("rebuild_dir")
    p.add_argument("live_id", type=int)
    p.add_argument("draft_id", type=int)
    p.add_argument("--confirm-site", help="Type the site name to confirm a production write")

    p = add("theme-css", "Append a CSS block to Divi Theme Options > Custom CSS (last resort, logged)")
    p.add_argument("css_file")
    p.add_argument("--reason", required=True, help="Why no native Divi setting can do this (logged)")
    p.add_argument("--confirm-site", help="Type the site name to confirm a production write")

    p = add("header-glow", "Add the hero glow to every dark Divi page header (dry run unless --confirm-site)")
    p.add_argument("--confirm-site", help="Type the site name to apply on production")
    p.add_argument("--only", type=int, nargs="*", help="Limit to these page ids")

    args = parser.parse_args(argv)
    try:
        site = load_site(args.site)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2

    if args.command == "snapshot":
        from .commands import snapshot
        return snapshot.run(site, headless=args.headless)
    if args.command == "plan":
        from .commands import plan
        return plan.run(site, args.task, plan_file=args.plan_file, headless=args.headless)

    if args.command == "header-glow":
        from .commands import header_glow
        return header_glow.run(site, args.confirm_site, only=args.only, headless=args.headless)
    if args.command == "theme-css":
        from .commands import theme_css
        return theme_css.run(site, args.css_file, args.confirm_site, reason=args.reason, headless=args.headless)
    if args.command == "golive":
        from .commands import golive
        return golive.run(site, args.rebuild_dir, args.live_id, args.draft_id, args.confirm_site,
                          headless=args.headless)
    if args.command == "rebuild":
        from .commands import rebuild
        return rebuild.run(site, args.source_path, args.draft_id, args.confirm_site, spec_file=args.spec_file,
                           spec_only=args.spec_only, headless=args.headless)
    if args.command == "clone":
        from .commands import clone
        return clone.run(site, args.page_id, args.confirm_site, headless=args.headless)

    from .commands import apply as apply_cmd
    try:
        if args.command == "apply":
            return apply_cmd.apply(site, args.plan_dir, args.confirm_site, headless=args.headless)
        return apply_cmd.rollback(site, args.apply_dir, args.confirm_site, headless=args.headless)
    except apply_cmd.ConfirmError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
