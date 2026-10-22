# wp-builder-agent

A browser agent that edits WordPress sites built with **Divi 4** the way a careful human would: through Theme
Options, the Customizer, the Visual Builder and Divi's own import/export, not by pasting CSS or dumping pages into a
single Code module. It is built to leave sites editable and to add as little code debt as possible.

> Status: early. Tested on Divi 4.27.4 / WordPress 7.1, on Windows. Divi 5 has a different builder and is not supported.

## What it does

| Command | What it does | Writes to the site? |
|---|---|---|
| `snapshot` | Logs in, screenshots key pages and Divi screens, records Theme Options and Customizer values, exports Theme Builder | No |
| `plan "<task>"` | Inspects the site and asks Claude for a change plan using the edit ladder below | No |
| `apply` / `rollback` | Applies an approved Customizer plan through the Customizer's own controls, verifies it as a visitor, and can put the old values back | Yes |
| `clone <page_id>` | Makes a draft copy of a page with Duplicate Post's "New Draft" | Yes (draft) |
| `rebuild <path> <draft_id>` | Rebuilds a page that was hand-coded inside one Code module as native Divi sections and modules, into a draft | Yes (draft) |
| `golive <rebuild_dir> <live_id> <draft_id>` | Puts a verified rebuild onto the live page, then moves the draft to Trash | Yes |
| `header-glow` | Adds a native background gradient to every dark page header (dry run unless confirmed) | Yes |
| `theme-css <file> --reason "..."` | Appends a CSS block to Theme Options > Custom CSS. Last resort only | Yes |

Helper scripts in `scripts/` (page structure analysis, page comparison, layout export, audits) are read-only and take
`--site <name>`.

## How it stays safe on a live site

- **Edit ladder.** It uses the highest level that works: Theme Options/Customizer, then global presets, Theme Builder,
  Library layouts, module settings. Custom CSS is the last rung and needs an explicit reason.
- **Guard.** Every request the browser makes is checked. Read-only runs block every save. Write runs allow only the
  saves the plan needs, often scoped to a single post id. WordPress action links (trash, delete, activate, logout)
  are blocked unless planned.
- **Backups first.** Divi's own exports or a field-by-field record before any write; the Visual Builder import
  downloads Divi's backup of the page before replacing it.
- **Confirm the target.** Every production write needs `--confirm-site <name>`.
- **Verify as a visitor.** After a change: clear the page cache, reload logged out, and check computed styles or
  content. Rebuilds stop if any original text is missing.
- **Never** installs or deletes plugins, themes or core, deletes posts permanently, or touches Users or Settings.

## How page rebuilds work

1. The source page's content tree, CSS and JSON-LD are read from the front end.
2. Claude writes a **layout spec**: sections, rows, columns and native modules (Text, Button, Image, Blurb, Toggle)
   with their Divi design settings. JSON-LD goes in one data-only Code module.
3. Code validates the spec: safe HTML tags only, no `style`/`class` attributes, images from the site's media library,
   allowlisted component classes, every original passage present.
4. Code renders the spec to Divi's own layout format, and the agent imports it through the Visual Builder's
   Portability window into a draft, then saves the draft.

## Setup

```bash
git clone https://github.com/Rankdough/wp-builder-agent-.git wp-builder-agent
cd wp-builder-agent
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # macOS/Linux: .venv/bin/python
.venv/Scripts/python -m playwright install chromium
cp .env.example .env            # add your site URL, a WordPress login and your Anthropic API key
cp sites/example.json sites/mysite.json   # optional: design tokens and notes for your site
```

Use a dedicated WordPress user for the agent. Credentials stay in `.env`, which is git-ignored, and are typed into the
login form only. The browser runs visible by default so you can watch it; add `--headless` to hide it.

```bash
.venv/Scripts/python -m wpagent snapshot --site mysite
.venv/Scripts/python -m wpagent plan "make all buttons 6px rounded" --site mysite
.venv/Scripts/python -m wpagent header-glow --site mysite                         # dry run
.venv/Scripts/python -m wpagent header-glow --site mysite --confirm-site mysite   # apply
```

Every run writes a folder under `runs/` with a JSON-lines log of every click and request, screenshots and backups.

## WordPress plugin: Builder Agent for Divi

The same agent, packaged as a WordPress plugin in [`plugin/builder-agent-for-divi/`](plugin/builder-agent-for-divi/).

**Driven from your Claude account.** The plugin is an MCP server. Add its URL once as a custom connector in
claude.ai, Claude Desktop or Cowork (sign in through a WordPress consent screen, or paste a connection token as a
header), or in Claude Code with `claude mcp add --transport http builder-agent-for-divi https://<site>/wp-json/wpba/v1/mcp`.
From then on the Claude you talk to is the planner and the page designer: the tools hand it the same context and
schemas the CLI gave the API (`get_plan_context`, `get_spec_schema`, `get_page_dump`), it writes the plan or spec,
and the same validators check it before `apply_plan` or `rebuild_page` write anything. No API key is needed on the
site in this mode. Every write still needs the site name as confirmation, backs up first and is recorded as a run.

Authentication follows the MCP spec: OAuth 2.1 with dynamic client registration, PKCE, exact redirect-URI matching,
short-lived access tokens with rotating refresh tokens, and tokens bound to this endpoint; or plain connection
tokens made in the admin screen; or a WordPress Application Password. Running
inside WordPress it needs no browser: it reads and writes the option Divi's Theme Options and Customizer write,
works on page layouts in Divi's own shortcode format, and keeps every run (events, backups, plan, spec) as a
private `wpba_run` record you can open from the admin screen or `wp wpagent runs`.

| Python command | Plugin (admin screen tab / WP-CLI) | Notes |
|---|---|---|
| `snapshot` | Plan & apply > Snapshot / `wp wpagent snapshot` | Backs up Theme Options, global colours, Custom CSS and every page layout |
| `plan` | Plan & apply / `wp wpagent plan "<task>"` | Structured output from Claude, validated against the site's real values |
| `apply` / `rollback` | Plan & apply / `wp wpagent apply <run> --confirm-site=<host>` | Computed styles are measured in your browser (same-origin iframe) before and after |
| `clone` | Page rebuilds / `wp wpagent clone <id>` | Copies the page and its meta into a draft |
| `rebuild` | Page rebuilds / `wp wpagent rebuild <source> [draft]` | Reads the Code module from the stored layout; same spec validator and renderer, ported to PHP and cross-checked byte for byte |
| `golive` | Page rebuilds / `wp wpagent golive <live> <draft>` | Live layout backed up; draft goes to Trash |
| `theme-css` | CSS & components / `wp wpagent theme-css <file> --reason=...` | Marked block replaced in place, other CSS kept |
| `header-glow` | Site-wide / `wp wpagent header-glow` | Dry run unless `--confirm-site` |
| `restyle` | Site-wide / `wp wpagent restyle --theme=navy-red` | Dry run unless `--confirm-site`; pages whose visible text would change are skipped |
| `components` | CSS & components / `wp wpagent components [--install]` | Registry reads `assets/components/*.css` plus `uploads/wp-builder-agent/components/` |

**What stays the same.** The edit ladder, plan validation, the layout spec and its HTML allowlist, the component
registry, the restyle roles, the glow rule, the CSS merge rule, the "confirm the site name" rule and the no-delete
rule. The guard is now structural: the plugin has no code path to plugins, themes, users or WordPress settings.

**What changed.** No Playwright, no `.env`: the API key lives in Settings or `WPBA_ANTHROPIC_API_KEY` in
`wp-config.php`; the site profile lives in Settings. Caches are cleared through the plugins' own functions (Divi static
CSS, WP Fastest Cache, WP Rocket, W3TC, WP Super Cache, LiteSpeed, Autoptimize). Computed-style verification runs in
the admin page's browser, because that is the only place a computed style exists.

```bash
plugin/build.sh                       # lint, run tests/php, zip -> plugin/dist/builder-agent-for-divi.zip
php tests/php/run.php                 # the Python tests, ported (73 checks) + a render cross-check
# Integration (what was run before release): WP-CLI commands, REST, the MCP endpoint over curl, the full OAuth
# flow with a browser consent step, and a Playwright pass over the admin screen, on WordPress 7.1 + SQLite.
```

Install the zip under Plugins > Add New > Upload, activate, open **Builder Agent** in the admin menu. Tested on
WordPress 7.1 / PHP 8.3 with Divi's data shapes (the `et_divi` option, `_et_pb_use_builder` meta, `et_pb_layout`
library posts); Divi 4 itself is needed on the site for the layouts to render.

## Claude API costs

`plan` and `rebuild` call Claude (`claude-opus-5-5`). Each call prints its tokens and cost and adds them to
`runs/usage.jsonl` with a running total. A plan costs a few cents; rebuilding a long page about $0.30.

## Reusable components

`assets/components.css` is an optional, small component library for things Divi 4 has no native module for: pill
tags (`rd-pills`) and numbered steps with circles (`rd-steps`). Add it once with `theme-css`, then use the classes in
a Text module's Advanced tab.

## Known limits

- Divi 4 only, and selectors were mapped on 4.27.4.
- Module-by-module clicking in the Visual Builder is not built yet; rebuilds use Divi's Portability import.
- Divi's preview iframe overlaps its own toolbar, so some toolbar clicks are delivered to the control directly; each
  is logged.

## Licence

MIT. See [LICENSE](LICENSE).

Built by [Rank Dough](https://www.rankdough.com).
