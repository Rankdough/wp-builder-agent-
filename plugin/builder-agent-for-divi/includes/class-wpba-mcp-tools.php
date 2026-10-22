<?php
/**
 * The MCP tool catalogue. Each tool is a thin wrapper over WPBA_Commands / WPBA_Divi, with an input schema
 * Claude sees and annotations that tell the client which calls are read-only.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class WPBA_MCP_Tools {

	private static function s( $desc, $type = 'string' ) {
		return array( 'type' => $type, 'description' => $desc );
	}

	private static function confirm() {
		return self::s( 'The site name exactly as site_status reports it, given by the user as approval for this production write. Omit it for a dry run where the tool offers one.' );
	}

	private static function ids() {
		return array( 'type' => 'array', 'items' => array( 'type' => 'integer' ), 'description' => 'Limit to these page ids (blank = all published pages)' );
	}

	private static function tool( $name, $title, $desc, array $props, array $required, $read_only, $destructive = false ) {
		return array(
			'name'        => $name,
			'title'       => $title,
			'description' => $desc,
			'inputSchema' => array( 'type' => 'object', 'properties' => $props ? $props : new stdClass(), 'required' => $required ),
			'annotations' => array( 'title' => $title, 'readOnlyHint' => $read_only, 'destructiveHint' => $destructive, 'idempotentHint' => $read_only, 'openWorldHint' => false ),
		);
	}

	public static function definitions() {
		return array(
			self::tool( 'site_status', 'Site status', 'WordPress, theme and Divi versions, the site name used for write confirmations, settings summary, Claude usage total, restyle themes available. Call this first.', array(), array(), true ),
			self::tool( 'snapshot', 'Snapshot (read-only backup)', 'Back up Theme Options, global colours, Custom CSS and every published page layout into one run record. Nothing is changed.', array(), array(), true ),
			self::tool( 'list_pages', 'List pages', 'Pages with id, title, status, URL, path and whether the Divi builder is on.', array( 'status' => self::s( 'publish, draft or any (default: publish and draft)' ) ), array(), true ),
			self::tool( 'get_page_layout', 'Get page layout', 'The raw Divi shortcode layout of a page, as stored.', array( 'page_id' => self::s( 'Page id', 'integer' ) ), array( 'page_id' ), true ),
			self::tool( 'get_page_dump', 'Dump a Code-module page', 'For a page hand-coded inside a Divi Code module: its content tree (tag, class, text, href, src, alt), original CSS and JSON-LD. Use before writing a rebuild spec.', array( 'page_id' => self::s( 'Page id', 'integer' ) ), array( 'page_id' ), true ),
			self::tool( 'get_plan_context', 'Get planning context', 'Everything needed to write a change plan: the edit ladder, the plan JSON schema, every Divi Customizer setting with its current value, button globals, the buttons on each page (custom_button=on means a Customizer change will not reach it), and the site profile.', array( 'setting_prefix' => self::s( 'Only settings whose id starts with this, e.g. et_divi[all_buttons_ (default: all)' ) ), array(), true ),
			self::tool( 'propose_plan', 'Propose a plan (validated, nothing written)', 'Submit a change plan you wrote from get_plan_context. It is validated against the live values (unknown settings, wrong old_value, code-like values and CSS rungs without approval are rejected) and stored as a plan run. Returns the run id to pass to apply_plan after the user approves.', array( 'task' => self::s( 'The task in the user\'s words' ), 'plan' => array( 'type' => 'object', 'description' => 'Plan object matching the schema from get_plan_context' ) ), array( 'task', 'plan' ), true ),
			self::tool( 'plan_with_api', 'Plan with the site\'s own Claude API key', 'Alternative to writing the plan yourself: the plugin asks Claude via the API key configured in its settings. Fails if no key is set.', array( 'task' => self::s( 'Plain-English task' ) ), array( 'task' ), true ),
			self::tool( 'apply_plan', 'Apply a plan', 'Apply an approved plan run: validates the site still matches, backs up the whole Theme Options record, writes the values, clears caches. Returns the apply run id (needed for rollback) and the verify checks to confirm on the front end.', array( 'run_id' => self::s( 'Plan run id from propose_plan or plan_with_api', 'integer' ), 'confirm_site' => self::confirm() ), array( 'run_id', 'confirm_site' ), false ),
			self::tool( 'rollback', 'Roll back an apply', 'Put back the old values of an apply_plan run and clear caches.', array( 'run_id' => self::s( 'Apply run id', 'integer' ), 'confirm_site' => self::confirm() ), array( 'run_id', 'confirm_site' ), false ),
			self::tool( 'get_spec_schema', 'Get the rebuild spec schema', 'The PageSpec JSON schema, the design rules, the registered component classes with usage notes, the image URL base, a sample of media library image URLs and the Divi global colours. Use with get_page_dump to write a rebuild spec.', array(), array(), true ),
			self::tool( 'rebuild_page', 'Rebuild a page from a spec', 'Validate a spec you wrote (safe HTML only, images from the media library, every original passage present), render it to Divi\'s layout format and save it into a draft. With spec_only=true nothing is written: use that first. Omit draft_id to create a new draft.', array( 'source_id' => self::s( 'Page to rebuild from', 'integer' ), 'spec' => array( 'type' => 'object', 'description' => 'PageSpec object' ), 'draft_id' => self::s( 'Existing draft to write into', 'integer' ), 'spec_only' => self::s( 'Validate and render only', 'boolean' ), 'confirm_site' => self::confirm() ), array( 'source_id', 'spec' ), false ),
			self::tool( 'clone_page', 'Clone a page into a draft', 'Copy a page and its meta into a new draft.', array( 'page_id' => self::s( 'Page id', 'integer' ), 'confirm_site' => self::confirm() ), array( 'page_id', 'confirm_site' ), false ),
			self::tool( 'golive', 'Put a draft live', 'Copy a verified draft\'s layout onto the live page (old layout backed up), then move the draft to Trash.', array( 'live_id' => self::s( 'Live page id', 'integer' ), 'draft_id' => self::s( 'Draft id', 'integer' ), 'confirm_site' => self::confirm() ), array( 'live_id', 'draft_id', 'confirm_site' ), false, true ),
			self::tool( 'header_glow', 'Header glow', 'Add the site profile\'s hero glow (Divi native circular gradient) to the first section of every page with a dark header. Dry run unless confirm_site is given.', array( 'only' => self::ids(), 'confirm_site' => self::confirm() ), array(), false ),
			self::tool( 'restyle', 'Restyle by role', 'Change colours and radii by role (backgrounds, borders, text, icons, button radius) across pages; content never changes. Dry run unless confirm_site is given.', array( 'theme' => self::s( 'Theme name from site_status' ), 'only' => self::ids(), 'confirm_site' => self::confirm() ), array( 'theme' ), false ),
			self::tool( 'theme_css', 'Theme Custom CSS (last resort)', 'Save a CSS block into Divi Theme Options > Custom CSS. Bottom rung of the edit ladder: needs a reason. A block starting with "/* wp-builder-agent: reusable components" replaces the earlier one; other CSS is kept.', array( 'css' => self::s( 'CSS block' ), 'reason' => self::s( 'Why no native Divi setting can do this (logged)' ), 'confirm_site' => self::confirm() ), array( 'css', 'reason', 'confirm_site' ), false ),
			self::tool( 'install_components', 'Install the component library', 'Write the plugin\'s component CSS bundle (rd-pills, rd-steps, rd-kpi ...) into Theme Options > Custom CSS as one marked block.', array( 'confirm_site' => self::confirm() ), array( 'confirm_site' ), false ),
			self::tool( 'list_components', 'List components', 'Registered component classes with usage notes, and the bundle CSS.', array(), array(), true ),
			self::tool( 'get_site_profile', 'Get the site profile', 'Design tokens, hero glow, dark header colours and component notes.', array(), array(), true ),
			self::tool( 'update_site_profile', 'Update the site profile', 'Replace the site profile object (design tokens, hero_glow, dark_header_colors, components).', array( 'profile' => array( 'type' => 'object', 'description' => 'Full profile object' ) ), array( 'profile' ), false ),
			self::tool( 'verify_front', 'Check the front end', 'Fetch a front-end path as a logged-out visitor (cache-busted) and report whether a string appears in the HTML or in Divi\'s static CSS files. Computed styles cannot be measured here; use the admin screen for those.', array( 'path' => self::s( 'Path starting with /' ), 'needle' => self::s( 'String to look for, e.g. radial-gradient or .rd-pills' ) ), array( 'path', 'needle' ), true ),
			self::tool( 'list_runs', 'List runs', 'Recent run records with command and status.', array( 'limit' => self::s( 'Max runs (default 30)', 'integer' ) ), array(), true ),
			self::tool( 'get_run', 'Get a run', 'A run in full: events, files (plan, spec, results) and the names of its backups.', array( 'run_id' => self::s( 'Run id', 'integer' ) ), array( 'run_id' ), true ),
		);
	}

	public static function exists( $name ) {
		foreach ( self::definitions() as $t ) {
			if ( $t['name'] === $name ) {
				return true;
			}
		}
		return false;
	}

	public static function call( $name, array $a ) {
		$i = function ( $k ) use ( $a ) { return isset( $a[ $k ] ) ? (int) $a[ $k ] : 0; };
		$s = function ( $k ) use ( $a ) { return isset( $a[ $k ] ) ? (string) $a[ $k ] : ''; };
		$c = function () use ( $a ) { return isset( $a['confirm_site'] ) && '' !== trim( (string) $a['confirm_site'] ) ? (string) $a['confirm_site'] : null; };
		$only = isset( $a['only'] ) && is_array( $a['only'] ) ? array_map( 'intval', $a['only'] ) : array();
		switch ( $name ) {
			case 'site_status':
				$st = WPBA_Rest::status();
				$st['confirm_site_value'] = $st['site'];
				$st['api_key']            = WPBA_Settings::key_source();
				$st['restyle_themes']     = array_keys( WPBA_Restyle::themes() );
				$st['mcp_resource']       = WPBA_OAuth::resource_uri();
				return $st;
			case 'snapshot':
				return WPBA_Commands::snapshot();
			case 'list_pages':
				$status = $s( 'status' );
				return WPBA_Divi::list_pages( array(), $status && 'any' !== $status ? $status : array( 'publish', 'draft' ) );
			case 'get_page_layout':
				$raw = WPBA_Divi::page_content( $i( 'page_id' ) );
				return is_wp_error( $raw ) ? $raw : array( 'page_id' => $i( 'page_id' ), 'bytes' => strlen( $raw ), 'layout' => $raw );
			case 'get_page_dump':
				return WPBA_Divi::page_dump( $i( 'page_id' ) );
			case 'get_plan_context':
				$customizer = WPBA_Divi::customizer_settings();
				$prefix     = $s( 'setting_prefix' );
				if ( $prefix ) {
					$customizer = array_filter( $customizer, function ( $k ) use ( $prefix ) { return 0 === strpos( $k, $prefix ); }, ARRAY_FILTER_USE_KEY );
				}
				$buttons = array();
				foreach ( WPBA_Divi::list_pages() as $p ) {
					$buttons[ $p['path'] ] = WPBA_Commands::page_buttons( (string) get_post_field( 'post_content', $p['id'] ) );
				}
				return array(
					'instructions'              => WPBA_Planner::SYSTEM,
					'edit_ladder'               => WPBA_Plan_Schema::EDIT_LADDER,
					'css_rungs_allowed'         => (bool) WPBA_Settings::get( 'allow_css' ),
					'plan_schema'               => WPBA_Plan_Schema::json_schema(),
					'customizer_button_globals' => WPBA_Divi::button_globals( $customizer ),
					'customizer_settings'       => $customizer,
					'buttons_by_page'           => $buttons,
					'site_profile'              => WPBA_Settings::profile(),
				);
			case 'propose_plan':
				if ( ! isset( $a['plan'] ) || ! is_array( $a['plan'] ) ) {
					return new WP_Error( 'wpba_plan', 'plan must be an object' );
				}
				return WPBA_Commands::plan( $s( 'task' ), $a['plan'] );
			case 'plan_with_api':
				return WPBA_Commands::plan( $s( 'task' ) );
			case 'apply_plan':
				return WPBA_Commands::apply( $i( 'run_id' ), $s( 'confirm_site' ) );
			case 'rollback':
				return WPBA_Commands::rollback( $i( 'run_id' ), $s( 'confirm_site' ) );
			case 'get_spec_schema':
				return array(
					'instructions'         => WPBA_Designer::SYSTEM,
					'spec_schema'          => WPBA_Spec::json_schema(),
					'components_catalogue' => WPBA_Components::catalogue(),
					'image_src_base'       => WPBA_Divi::media_base(),
					'media_library'        => array_slice( WPBA_Divi::media_urls(), 0, 200 ),
					'site_global_colors'   => WPBA_Divi::global_colors(),
					'site_profile'         => WPBA_Settings::profile(),
				);
			case 'rebuild_page':
				if ( ! isset( $a['spec'] ) || ! is_array( $a['spec'] ) ) {
					return new WP_Error( 'wpba_spec', 'spec must be an object' );
				}
				return WPBA_Commands::rebuild( $i( 'source_id' ), $i( 'draft_id' ), $s( 'confirm_site' ), $a['spec'], ! empty( $a['spec_only'] ) );
			case 'clone_page':
				return WPBA_Commands::clone_page( $i( 'page_id' ), $s( 'confirm_site' ) );
			case 'golive':
				return WPBA_Commands::golive( $i( 'live_id' ), $i( 'draft_id' ), $s( 'confirm_site' ) );
			case 'header_glow':
				return WPBA_Commands::header_glow( $c(), $only );
			case 'restyle':
				return WPBA_Commands::restyle( $s( 'theme' ), $c(), $only );
			case 'theme_css':
				return WPBA_Commands::theme_css( $s( 'css' ), $s( 'reason' ), $s( 'confirm_site' ) );
			case 'install_components':
				return WPBA_Commands::install_components( $s( 'confirm_site' ) );
			case 'list_components':
				return WPBA_Commands::components();
			case 'get_site_profile':
				return WPBA_Settings::profile();
			case 'update_site_profile':
				return WPBA_Settings::update_profile( isset( $a['profile'] ) && is_array( $a['profile'] ) ? $a['profile'] : null );
			case 'verify_front':
				$found = WPBA_Verify::front_contains( $s( 'path' ), $s( 'needle' ) );
				return is_wp_error( $found ) ? $found : array( 'path' => $s( 'path' ), 'needle' => $s( 'needle' ), 'found' => $found );
			case 'list_runs':
				return WPBA_RunLog::list_runs( $i( 'limit' ) ?: 30 );
			case 'get_run':
				return WPBA_RunLog::detail( $i( 'run_id' ) );
		}
		return new WP_Error( 'wpba_tool', "Unknown tool $name" );
	}
}
