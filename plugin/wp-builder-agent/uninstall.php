<?php
/**
 * Removes the plugin's own data: settings, usage log and run records.
 * Site content the agent edited (pages, Customizer values, Custom CSS) is left exactly as it is.
 */
if ( ! defined( 'WP_UNINSTALL_PLUGIN' ) ) {
	exit;
}

function wpba_uninstall() {
	foreach ( array( 'wpba_settings', 'wpba_usage', 'wpba_site_profile', 'wpba_tokens', 'wpba_oauth_clients' ) as $option ) {
		delete_option( $option );
	}
	$runs = get_posts(
		array(
			'post_type'   => 'wpba_run',
			'post_status' => 'any',
			'numberposts' => -1,
			'fields'      => 'ids',
		)
	);
	foreach ( $runs as $run_id ) {
		wp_delete_post( $run_id, true );
	}
}
wpba_uninstall();
