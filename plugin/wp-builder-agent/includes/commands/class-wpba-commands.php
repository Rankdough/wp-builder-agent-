<?php
/**
 * The agent's commands, shared by the admin screen, the REST API and WP-CLI. Each returns an array result or
 * a WP_Error, and every write goes: guard -> backup -> write -> clear caches -> verify -> run log.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class WPBA_Commands {

	// --- snapshot (read-only) ------------------------------------------------------------------------

	public static function snapshot() {
		$log = WPBA_RunLog::start( 'snapshot', array( 'mode' => 'read-only' ) );
		$detect = WPBA_Divi::detect();
		$log->write_json( 'detect', $detect );
		$settings = WPBA_Divi::customizer_settings();
		$log->backup( 'et_divi-option', get_option( WPBA_Divi::OPTION, array() ) );
		$log->write_json( 'customizer-settings', $settings );
		$log->write_json( 'global-colors', WPBA_Divi::global_colors() );
		$log->backup( 'custom-css', WPBA_Divi::custom_css_get() );
		$pages = WPBA_Divi::list_pages();
		foreach ( $pages as $p ) {
			$log->backup( $p['id'] . '-content', (string) get_post_field( 'post_content', $p['id'] ) );
		}
		$log->write_json( 'pages', $pages );
		$plugins = array();
		if ( ! function_exists( 'get_plugins' ) ) {
			require_once ABSPATH . 'wp-admin/includes/plugin.php';
		}
		foreach ( get_plugins() as $file => $data ) {
			$plugins[] = array( 'file' => $file, 'name' => $data['Name'], 'version' => $data['Version'], 'active' => is_plugin_active( $file ) );
		}
		$log->write_json( 'plugins', $plugins );
		$log->close();
		return array(
			'run_id'   => $log->id,
			'detect'   => $detect,
			'settings' => count( $settings ),
			'pages'    => count( $pages ),
			'plugins'  => count( $plugins ),
			'note'     => 'Read-only: Theme Options, global colours, Custom CSS and every published page layout are backed up in this run.',
		);
	}

	// --- plan (read-only) ----------------------------------------------------------------------------

	/** Buttons on a page, from its stored layout: custom_button="on" means module-level styling. */
	private static function page_buttons( $content ) {
		$out = array();
		if ( preg_match_all( '/\[et_pb_button((?:\s+[a-z0-9_]+="[^"]*")*)\s*\]/', $content, $m ) ) {
			foreach ( $m[1] as $attrs ) {
				preg_match_all( '/([a-z0-9_]+)="([^"]*)"/', $attrs, $am, PREG_SET_ORDER );
				$a = array();
				foreach ( $am as $x ) {
					if ( 0 === strpos( $x[1], 'button_' ) || 'custom_button' === $x[1] ) {
						$a[ $x[1] ] = $x[2];
					}
				}
				$out[] = $a;
			}
		}
		return $out;
	}

	public static function plan( $task, array $plan_file = null ) {
		$task = trim( (string) $task );
		if ( '' === $task ) {
			return new WP_Error( 'wpba_task', 'Give the task in plain English.' );
		}
		$log = WPBA_RunLog::start( 'plan', array( 'task' => $task, 'mode' => 'read-only' ) );
		$customizer = WPBA_Divi::customizer_settings();
		$pages      = array();
		$buttons    = array();
		foreach ( WPBA_Divi::list_pages() as $p ) {
			$pages[]               = $p['path'];
			$buttons[ $p['path'] ] = self::page_buttons( (string) get_post_field( 'post_content', $p['id'] ) );
		}
		$context = array(
			'site_profile'              => WPBA_Settings::profile(),
			'pages_checked'             => $pages,
			'customizer_button_globals' => WPBA_Divi::button_globals( $customizer ),
			'customizer_settings'       => $customizer,
			'buttons_by_page'           => $buttons,
		);
		$log->write_json( 'context', $context );
		$log->write_json( 'customizer-before', $customizer );

		if ( null !== $plan_file ) {
			$plan         = WPBA_Plan_Schema::normalize( $plan_file );
			$plan['task'] = $task;
			$log->event( 'plan_loaded' );
		} else {
			$plan = WPBA_Planner::make_plan( $task, $context, $log->id );
			if ( is_wp_error( $plan ) ) {
				$log->fail( $plan->get_error_message() );
				return $plan;
			}
			$log->event( 'plan_created', array( 'feasible' => $plan['feasible'], 'rung' => $plan['rung'], 'changes' => count( $plan['changes'] ) ) );
		}
		$log->write_json( 'plan', $plan );
		$ok = WPBA_Plan_Schema::validate( $plan, $customizer, (bool) WPBA_Settings::get( 'allow_css' ) );
		if ( is_wp_error( $ok ) ) {
			$log->event( 'plan_rejected', array( 'error' => $ok->get_error_message() ) );
			$log->close( 'rejected' );
			return new WP_Error( 'wpba_plan', 'Plan rejected by validation: ' . $ok->get_error_message(), array( 'run_id' => $log->id, 'plan' => $plan ) );
		}
		$log->close( 'planned' );
		return array(
			'run_id' => $log->id,
			'plan'   => $plan,
			'usage'  => WPBA_Usage::recent( 1 ),
			'note'   => $plan['feasible'] ? 'Nothing has been changed. Apply this run after approval.' : 'Not feasible with the supported actions.',
		);
	}

	// --- apply / rollback ----------------------------------------------------------------------------

	public static function apply( $plan_run_id, $confirm_site, array $before = array() ) {
		$ok = WPBA_Guard::check_write( $confirm_site );
		if ( is_wp_error( $ok ) ) {
			return $ok;
		}
		$plan_run = WPBA_RunLog::open( $plan_run_id );
		if ( is_wp_error( $plan_run ) ) {
			return $plan_run;
		}
		$plan = $plan_run->read_json( 'plan' );
		if ( ! is_array( $plan ) ) {
			return new WP_Error( 'wpba_no_plan', "Run $plan_run_id holds no plan." );
		}
		if ( empty( $plan['feasible'] ) ) {
			return new WP_Error( 'wpba_infeasible', 'Plan is not feasible; nothing to apply.' );
		}
		$log = WPBA_RunLog::start( 'apply', array( 'plan_run' => (int) $plan_run_id, 'changes' => count( $plan['changes'] ) ) );
		$log->write_json( 'plan', $plan );
		$current = WPBA_Divi::customizer_settings();
		$ok      = WPBA_Plan_Schema::validate( $plan, $current, (bool) WPBA_Settings::get( 'allow_css' ) ); // values must still match what was approved
		if ( is_wp_error( $ok ) ) {
			$log->fail( $ok->get_error_message() );
			return new WP_Error( 'wpba_plan', 'Site changed since the plan was made: ' . $ok->get_error_message() );
		}
		$log->write_json( 'customizer-before', $current );
		if ( $before ) {
			$log->write_json( 'before-measurements', $before ); // what the front end showed before, so rollback can prove it is back
		}
		$changes = array();
		foreach ( $plan['changes'] as $c ) {
			$changes[ $c['setting'] ] = $c['new_value'];
		}
		$r = WPBA_Divi::customizer_set( $changes, $log );
		if ( is_wp_error( $r ) ) {
			$log->fail( $r->get_error_message() );
			return $r;
		}
		$cleared = WPBA_Cache::clear_all();
		$log->event( 'caches_cleared', array( 'cleared' => $cleared ) );
		$log->write_json( 'customizer-after', WPBA_Divi::customizer_settings() );
		$log->close( 'applied', array( 'verify_pending' => count( $plan['verify'] ) ) );
		return array(
			'run_id'  => $log->id,
			'applied' => $changes,
			'cleared' => $cleared,
			'verify'  => $plan['verify'],
			'note'    => 'Applied. Run the front-end verification from the admin screen (computed styles are measured in your browser). Rollback uses this run id.',
		);
	}

	public static function rollback( $apply_run_id, $confirm_site ) {
		$ok = WPBA_Guard::check_write( $confirm_site );
		if ( is_wp_error( $ok ) ) {
			return $ok;
		}
		$apply_run = WPBA_RunLog::open( $apply_run_id );
		if ( is_wp_error( $apply_run ) ) {
			return $apply_run;
		}
		$plan   = $apply_run->read_json( 'plan' );
		$backup = $apply_run->read_backup( 'et_divi-option' );
		if ( ! is_array( $plan ) || ! is_array( $backup ) ) {
			return new WP_Error( 'wpba_no_backup', "Run $apply_run_id holds no apply backup." );
		}
		$log = WPBA_RunLog::start( 'rollback', array( 'apply_run' => (int) $apply_run_id ) );
		// Put only the changed keys back (so later unrelated edits elsewhere in Theme Options survive).
		$changes = array();
		foreach ( array_reverse( $plan['changes'] ) as $c ) {
			$changes[ $c['setting'] ] = $c['old_value'];
		}
		$r = WPBA_Divi::customizer_set( $changes, $log );
		if ( is_wp_error( $r ) ) {
			$log->fail( $r->get_error_message() );
			return $r;
		}
		$cleared = WPBA_Cache::clear_all();
		$log->event( 'caches_cleared', array( 'cleared' => $cleared ) );
		$before = $apply_run->read_json( 'before-measurements' );
		$log->close( 'rolled_back' );
		return array(
			'run_id'   => $log->id,
			'restored' => $changes,
			'verify'   => is_array( $before ) ? $before : array(),
			'note'     => 'Old values restored and caches cleared.',
		);
	}

	// --- pages: clone, rebuild, golive ----------------------------------------------------------------

	public static function clone_page( $page_id, $confirm_site ) {
		$ok = WPBA_Guard::check_write( $confirm_site );
		if ( is_wp_error( $ok ) ) {
			return $ok;
		}
		$log = WPBA_RunLog::start( 'clone', array( 'page_id' => (int) $page_id ) );
		$id  = WPBA_Divi::clone_as_draft( $page_id, $log );
		if ( is_wp_error( $id ) ) {
			$log->fail( $id->get_error_message() );
			return $id;
		}
		$log->close();
		return array( 'run_id' => $log->id, 'draft_id' => $id, 'edit_url' => admin_url( 'post.php?post=' . $id . '&action=edit' ), 'note' => "Draft $id created from page $page_id." );
	}

	/**
	 * Rebuild a code-chunk page as native Divi modules. Without a draft id a new draft is created.
	 * spec_only: produce and validate the spec, save it to the run, touch nothing else.
	 */
	public static function rebuild( $source_id, $draft_id, $confirm_site, array $spec_file = null, $spec_only = false ) {
		if ( ! $spec_only ) {
			$ok = WPBA_Guard::check_write( $confirm_site );
			if ( is_wp_error( $ok ) ) {
				return $ok;
			}
		}
		$log  = WPBA_RunLog::start( 'rebuild', array( 'source' => (int) $source_id, 'draft' => (int) $draft_id, 'spec_only' => (bool) $spec_only ) );
		$dump = WPBA_Divi::page_dump( $source_id );
		if ( is_wp_error( $dump ) ) {
			$log->fail( $dump->get_error_message() );
			return $dump;
		}
		$log->write_json( 'source-dump', $dump );
		$colors     = WPBA_Divi::global_colors();
		$media_base = WPBA_Divi::media_base();
		if ( null !== $spec_file ) {
			$spec = $spec_file;
		} else {
			$spec = WPBA_Designer::design_page( $dump, $colors, $log->id, 1, WPBA_Settings::profile(), $media_base );
			if ( is_wp_error( $spec ) ) {
				$log->fail( $spec->get_error_message() );
				return $spec;
			}
		}
		$curly = false;
		foreach ( $dump['nodes'] as $n ) {
			if ( preg_match( '/[‘’“”]/u', (string) ( $n['text'] ?? '' ) ) ) {
				$curly = true;
			}
		}
		if ( ! $curly ) {
			$spec = WPBA_Spec::straighten_quotes( $spec );
		}
		$log->write_json( 'spec', $spec );
		$ok = WPBA_Spec::validate( $spec, $media_base );
		if ( is_wp_error( $ok ) ) {
			$log->fail( $ok->get_error_message() );
			return $ok;
		}
		$missing = WPBA_Spec::missing_text( $dump['nodes'], $spec );
		if ( $missing ) {
			$log->write_json( 'missing-text', $missing );
			$log->fail( 'original text missing from the rebuild' );
			return new WP_Error( 'wpba_missing_text', 'Stopped: original text missing from the rebuild.', array( 'run_id' => $log->id, 'missing' => $missing ) );
		}
		$layout = WPBA_Render::render( $spec );
		$counts = WPBA_Spec::count_modules( $spec );
		$log->event( 'spec_valid', array( 'sections' => count( $spec['sections'] ), 'modules' => $counts, 'notes' => count( $spec['notes'] ?? array() ) ) );
		$log->write_json( 'layout', array( 'shortcodes' => $layout ) );
		if ( $spec_only ) {
			$log->write_json( 'import-layout', json_decode( WPBA_Render::portability_json( $layout, (int) $draft_id, $colors ), true ) );
			$log->close( 'spec_only' );
			return array( 'run_id' => $log->id, 'modules' => $counts, 'notes' => $spec['notes'] ?? array(), 'spec' => $spec, 'note' => 'Spec only: nothing was written to the site.' );
		}
		if ( $draft_id ) {
			$r = WPBA_Divi::page_update_content( $draft_id, $layout, $log, 'draft' );
		} else {
			$r        = WPBA_Divi::create_draft_page( get_the_title( $source_id ) . ' (rebuild)', $layout, $log );
			$draft_id = $r;
		}
		if ( is_wp_error( $r ) ) {
			$log->fail( $r->get_error_message() );
			return $r;
		}
		$log->close( 'done', array( 'draft' => (int) $draft_id ) );
		return array(
			'run_id'      => $log->id,
			'draft_id'    => (int) $draft_id,
			'modules'     => $counts,
			'notes'       => $spec['notes'] ?? array(),
			'preview_url' => add_query_arg( 'preview', 'true', get_permalink( (int) $draft_id ) ),
			'edit_url'    => admin_url( 'post.php?post=' . (int) $draft_id . '&action=edit' ),
			'note'        => "Rebuilt into draft $draft_id. Preview it, then go live.",
		);
	}

	public static function golive( $live_id, $draft_id, $confirm_site ) {
		$ok = WPBA_Guard::check_write( $confirm_site );
		if ( is_wp_error( $ok ) ) {
			return $ok;
		}
		$log   = WPBA_RunLog::start( 'golive', array( 'live' => (int) $live_id, 'draft' => (int) $draft_id ) );
		$draft = get_post( (int) $draft_id );
		$words = $draft ? WPBA_Restyle::visible_text( $draft->post_content ) : '';
		if ( '' === trim( $words ) ) {
			$log->fail( 'draft has no visible text' );
			return new WP_Error( 'wpba_empty', "Draft $draft_id has no visible content; refusing to go live." );
		}
		$r = WPBA_Divi::golive( $live_id, $draft_id, $log );
		if ( is_wp_error( $r ) ) {
			$log->fail( $r->get_error_message() );
			return $r;
		}
		$cleared = WPBA_Cache::clear_all();
		$log->event( 'caches_cleared', array( 'cleared' => $cleared ) );
		$log->close();
		return array( 'run_id' => $log->id, 'live_id' => (int) $live_id, 'url' => get_permalink( (int) $live_id ), 'note' => "Live page $live_id now holds the draft's layout; draft $draft_id is in Trash (restorable for 30 days)." );
	}

	// --- theme-css (last resort) ----------------------------------------------------------------------

	public static function theme_css( $css, $reason, $confirm_site ) {
		if ( '' === trim( (string) $reason ) ) {
			return new WP_Error( 'wpba_reason', 'CSS is a last resort: give a reason why no native Divi setting can do this.' );
		}
		$ok = WPBA_Guard::check_write( $confirm_site );
		if ( is_wp_error( $ok ) ) {
			return $ok;
		}
		$block  = trim( (string) $css );
		$log    = WPBA_RunLog::start( 'theme-css', array( 'reason' => $reason ) );
		$before = WPBA_Divi::custom_css_get();
		if ( false !== strpos( $before, $block ) ) {
			$log->close( 'noop' );
			return array( 'run_id' => $log->id, 'note' => 'This exact block is already present; nothing to do.' );
		}
		$target = WPBA_Theme_CSS::merge_block( $before, $block );
		$log->event( 'rung', array( 'rung' => 'theme_custom_css', 'reason' => $reason ) );
		$r = WPBA_Divi::custom_css_set( $target, $log );
		if ( is_wp_error( $r ) ) {
			$log->fail( $r->get_error_message() );
			return $r;
		}
		$after   = WPBA_Divi::custom_css_get();
		$saved   = trim( $after ) === trim( $target );
		$cleared = WPBA_Cache::clear_all();
		$log->event( 'verify', array( 'saved_as_intended' => $saved, 'replaced_previous' => false !== strpos( $before, WPBA_Theme_CSS::BLOCK_START ) ) );
		$live = null;
		if ( preg_match( '/\.(rd-[a-z0-9-]+)/', $block, $m ) ) {
			$found = WPBA_Verify::front_contains( '/', '.' . $m[1] );
			$live  = is_wp_error( $found ) ? null : $found;
			$log->event( 'verify_front', array( 'css_in_page' => $live, 'class' => $m[1] ) );
		}
		$log->close( $saved ? 'done' : 'failed' );
		return array( 'run_id' => $log->id, 'saved' => $saved, 'css_in_page' => $live, 'cleared' => $cleared, 'note' => $saved ? 'Custom CSS saved.' : 'Custom CSS did not save as intended.' );
	}

	// --- header-glow ----------------------------------------------------------------------------------

	public static function header_glow( $confirm_site = null, array $only = array() ) {
		$live = $confirm_site && ! is_wp_error( WPBA_Guard::check_write( $confirm_site ) );
		if ( $confirm_site && ! $live ) {
			return WPBA_Guard::check_write( $confirm_site );
		}
		$glow = WPBA_Settings::hero_glow();
		if ( ! $glow ) {
			return new WP_Error( 'wpba_profile', 'Set design_tokens.hero_glow in the site profile first.' );
		}
		$dark    = WPBA_Settings::dark_header_colors() ?: WPBA_Header_Glow::DARK_DEFAULT;
		$log     = WPBA_RunLog::start( $live ? 'header-glow' : 'header-glow-dry', array( 'only' => $only ) );
		$results = array();
		foreach ( WPBA_Divi::list_pages( $only, $only ? array( 'publish', 'draft' ) : 'publish' ) as $t ) {
			$raw = (string) get_post_field( 'post_content', $t['id'] );
			list( $new, $status ) = WPBA_Header_Glow::add_glow( $raw, $glow, $dark );
			$row = array( 'id' => $t['id'], 'path' => $t['path'], 'status' => $status );
			if ( 'change' !== $status ) {
				$results[] = $row;
				$log->event( 'page', $row );
				continue;
			}
			if ( $live ) {
				$r = WPBA_Divi::page_update_content( $t['id'], $new, $log );
				if ( is_wp_error( $r ) ) {
					$row['status'] = 'error: ' . $r->get_error_message();
					$results[]     = $row;
					$log->event( 'page', $row );
					break;
				}
				WPBA_Cache::clear_all();
				$found           = WPBA_Verify::front_contains( $t['path'], 'radial-gradient' );
				$row['verified'] = true === $found;
				$results[]       = $row;
				$log->event( 'page', $row );
				if ( ! $row['verified'] ) {
					$log->event( 'stopped', array( 'reason' => 'glow not visible', 'page' => $t['path'] ) );
					break;
				}
			} else {
				$row['status'] = 'would change';
				$results[]     = $row;
				$log->event( 'page', $row );
			}
		}
		$log->write_json( 'results', $results );
		$log->close();
		$n = 0;
		foreach ( $results as $r ) {
			if ( false !== strpos( $r['status'], 'change' ) ) {
				$n++;
			}
		}
		return array( 'run_id' => $log->id, 'live' => $live, 'results' => $results, 'changed' => $n, 'note' => $live ? "$n page(s) changed." : "Dry run: $n page(s) would change. Confirm the site name to apply." );
	}

	// --- restyle --------------------------------------------------------------------------------------

	public static function restyle( $theme_name, $confirm_site = null, array $only = array() ) {
		$themes = WPBA_Restyle::themes();
		if ( ! isset( $themes[ $theme_name ] ) ) {
			return new WP_Error( 'wpba_theme', 'Unknown theme. Available: ' . implode( ', ', array_keys( $themes ) ) );
		}
		$live = $confirm_site && ! is_wp_error( WPBA_Guard::check_write( $confirm_site ) );
		if ( $confirm_site && ! $live ) {
			return WPBA_Guard::check_write( $confirm_site );
		}
		$theme   = $themes[ $theme_name ];
		$log     = WPBA_RunLog::start( $live ? 'restyle' : 'restyle-dry', array( 'theme' => $theme_name, 'only' => $only ) );
		$results = array();
		foreach ( WPBA_Divi::list_pages( $only, $only ? array( 'publish', 'draft' ) : 'publish' ) as $t ) {
			$raw = (string) get_post_field( 'post_content', $t['id'] );
			list( $new, $counts ) = WPBA_Restyle::apply_theme( $raw, $theme );
			$row = array( 'id' => $t['id'], 'path' => $t['path'], 'changes' => array_sum( $counts ), 'counts' => $counts );
			if ( $new === $raw ) {
				$row['status'] = 'no change';
			} elseif ( WPBA_Restyle::visible_text( $new ) !== WPBA_Restyle::visible_text( $raw ) ) {
				$row['status'] = 'skip: visible text would change';
			} elseif ( $live ) {
				$r             = WPBA_Divi::page_update_content( $t['id'], $new, $log );
				$row['status'] = is_wp_error( $r ) ? 'error: ' . $r->get_error_message() : 'changed';
			} else {
				$row['status'] = 'would change';
			}
			$results[] = $row;
			$log->event( 'page', $row );
		}
		if ( $live ) {
			WPBA_Cache::clear_all();
		}
		$log->write_json( 'results', $results );
		$log->close();
		return array( 'run_id' => $log->id, 'live' => $live, 'theme' => $theme_name, 'results' => $results, 'note' => $live ? 'Applied.' : 'Dry run. Confirm the site name to apply.' );
	}

	// --- components -----------------------------------------------------------------------------------

	public static function components() {
		return array( 'catalogue' => WPBA_Components::catalogue(), 'bundle' => WPBA_Components::bundle(), 'site_folder' => WPBA_Components::site_folder() );
	}

	/** Install (or update) the component bundle in Theme Options > Custom CSS. */
	public static function install_components( $confirm_site ) {
		return self::theme_css( WPBA_Components::bundle(), 'component library: pill tags, numbered steps and KPI cards have no native Divi module', $confirm_site );
	}
}
