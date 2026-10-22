<?php
/**
 * REST API (namespace wpba/v1) used by the admin screen. Every route needs manage_options and a REST nonce.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class WPBA_Rest {

	const NS = 'wpba/v1';

	public static function register_routes() {
		$perm = function () { return current_user_can( WPBA_Plugin::CAPABILITY ); };
		$r    = function ( $route, $methods, $cb ) use ( $perm ) {
			register_rest_route( self::NS, $route, array( 'methods' => $methods, 'callback' => $cb, 'permission_callback' => $perm ) );
		};
		$r( '/status', 'GET', array( __CLASS__, 'status' ) );
		$r( '/settings', 'GET', function () { return WPBA_Settings::public_view(); } );
		$r( '/settings', 'POST', function ( $q ) { $u = WPBA_Settings::update( (array) $q->get_json_params() ); return self::out( is_wp_error( $u ) ? $u : WPBA_Settings::public_view() ); } );
		$r( '/profile', 'GET', function () { return WPBA_Settings::profile(); } );
		$r( '/profile', 'POST', function ( $q ) { $j = $q->get_json_params(); return self::out( WPBA_Settings::update_profile( $j['profile'] ?? $j ) ); } );
		$r( '/pages', 'GET', function ( $q ) { return WPBA_Divi::list_pages( array(), $q->get_param( 'status' ) ?: array( 'publish', 'draft' ) ); } );
		$r( '/runs', 'GET', function ( $q ) { return WPBA_RunLog::list_runs( (int) ( $q->get_param( 'limit' ) ?: 50 ) ); } );
		$r( '/runs/(?P<id>\d+)', 'GET', function ( $q ) { return self::out( WPBA_RunLog::detail( (int) $q['id'] ) ); } );
		$r( '/usage', 'GET', function () { return array( 'total_usd' => WPBA_Usage::total_usd(), 'recent' => WPBA_Usage::recent( 20 ) ); } );
		$r( '/components', 'GET', function () { return WPBA_Commands::components(); } );
		$r( '/restyle/themes', 'GET', function () { return array_keys( WPBA_Restyle::themes() ); } );

		// Connect Claude: the MCP endpoint, its OAuth endpoints, and token management for the admin screen.
		WPBA_MCP::register_routes( $perm );
		$r( '/connect', 'GET', array( __CLASS__, 'connect_info' ) );
		$r( '/tokens', 'GET', function () { return WPBA_OAuth::list_tokens(); } );
		$r( '/tokens', 'POST', function ( $q ) {
			$j     = $q->get_json_params();
			$label = sanitize_text_field( (string) ( $j['label'] ?? 'connection' ) );
			$token = WPBA_OAuth::issue( 'connection', get_current_user_id(), array( 'label' => $label ) );
			return array( 'token' => $token, 'label' => $label, 'note' => 'Shown once. Paste it as a request header: Authorization: Bearer <token>' );
		} );
		$r( '/tokens', 'DELETE', function ( $q ) { $j = $q->get_json_params(); WPBA_OAuth::revoke_hash( (string) ( $j['hash'] ?? '' ) ); return WPBA_OAuth::list_tokens(); } );
		$r( '/oauth/clients', 'GET', function () { return WPBA_OAuth::list_clients(); } );
		$r( '/oauth/clients', 'DELETE', function ( $q ) { $j = $q->get_json_params(); WPBA_OAuth::revoke_client( (string) ( $j['client_id'] ?? '' ) ); return WPBA_OAuth::list_clients(); } );

		$r( '/snapshot', 'POST', function () { return self::out( WPBA_Commands::snapshot() ); } );
		$r( '/plan', 'POST', function ( $q ) {
			$j = $q->get_json_params();
			return self::out( WPBA_Commands::plan( $j['task'] ?? '', isset( $j['plan_file'] ) && is_array( $j['plan_file'] ) ? $j['plan_file'] : null ) );
		} );
		$r( '/apply', 'POST', function ( $q ) {
			$j = $q->get_json_params();
			return self::out( WPBA_Commands::apply( (int) ( $j['run_id'] ?? 0 ), $j['confirm_site'] ?? '', isset( $j['before'] ) && is_array( $j['before'] ) ? $j['before'] : array() ) );
		} );
		$r( '/rollback', 'POST', function ( $q ) {
			$j = $q->get_json_params();
			return self::out( WPBA_Commands::rollback( (int) ( $j['run_id'] ?? 0 ), $j['confirm_site'] ?? '' ) );
		} );
		$r( '/verify', 'POST', function ( $q ) {
			$j   = $q->get_json_params();
			$log = WPBA_RunLog::open( (int) ( $j['run_id'] ?? 0 ) );
			if ( is_wp_error( $log ) ) {
				return self::out( $log );
			}
			return WPBA_Verify::record( $log, isset( $j['results'] ) && is_array( $j['results'] ) ? $j['results'] : array() );
		} );
		$r( '/clone', 'POST', function ( $q ) {
			$j = $q->get_json_params();
			return self::out( WPBA_Commands::clone_page( (int) ( $j['page_id'] ?? 0 ), $j['confirm_site'] ?? '' ) );
		} );
		$r( '/rebuild', 'POST', function ( $q ) {
			$j = $q->get_json_params();
			return self::out( WPBA_Commands::rebuild( (int) ( $j['source_id'] ?? 0 ), (int) ( $j['draft_id'] ?? 0 ), $j['confirm_site'] ?? '',
				isset( $j['spec'] ) && is_array( $j['spec'] ) ? $j['spec'] : null, ! empty( $j['spec_only'] ) ) );
		} );
		$r( '/golive', 'POST', function ( $q ) {
			$j = $q->get_json_params();
			return self::out( WPBA_Commands::golive( (int) ( $j['live_id'] ?? 0 ), (int) ( $j['draft_id'] ?? 0 ), $j['confirm_site'] ?? '' ) );
		} );
		$r( '/theme-css', 'POST', function ( $q ) {
			$j = $q->get_json_params();
			return self::out( WPBA_Commands::theme_css( (string) ( $j['css'] ?? '' ), (string) ( $j['reason'] ?? '' ), $j['confirm_site'] ?? '' ) );
		} );
		$r( '/components/install', 'POST', function ( $q ) {
			$j = $q->get_json_params();
			return self::out( WPBA_Commands::install_components( $j['confirm_site'] ?? '' ) );
		} );
		$r( '/header-glow', 'POST', function ( $q ) {
			$j = $q->get_json_params();
			return self::out( WPBA_Commands::header_glow( $j['confirm_site'] ?? null, array_map( 'intval', (array) ( $j['only'] ?? array() ) ) ) );
		} );
		$r( '/restyle', 'POST', function ( $q ) {
			$j = $q->get_json_params();
			return self::out( WPBA_Commands::restyle( (string) ( $j['theme'] ?? '' ), $j['confirm_site'] ?? null, array_map( 'intval', (array) ( $j['only'] ?? array() ) ) ) );
		} );
	}

	public static function connect_info() {
		$mcp = WPBA_OAuth::resource_uri();
		return array(
			'mcp_url'          => $mcp,
			'https'            => 0 === strpos( $mcp, 'https://' ),
			'metadata_url'     => WPBA_OAuth::metadata_url(),
			'authorize_url'    => admin_url( 'admin-post.php?action=' . WPBA_OAuth::CONSENT_ACTION ),
			'claude_code'      => 'claude mcp add --transport http wp-builder-agent ' . $mcp,
			'claude_code_token' => 'claude mcp add --transport http wp-builder-agent ' . $mcp . ' --header "Authorization: Bearer <token>"',
			'tokens'           => WPBA_OAuth::list_tokens(),
			'clients'          => WPBA_OAuth::list_clients(),
			'tools'            => array_map( function ( $t ) { return $t['name']; }, WPBA_MCP_Tools::definitions() ),
		);
	}

	public static function status() {
		return array(
			'detect'     => WPBA_Divi::detect(),
			'site'       => WPBA_Guard::site_name(),
			'home_url'   => home_url(),
			'settings'   => WPBA_Settings::public_view(),
			'usage_usd'  => WPBA_Usage::total_usd(),
			'components' => count( WPBA_Components::registered() ),
			'runs'       => count( WPBA_RunLog::list_runs( 500 ) ),
		);
	}

	/** Arrays pass through; WP_Error becomes a proper error response with its data attached. */
	public static function out( $result ) {
		if ( is_wp_error( $result ) ) {
			$data   = (array) $result->get_error_data();
			$status = isset( $data['status'] ) ? (int) $data['status'] : 400;
			return new WP_REST_Response( array( 'error' => $result->get_error_message(), 'code' => $result->get_error_code(), 'data' => $data ), $status );
		}
		return rest_ensure_response( $result );
	}
}
