=== WP Builder Agent ===
Contributors: rankdough
Tags: divi, customizer, page builder, claude, agent
Requires at least: 6.0
Tested up to: 7.1
Requires PHP: 7.4
Stable tag: 0.1.0
License: MIT
License URI: https://opensource.org/licenses/MIT

Edits a Divi 4 site the way a careful human would: plans reviewed before they are applied, backups before every write, verification after.

== Description ==

WP Builder Agent is the WordPress-plugin form of the wp-builder-agent CLI. It runs inside WordPress, so it needs no browser automation: it reads and writes the same option Divi's Theme Options and Customizer write, works on page layouts in Divi's own shortcode format, and keeps a run record of everything it reads, decides and writes.

* **Plan and apply.** Describe a change in plain English. Claude maps it to the highest rung of the edit ladder (Theme Options and Customizer first, Custom CSS last and only with approval), the plan is validated against the site's real values, shown to you, and only then applied. Front-end computed styles are measured in your browser before and after; rollback restores the old values.
* **Page rebuilds.** A page hand-coded inside one Code module is rebuilt as native Divi sections, rows and modules into a draft. The spec is validated (safe HTML only, images from the media library, every original passage present) before anything is saved.
* **Site-wide tools.** Header glow (Divi native gradient on dark page headers), role-aware restyle (colours and radii by role, content untouched), clone, go live.
* **Guard rails.** Every production write needs the site name typed as confirmation. Backups are taken into the run before every write. Only pages, Divi Library items and Divi's own option are ever written. Drafts are the only posts that can be trashed, and nothing is deleted permanently. Plugins, themes, users and WordPress settings are never touched.
* **WP-CLI.** `wp wpagent snapshot|plan|apply|rollback|clone|rebuild|golive|theme-css|header-glow|restyle|components|runs`.

Planning and rebuilds call the Claude API (Anthropic). Add your API key under Builder Agent > Settings or define `WPBA_ANTHROPIC_API_KEY` in wp-config.php. Every call's token usage and cost is recorded.

== Installation ==

1. Upload the plugin zip under Plugins > Add New > Upload Plugin, or copy the folder to wp-content/plugins/.
2. Activate it.
3. Open Builder Agent in the admin menu, add your Anthropic API key under Settings, and fill in the site profile.

== Changelog ==

= 0.1.0 =
* First release: plan/apply/rollback, snapshot, clone, rebuild, go live, theme CSS, header glow, restyle, components, run log, REST API, WP-CLI.
