<?php
/**
 * Guard: every production write passes through here.
 *
 * - The caller must hold manage_options.
 * - The target site must be confirmed by typing its host name (like `--confirm-site` in the CLI agent).
 * - Only the post types and options listed here can be written. Plugins, themes, users and WordPress
 *   settings have no code path in this plugin at all.
 * - Drafts are the only posts that may be trashed, and nothing is ever deleted permanently.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class WPBA_Guard {

	const WRITABLE_OPTIONS    = array( 'et_divi' );
	const WRITABLE_POST_TYPES = array( 'page', 'et_pb_layout' );

	/** The string a human must type to confirm a production write. */
	public static function site_name() {
		$host = wp_parse_url( home_url(), PHP_URL_HOST );
		return strtolower( preg_replace( '/^www\./', '', (string) $host ) );
	}

	public static function can_run() {
		return current_user_can( WPBA_Plugin::CAPABILITY ) || ( defined( 'WP_CLI' ) && WP_CLI );
	}

	/** @return true|WP_Error */
	public static function check_write( $confirm_site ) {
		if ( ! self::can_run() ) {
			return new WP_Error( 'wpba_forbidden', 'You need the manage_options capability.', array( 'status' => 403 ) );
		}
		$want = self::site_name();
		if ( strtolower( trim( (string) $confirm_site ) ) !== $want ) {
			return new WP_Error(
				'wpba_confirm',
				"Production write: confirm the target site by typing its name: $want",
				array( 'status' => 400, 'expected' => $want )
			);
		}
		return true;
	}

	/** @return true|WP_Error */
	public static function check_option( $name ) {
		if ( ! in_array( $name, self::WRITABLE_OPTIONS, true ) ) {
			return new WP_Error( 'wpba_blocked', "Option '$name' is outside what the agent may write." );
		}
		return true;
	}

	/** @return WP_Post|WP_Error */
	public static function check_post( $post_id, $require_status = null ) {
		$post = get_post( (int) $post_id );
		if ( ! $post ) {
			return new WP_Error( 'wpba_no_post', "Post $post_id does not exist." );
		}
		if ( ! in_array( $post->post_type, self::WRITABLE_POST_TYPES, true ) ) {
			return new WP_Error( 'wpba_blocked', "Post type '{$post->post_type}' is outside what the agent may write." );
		}
		if ( $require_status && $post->post_status !== $require_status ) {
			return new WP_Error( 'wpba_status', "Post $post_id is '{$post->post_status}', expected '$require_status'." );
		}
		return $post;
	}
}
