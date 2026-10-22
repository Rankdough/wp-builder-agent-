<?php
/**
 * WP-CLI: `wp wpagent <command>`, the same commands as the Python CLI agent, without a browser.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class WPBA_CLI {

	private function print( $result ) {
		if ( is_wp_error( $result ) ) {
			$data = $result->get_error_data();
			if ( is_array( $data ) && ! empty( $data['missing'] ) ) {
				foreach ( $data['missing'] as $m ) {
					WP_CLI::line( '  - ' . mb_substr( $m, 0, 120 ) );
				}
			}
			WP_CLI::error( $result->get_error_message() );
		}
		WP_CLI::line( json_encode( $result, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) );
	}

	private function read_json_file( $path ) {
		if ( ! $path ) {
			return null;
		}
		$data = json_decode( (string) file_get_contents( $path ), true );
		if ( ! is_array( $data ) ) {
			WP_CLI::error( "Could not read JSON from $path" );
		}
		return $data;
	}

	/**
	 * Read-only: back up Theme Options, global colours, Custom CSS and every page layout into a run.
	 *
	 * @when after_wp_load
	 */
	public function snapshot( $args, $assoc ) {
		$this->print( WPBA_Commands::snapshot() );
	}

	/**
	 * Read-only: ask Claude for a change plan.
	 *
	 * ## OPTIONS
	 *
	 * <task>
	 * : Plain-English task, e.g. "make all buttons #ff8a3d with 6px radius"
	 *
	 * [--plan-file=<path>]
	 * : Use a hand-written plan JSON instead of calling Claude
	 *
	 * @when after_wp_load
	 */
	public function plan( $args, $assoc ) {
		$r = WPBA_Commands::plan( $args[0], $this->read_json_file( $assoc['plan-file'] ?? null ) );
		if ( ! is_wp_error( $r ) ) {
			$this->print_plan( $r['plan'] );
			WP_CLI::line( $r['note'] );
			if ( $r['plan']['feasible'] ) {
				WP_CLI::line( 'To apply after approval: wp wpagent apply ' . $r['run_id'] . ' --confirm-site=' . WPBA_Guard::site_name() );
			}
			return;
		}
		$this->print( $r );
	}

	private function print_plan( array $plan ) {
		WP_CLI::line( "\n================ CHANGE PLAN ================" );
		WP_CLI::line( 'Task:      ' . $plan['task'] );
		WP_CLI::line( 'Feasible:  ' . ( $plan['feasible'] ? 'yes' : 'no' ) );
		if ( ! $plan['feasible'] ) {
			WP_CLI::line( 'Blocked:   ' . $plan['blocked_reason'] );
		}
		if ( $plan['rung'] ) {
			WP_CLI::line( 'Edit rung: ' . $plan['rung'] );
		}
		foreach ( $plan['skipped_rungs'] as $r ) {
			WP_CLI::line( "  skipped: $r" );
		}
		foreach ( $plan['changes'] as $c ) {
			WP_CLI::line( "  CHANGE {$c['setting']}: '{$c['old_value']}' -> '{$c['new_value']}'  ({$c['reason']})" );
		}
		foreach ( $plan['pages_affected'] as $p ) {
			WP_CLI::line( "  page: $p" );
		}
		foreach ( $plan['side_effects'] as $e ) {
			WP_CLI::line( "  note: $e" );
		}
		foreach ( $plan['verify'] as $v ) {
			WP_CLI::line( "  verify {$v['page']} {$v['selector']} {$v['css_property']} == {$v['expected']}" );
		}
		WP_CLI::line( "=============================================\n" );
	}

	/**
	 * Apply an approved plan run (backs up first, clears caches after).
	 *
	 * ## OPTIONS
	 *
	 * <run_id>
	 * : Run id produced by `plan`
	 *
	 * --confirm-site=<name>
	 * : Type the site name to confirm a production write
	 *
	 * @when after_wp_load
	 */
	public function apply( $args, $assoc ) {
		$this->print( WPBA_Commands::apply( (int) $args[0], $assoc['confirm-site'] ?? '' ) );
	}

	/**
	 * Restore the values changed by an `apply` run.
	 *
	 * ## OPTIONS
	 *
	 * <run_id>
	 * : Run id produced by `apply`
	 *
	 * --confirm-site=<name>
	 * : Type the site name to confirm a production write
	 *
	 * @when after_wp_load
	 */
	public function rollback( $args, $assoc ) {
		$this->print( WPBA_Commands::rollback( (int) $args[0], $assoc['confirm-site'] ?? '' ) );
	}

	/**
	 * Duplicate a page into a new draft.
	 *
	 * ## OPTIONS
	 *
	 * <page_id>
	 * : Page to copy
	 *
	 * --confirm-site=<name>
	 * : Type the site name to confirm a production write
	 *
	 * @when after_wp_load
	 */
	public function clone( $args, $assoc ) {
		$this->print( WPBA_Commands::clone_page( (int) $args[0], $assoc['confirm-site'] ?? '' ) );
	}

	/**
	 * Rebuild a code-chunk page as native Divi modules inside a draft.
	 *
	 * ## OPTIONS
	 *
	 * <source_id>
	 * : Page id to rebuild from
	 *
	 * [<draft_id>]
	 * : Draft to write into (omit to create a new draft)
	 *
	 * [--confirm-site=<name>]
	 * : Type the site name to confirm a production write
	 *
	 * [--spec-file=<path>]
	 * : Reuse a saved spec JSON instead of calling Claude
	 *
	 * [--spec-only]
	 * : Produce and validate the spec; don't touch the site
	 *
	 * @when after_wp_load
	 */
	public function rebuild( $args, $assoc ) {
		$this->print( WPBA_Commands::rebuild( (int) $args[0], (int) ( $args[1] ?? 0 ), $assoc['confirm-site'] ?? '', $this->read_json_file( $assoc['spec-file'] ?? null ), ! empty( $assoc['spec-only'] ) ) );
	}

	/**
	 * Put a verified draft's layout onto the live page and trash the draft.
	 *
	 * ## OPTIONS
	 *
	 * <live_id>
	 * : Live page id
	 *
	 * <draft_id>
	 * : Draft id
	 *
	 * --confirm-site=<name>
	 * : Type the site name to confirm a production write
	 *
	 * @when after_wp_load
	 */
	public function golive( $args, $assoc ) {
		$this->print( WPBA_Commands::golive( (int) $args[0], (int) $args[1], $assoc['confirm-site'] ?? '' ) );
	}

	/**
	 * Append a CSS block to Divi Theme Options > Custom CSS (last resort, logged).
	 *
	 * ## OPTIONS
	 *
	 * <css_file>
	 * : Path to the CSS file
	 *
	 * --reason=<text>
	 * : Why no native Divi setting can do this (logged)
	 *
	 * --confirm-site=<name>
	 * : Type the site name to confirm a production write
	 *
	 * @subcommand theme-css
	 * @when after_wp_load
	 */
	public function theme_css( $args, $assoc ) {
		$this->print( WPBA_Commands::theme_css( (string) file_get_contents( $args[0] ), $assoc['reason'] ?? '', $assoc['confirm-site'] ?? '' ) );
	}

	/**
	 * Add the hero glow to every dark Divi page header (dry run unless --confirm-site).
	 *
	 * ## OPTIONS
	 *
	 * [--confirm-site=<name>]
	 * : Type the site name to apply on production
	 *
	 * [--only=<ids>]
	 * : Comma-separated page ids
	 *
	 * @subcommand header-glow
	 * @when after_wp_load
	 */
	public function header_glow( $args, $assoc ) {
		$only = isset( $assoc['only'] ) ? array_map( 'intval', explode( ',', $assoc['only'] ) ) : array();
		$this->print( WPBA_Commands::header_glow( $assoc['confirm-site'] ?? null, $only ) );
	}

	/**
	 * Apply a colour/radius theme to Divi pages by role (dry run unless --confirm-site).
	 *
	 * ## OPTIONS
	 *
	 * --theme=<name>
	 * : Theme name, e.g. navy-red
	 *
	 * [--confirm-site=<name>]
	 * : Type the site name to apply on production
	 *
	 * [--only=<ids>]
	 * : Comma-separated page ids (drafts allowed)
	 *
	 * @when after_wp_load
	 */
	public function restyle( $args, $assoc ) {
		$only = isset( $assoc['only'] ) ? array_map( 'intval', explode( ',', $assoc['only'] ) ) : array();
		$this->print( WPBA_Commands::restyle( $assoc['theme'] ?? '', $assoc['confirm-site'] ?? null, $only ) );
	}

	/**
	 * List registered components, or --bundle them into one Theme Options CSS block, or --install the bundle.
	 *
	 * ## OPTIONS
	 *
	 * [--bundle=<path>]
	 * : Write all component CSS to this file
	 *
	 * [--install]
	 * : Save the bundle to Theme Options > Custom CSS (needs --confirm-site)
	 *
	 * [--confirm-site=<name>]
	 * : Type the site name to confirm a production write
	 *
	 * @when after_wp_load
	 */
	public function components( $args, $assoc ) {
		if ( ! empty( $assoc['install'] ) ) {
			$this->print( WPBA_Commands::install_components( $assoc['confirm-site'] ?? '' ) );
			return;
		}
		if ( ! empty( $assoc['bundle'] ) ) {
			file_put_contents( $assoc['bundle'], WPBA_Components::bundle() );
			WP_CLI::line( 'Wrote ' . $assoc['bundle'] );
		}
		foreach ( WPBA_Components::catalogue() as $c ) {
			WP_CLI::line( $c['file'] . ': ' . implode( ' ', $c['classes'] ) );
		}
	}

	/**
	 * List runs, or show one run with --id=<run_id>.
	 *
	 * ## OPTIONS
	 *
	 * [--id=<run_id>]
	 * : Show this run in full
	 *
	 * @when after_wp_load
	 */
	public function runs( $args, $assoc ) {
		if ( ! empty( $assoc['id'] ) ) {
			$this->print( WPBA_RunLog::detail( (int) $assoc['id'] ) );
			return;
		}
		foreach ( WPBA_RunLog::list_runs( 50 ) as $r ) {
			WP_CLI::line( sprintf( '%-6d %-20s %-12s %s', $r['id'], $r['command'], $r['status'], $r['date'] ) );
		}
	}
}
