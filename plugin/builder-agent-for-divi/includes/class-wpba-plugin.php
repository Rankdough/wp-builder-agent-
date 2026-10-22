<?php
/**
 * Bootstrap: post type for run records, admin screens, REST routes and WP-CLI commands.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class WPBA_Plugin {

	const RUN_POST_TYPE = 'wpba_run';
	const CAPABILITY    = 'manage_options';

	/** @var WPBA_Plugin|null */
	private static $instance = null;

	public static function instance() {
		if ( null === self::$instance ) {
			self::$instance = new self();
		}
		return self::$instance;
	}

	private function __construct() {
		add_action( 'init', array( $this, 'register_post_type' ) );
		add_action( 'rest_api_init', array( 'WPBA_Rest', 'register_routes' ) );
		WPBA_OAuth::init();
		if ( is_admin() ) {
			WPBA_Admin::init();
		}
		if ( defined( 'WP_CLI' ) && WP_CLI ) {
			WP_CLI::add_command( 'wpagent', 'WPBA_CLI' );
		}
	}

	public static function activate() {
		self::instance()->register_post_type();
		flush_rewrite_rules();
		if ( false === get_option( 'wpba_settings', false ) ) {
			add_option( 'wpba_settings', WPBA_Settings::defaults(), '', 'no' );
		}
	}

	public static function deactivate() {
		flush_rewrite_rules();
	}

	/** Run records: one private post per command run, with the event log, backups and files as meta. */
	public function register_post_type() {
		register_post_type(
			self::RUN_POST_TYPE,
			array(
				'labels'              => array(
					'name'          => 'Agent runs',
					'singular_name' => 'Agent run',
				),
				'public'              => false,
				'show_ui'             => false,
				'show_in_rest'        => false,
				'exclude_from_search' => true,
				'supports'            => array( 'title' ),
				'capability_type'     => 'post',
				'capabilities'        => array( 'create_posts' => self::CAPABILITY ),
				'map_meta_cap'        => true,
			)
		);
	}

	/** True when the Divi theme (or the Divi Builder plugin) is active. */
	public static function divi_present() {
		return function_exists( 'et_pb_is_pagebuilder_used' ) || defined( 'ET_BUILDER_VERSION' ) || defined( 'ET_CORE_VERSION' );
	}
}
