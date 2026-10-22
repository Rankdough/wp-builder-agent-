# Builder Agent for Divi: scope

## What it is

- A WordPress plugin that edits a Divi 4 site the way a careful human would: one change at a time, plan shown first,
  backup before every write, check afterwards, every run recorded.
- Controlled from your Claude account. The plugin is an MCP server; add it to claude.ai, Claude Desktop, Cowork or
  Claude Code once, then ask Claude to make the change. Claude does the thinking, the plugin does the writing.
- It never touches plugins, themes, users or WordPress settings. It can only write pages, Divi Library items and
  Divi's own settings record. Drafts are the only posts it can trash, and nothing is deleted permanently.

## How it works

| Step | What happens |
|---|---|
| Connect | Claude signs in through a WordPress consent screen (OAuth 2.1), or you paste a connection token. Every token belongs to an administrator and can be revoked under Builder Agent > Connect Claude. |
| Read | Claude calls `site_status`, `get_plan_context` or `get_page_dump`: Divi Theme Options and Customizer values, page layouts, the buttons on each page, global colours, the site profile. |
| Plan | Claude writes the plan using the edit ladder (Customizer first, Custom CSS last and only with your approval) and submits it with `propose_plan`. The plugin validates it against the live values and stores it as a run. Nothing is written. |
| Confirm | Claude shows you the plan. You give the site name as approval; Claude passes it as `confirm_site`. Without it every write is refused. |
| Back up | The full settings record or the page layout is saved into the run before anything changes. |
| Write | `apply_plan` writes the values, then clears every cache the site uses, Divi's static CSS included. |
| Verify | `verify_front` checks the front end as a visitor. Computed styles are measured in the admin screen's browser. `rollback` puts the old values back. |

Page rebuilds follow the same shape: `get_page_dump` + `get_spec_schema`, Claude writes the spec, `rebuild_page`
with `spec_only` validates it (safe HTML only, images from the media library, every original sentence present),
then writes it into a draft; `golive` copies the draft onto the live page.

## How to use it

1. Install the zip (`plugin/build.sh` builds it) and activate. Open **Builder Agent** in the admin menu.
2. Under **Connect Claude**, copy the MCP URL. In claude.ai or Claude Desktop: Customize > Connectors > Add custom
   connector, paste the URL, choose Sign in, approve on the WordPress screen. In Claude Code:
   `claude mcp add --transport http builder-agent-for-divi <url>` then `/mcp`. Or create a connection token and add it as
   the header `Authorization: Bearer <token>`.
3. Under **Settings**, fill in the site profile (brand colours, hero glow, dark header colours).
4. Ask Claude: "Take a snapshot, then make all buttons 6px rounded." Read the plan, confirm the site name, done.
5. For a page: "Rebuild the Shopify page as native Divi modules into a draft." Preview the draft, then "put it live".
6. The admin screen and `wp wpagent` do the same jobs without Claude in the loop (those need an API key in Settings
   for planning and rebuilds).

## Limits

- Divi 4 only. Divi 5 uses a different builder.
- Claude's connectors need a public HTTPS site. Local or http sites work only with Claude Code on the same machine.
- Long rebuilds can hit a host's PHP timeout.
- Tested on WordPress 7.1 with Divi's data shapes and the full MCP/OAuth flow; not yet run against a live Divi install.
