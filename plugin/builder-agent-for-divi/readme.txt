=== Builder Agent for Divi ===
Contributors: rankdough
Tags: divi, claude, mcp, customizer, page builder
Requires at least: 6.0
Tested up to: 7.1
Requires PHP: 7.4
Stable tag: 0.1.0
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

Careful edits to a Divi 4 site: plans reviewed first, backups before every write, verification after. Connects to Claude as an MCP server.

== Description ==

Builder Agent for Divi is an agent that lives inside WordPress and an MCP server: connect it to Claude (claude.ai, Claude Desktop, Cowork or Claude Code) and ask Claude to make the change. Claude reads the site through the plugin's tools, proposes the plan or page spec, and the plugin validates, backs up, writes and records it.

* **Plan and apply.** Describe a change in plain English. Claude maps it to the highest rung of the edit ladder (Theme Options and Customizer first, Custom CSS last and only with approval), the plan is validated against the site's real values, shown to you, and only then applied. Front-end computed styles are measured in your browser before and after; rollback restores the old values.
* **Page rebuilds.** A page hand-coded inside one Code module is rebuilt as native Divi sections, rows and modules into a draft. The spec is validated (safe HTML only, images from the media library, every original passage present) before anything is saved.
* **Site-wide tools.** Header glow (Divi native gradient on dark page headers), role-aware restyle (colours and radii by role, content untouched), clone, go live.
* **Guard rails.** Every production write needs the site name typed as confirmation. Backups are taken into the run before every write. Only pages, Divi Library items and Divi's own option are ever written. Drafts are the only posts that can be trashed, and nothing is deleted permanently. Plugins, themes, users and WordPress settings are never touched.
* **Connect Claude.** The plugin exposes an MCP endpoint at /wp-json/wpba/v1/mcp with OAuth 2.1 sign-in (dynamic client registration, PKCE) or connection tokens. Add it as a custom connector and talk to your site.
* **WP-CLI.** `wp wpagent snapshot|plan|apply|rollback|clone|rebuild|golive|theme-css|header-glow|restyle|components|runs`.

Connected through MCP, Claude does the planning itself and no API key is needed on the site. The admin screen and WP-CLI can also call the Claude API directly: add your API key under Builder Agent > Settings or define `WPBA_ANTHROPIC_API_KEY` in wp-config.php. Every call's token usage and cost is recorded.

This plugin is an independent product of Rank Dough. Divi is a trademark of Elegant Themes, Inc.; Claude is a trademark of Anthropic, PBC. Neither company is affiliated with or endorses this plugin.

== Third-party services ==

* **Anthropic Claude API** (https://api.anthropic.com). Used only when you add an API key under Settings and run a plan or rebuild from the admin screen or WP-CLI. The task text and the site data read for it (Divi settings, page layouts, site profile) are sent to Anthropic. Terms: https://www.anthropic.com/legal/consumer-terms and https://www.anthropic.com/legal/privacy. Connected through MCP instead, no data leaves the site except in response to your own Claude client's requests.
* **Client ID metadata documents**: when an MCP client signs in with a client id that is an https URL, the plugin fetches that URL once to read the client's registered redirect URIs.

== Installation ==

1. Upload the plugin zip under Plugins > Add New > Upload Plugin, or copy the folder to wp-content/plugins/.
2. Activate it.
3. Open Builder Agent in the admin menu. Under Connect Claude, copy the MCP URL into Claude as a custom connector (or create a connection token). Fill in the site profile under Settings.

== Frequently Asked Questions ==

= Does it need an Anthropic API key? =

Not when Claude is connected through MCP: the Claude you talk to does the planning. A key is only needed to run plans and rebuilds from the admin screen or WP-CLI without Claude in the loop.

= What can it change on my site? =

Divi's Theme Options and Customizer values, page layouts (into drafts first), Divi Library items and Theme Options Custom CSS. It never installs or removes plugins or themes, never touches users or WordPress settings, and never deletes anything permanently.

= What happens before a change is written? =

The whole Theme Options record or the page layout is backed up into a run record, the plan is re-validated against the live values, and the site name must be given as confirmation. Caches are cleared afterwards, Divi's static CSS included.

= Does it work with Divi 5? =

No. Divi 5 uses a different builder and layout format. Divi 4 only.

= How do I disconnect Claude? =

Builder Agent > Connect Claude lists every token and connected app with a revoke link. Deactivating the plugin also closes the MCP endpoint.

== Changelog ==

= 0.1.0 =
* First release: MCP server with OAuth 2.1 and connection tokens, plan/apply/rollback, snapshot, clone, rebuild, go live, theme CSS, header glow, restyle, components, run log, REST API, WP-CLI.
