<?php
/**
 * Authentication for the MCP endpoint.
 *
 * Two ways in, both ending in a Bearer token the plugin issued:
 *  1. Connection tokens: made in the admin screen, pasted as a request header (claude.ai "fixed credentials",
 *     Claude Code `--header`, Claude Desktop config).
 *  2. OAuth 2.1: the client registers itself (RFC 7591) or presents a client-id metadata URL, the site owner
 *     signs in to WordPress and approves, the client gets a short-lived access token plus a rotating refresh
 *     token (PKCE S256 required, redirect URIs matched exactly, resource bound to this MCP endpoint).
 * WordPress Application Passwords (Basic auth) also work, because WordPress core authenticates those itself.
 *
 * Every token maps to a WordPress user who must hold manage_options; the MCP request then runs as that user.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class WPBA_OAuth {

	const TOKENS_OPTION  = 'wpba_tokens';
	const CLIENTS_OPTION = 'wpba_oauth_clients';
	const ACCESS_TTL     = 3600;          // 1 hour
	const REFRESH_TTL    = 30 * 86400;    // 30 days
	const CODE_TTL       = 600;           // 10 minutes
	const CONSENT_ACTION = 'wpba_oauth_authorize';

	public static function init() {
		add_action( 'init', array( __CLASS__, 'serve_well_known' ), 0 );
		add_action( 'admin_post_' . self::CONSENT_ACTION, array( __CLASS__, 'authorize_screen' ) );
		add_action( 'admin_post_nopriv_' . self::CONSENT_ACTION, array( __CLASS__, 'authorize_login_redirect' ) );
	}

	// --- URLs -----------------------------------------------------------------------------------------

	/** Canonical MCP resource URI (RFC 8707): no trailing slash. */
	public static function resource_uri() {
		return untrailingslashit( rest_url( WPBA_Rest::NS . '/mcp' ) );
	}

	public static function issuer() {
		return untrailingslashit( home_url() );
	}

	public static function metadata_url() {
		return self::issuer() . '/.well-known/oauth-protected-resource';
	}

	public static function protected_resource_metadata() {
		return array(
			'resource'                 => self::resource_uri(),
			'authorization_servers'    => array( self::issuer() ),
			'scopes_supported'         => array( 'wpba' ),
			'bearer_methods_supported' => array( 'header' ),
			'resource_name'            => get_bloginfo( 'name' ) . ' (WP Builder Agent)',
		);
	}

	public static function authorization_server_metadata() {
		return array(
			'issuer'                                => self::issuer(),
			'authorization_endpoint'                => admin_url( 'admin-post.php?action=' . self::CONSENT_ACTION ),
			'token_endpoint'                        => rest_url( WPBA_Rest::NS . '/oauth/token' ),
			'registration_endpoint'                 => rest_url( WPBA_Rest::NS . '/oauth/register' ),
			'scopes_supported'                      => array( 'wpba' ),
			'response_types_supported'              => array( 'code' ),
			'response_modes_supported'              => array( 'query' ),
			'grant_types_supported'                 => array( 'authorization_code', 'refresh_token' ),
			'token_endpoint_auth_methods_supported' => array( 'none', 'client_secret_post' ),
			'code_challenge_methods_supported'      => array( 'S256' ),
			'client_id_metadata_document_supported' => true,
		);
	}

	/** /.well-known/oauth-protected-resource[/...] and /.well-known/oauth-authorization-server[/...] at the site root. */
	public static function serve_well_known() {
		$path = isset( $_SERVER['REQUEST_URI'] ) ? wp_parse_url( sanitize_text_field( wp_unslash( $_SERVER['REQUEST_URI'] ) ), PHP_URL_PATH ) : '';
		$home = wp_parse_url( home_url(), PHP_URL_PATH );
		if ( $home && '/' !== $home && 0 === strpos( $path, $home ) ) {
			$path = substr( $path, strlen( $home ) );
		}
		if ( 0 === strpos( $path, '/.well-known/oauth-protected-resource' ) ) {
			self::send_json( self::protected_resource_metadata() );
		}
		if ( 0 === strpos( $path, '/.well-known/oauth-authorization-server' ) ) {
			self::send_json( self::authorization_server_metadata() );
		}
	}

	private static function send_json( $data, $status = 200 ) {
		status_header( $status );
		header( 'Content-Type: application/json; charset=utf-8' );
		header( 'Access-Control-Allow-Origin: *' );
		header( 'Cache-Control: no-store' );
		if ( 'OPTIONS' === self::method() ) {
			header( 'Access-Control-Allow-Methods: GET, OPTIONS' );
			header( 'Access-Control-Allow-Headers: Content-Type, Authorization, MCP-Protocol-Version' );
			exit;
		}
		echo wp_json_encode( $data, JSON_UNESCAPED_SLASHES );
		exit;
	}

	// --- token store ----------------------------------------------------------------------------------

	private static function tokens() {
		$t = get_option( self::TOKENS_OPTION, array() );
		return is_array( $t ) ? $t : array();
	}

	private static function save_tokens( array $t ) {
		$now = time();
		foreach ( $t as $hash => $row ) {
			if ( ! empty( $row['expires'] ) && $row['expires'] < $now ) {
				unset( $t[ $hash ] );
			}
		}
		update_option( self::TOKENS_OPTION, $t, 'no' );
	}

	private static function hash( $token ) {
		return hash( 'sha256', $token );
	}

	/**
	 * Mint a token. type: connection | access | refresh. Returns the plain token (shown once).
	 */
	public static function issue( $type, $user_id, array $meta = array(), $ttl = null ) {
		$plain = ( 'connection' === $type ? 'wpba_' : '' ) . bin2hex( random_bytes( 32 ) );
		$t     = self::tokens();
		$t[ self::hash( $plain ) ] = array_merge(
			array(
				'type'    => $type,
				'user_id' => (int) $user_id,
				'created' => time(),
				'expires' => $ttl ? time() + $ttl : 0,
				'prefix'  => substr( $plain, 0, 10 ),
			),
			$meta
		);
		self::save_tokens( $t );
		return $plain;
	}

	public static function lookup( $plain ) {
		$t = self::tokens();
		$h = self::hash( (string) $plain );
		if ( ! isset( $t[ $h ] ) ) {
			return null;
		}
		$row = $t[ $h ];
		if ( ! empty( $row['expires'] ) && $row['expires'] < time() ) {
			return null;
		}
		$row['hash'] = $h;
		return $row;
	}

	public static function revoke_hash( $hash ) {
		$t = self::tokens();
		unset( $t[ $hash ] );
		self::save_tokens( $t );
	}

	public static function revoke_client( $client_id ) {
		$t = self::tokens();
		foreach ( $t as $h => $row ) {
			if ( ( $row['client_id'] ?? '' ) === $client_id ) {
				unset( $t[ $h ] );
			}
		}
		self::save_tokens( $t );
		$c = self::clients();
		unset( $c[ $client_id ] );
		update_option( self::CLIENTS_OPTION, $c, 'no' );
	}

	/** Listing for the admin screen: never the token itself. */
	public static function list_tokens() {
		$out = array();
		foreach ( self::tokens() as $h => $row ) {
			$u     = get_userdata( (int) $row['user_id'] );
			$out[] = array(
				'hash'      => $h,
				'type'      => $row['type'],
				'label'     => $row['label'] ?? ( $row['client_name'] ?? '' ),
				'client_id' => $row['client_id'] ?? '',
				'prefix'    => $row['prefix'] ?? '',
				'user'      => $u ? $u->user_login : (string) $row['user_id'],
				'created'   => gmdate( 'Y-m-d H:i', (int) $row['created'] ),
				'expires'   => empty( $row['expires'] ) ? 'never' : gmdate( 'Y-m-d H:i', (int) $row['expires'] ),
				'last_used' => empty( $row['last_used'] ) ? '' : gmdate( 'Y-m-d H:i', (int) $row['last_used'] ),
			);
		}
		return $out;
	}

	public static function touch( $hash ) {
		$t = self::tokens();
		if ( isset( $t[ $hash ] ) && ( empty( $t[ $hash ]['last_used'] ) || time() - $t[ $hash ]['last_used'] > 300 ) ) {
			$t[ $hash ]['last_used'] = time();
			update_option( self::TOKENS_OPTION, $t, 'no' );
		}
	}

	// --- request authentication -----------------------------------------------------------------------

	private static function bearer_from_request( WP_REST_Request $r ) {
		$auth = $r->get_header( 'authorization' );
		if ( ! $auth && isset( $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ) ) {
			$auth = sanitize_text_field( wp_unslash( $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ) ); // Apache CGI/FastCGI keeps it here
		}
		if ( $auth && preg_match( '/^Bearer\s+(\S+)$/i', trim( $auth ), $m ) ) {
			return $m[1];
		}
		$alt = $r->get_header( 'x-wpba-token' );
		return $alt ? trim( $alt ) : null;
	}

	/**
	 * Authenticate an MCP request. @return int|WP_Error user id
	 */
	public static function authenticate( WP_REST_Request $r ) {
		// Already authenticated by WordPress itself (Application Password Basic auth, or a logged-in REST call with nonce).
		if ( get_current_user_id() && current_user_can( WPBA_Plugin::CAPABILITY ) ) {
			return get_current_user_id();
		}
		$plain = self::bearer_from_request( $r );
		if ( ! $plain ) {
			return new WP_Error( 'wpba_unauthorized', 'Bearer token required', array( 'status' => 401 ) );
		}
		$row = self::lookup( $plain );
		if ( ! $row || ! in_array( $row['type'], array( 'connection', 'access' ), true ) ) {
			return new WP_Error( 'wpba_unauthorized', 'Invalid or expired token', array( 'status' => 401 ) );
		}
		if ( 'access' === $row['type'] && ( $row['resource'] ?? '' ) !== self::resource_uri() ) {
			return new WP_Error( 'wpba_unauthorized', 'Token was not issued for this MCP server', array( 'status' => 401 ) );
		}
		$user = get_userdata( (int) $row['user_id'] );
		if ( ! $user || ! user_can( $user, WPBA_Plugin::CAPABILITY ) ) {
			return new WP_Error( 'wpba_forbidden', 'Token owner no longer has manage_options', array( 'status' => 403 ) );
		}
		wp_set_current_user( $user->ID );
		self::touch( $row['hash'] );
		return $user->ID;
	}

	public static function www_authenticate_header() {
		return 'Bearer resource_metadata="' . self::metadata_url() . '"';
	}

	// --- clients (RFC 7591 dynamic registration, or client-id metadata documents) -----------------------

	private static function clients() {
		$c = get_option( self::CLIENTS_OPTION, array() );
		return is_array( $c ) ? $c : array();
	}

	public static function list_clients() {
		$out = array();
		foreach ( self::clients() as $id => $c ) {
			$out[] = array( 'client_id' => $id, 'client_name' => $c['client_name'] ?? '', 'redirect_uris' => $c['redirect_uris'] ?? array(), 'created' => gmdate( 'Y-m-d H:i', (int) ( $c['created'] ?? 0 ) ) );
		}
		return $out;
	}

	/** POST /oauth/register */
	public static function register( WP_REST_Request $r ) {
		$j = $r->get_json_params();
		if ( ! is_array( $j ) ) {
			return self::oauth_error( 'invalid_client_metadata', 'JSON body required' );
		}
		$uris = isset( $j['redirect_uris'] ) && is_array( $j['redirect_uris'] ) ? array_values( array_filter( array_map( 'strval', $j['redirect_uris'] ) ) ) : array();
		if ( ! $uris ) {
			return self::oauth_error( 'invalid_redirect_uri', 'redirect_uris required' );
		}
		foreach ( $uris as $u ) {
			if ( ! self::redirect_uri_ok( $u ) ) {
				return self::oauth_error( 'invalid_redirect_uri', "redirect_uris must be https or localhost: $u" );
			}
		}
		$auth_method = $j['token_endpoint_auth_method'] ?? 'none';
		if ( ! in_array( $auth_method, array( 'none', 'client_secret_post' ), true ) ) {
			$auth_method = 'none';
		}
		$id     = 'wpba-' . bin2hex( random_bytes( 12 ) );
		$secret = 'client_secret_post' === $auth_method ? bin2hex( random_bytes( 24 ) ) : null;
		$c      = self::clients();
		$c[ $id ] = array(
			'client_name'   => sanitize_text_field( (string) ( $j['client_name'] ?? '' ) ),
			'redirect_uris' => $uris,
			'auth_method'   => $auth_method,
			'secret_hash'   => $secret ? self::hash( $secret ) : null,
			'created'       => time(),
		);
		update_option( self::CLIENTS_OPTION, $c, 'no' );
		$out = array(
			'client_id'                  => $id,
			'client_id_issued_at'        => time(),
			'client_name'                => $c[ $id ]['client_name'],
			'redirect_uris'              => $uris,
			'token_endpoint_auth_method' => $auth_method,
			'grant_types'                => array( 'authorization_code', 'refresh_token' ),
			'response_types'             => array( 'code' ),
			'scope'                      => 'wpba',
		);
		if ( $secret ) {
			$out['client_secret']            = $secret;
			$out['client_secret_expires_at'] = 0;
		}
		return new WP_REST_Response( $out, 201 );
	}

	private static function redirect_uri_ok( $u ) {
		$p = wp_parse_url( $u );
		if ( empty( $p['scheme'] ) || empty( $p['host'] ) || ! empty( $p['fragment'] ) ) {
			return false;
		}
		return 'https' === $p['scheme'] || in_array( $p['host'], array( 'localhost', '127.0.0.1', '[::1]' ), true );
	}

	/**
	 * Resolve a client: a registered id, or an https URL to a client-id metadata document.
	 * @return array|WP_Error { client_name, redirect_uris, auth_method, secret_hash }
	 */
	public static function resolve_client( $client_id ) {
		$c = self::clients();
		if ( isset( $c[ $client_id ] ) ) {
			return $c[ $client_id ];
		}
		if ( preg_match( '#^https://#i', $client_id ) ) {
			$cached = get_transient( 'wpba_cimd_' . md5( $client_id ) );
			if ( is_array( $cached ) ) {
				return $cached;
			}
			$res = wp_remote_get( $client_id, array( 'timeout' => 15, 'headers' => array( 'Accept' => 'application/json' ) ) );
			if ( is_wp_error( $res ) || 200 !== (int) wp_remote_retrieve_response_code( $res ) ) {
				return new WP_Error( 'invalid_client', 'Could not fetch client metadata document' );
			}
			$doc = json_decode( wp_remote_retrieve_body( $res ), true );
			if ( ! is_array( $doc ) || ( $doc['client_id'] ?? '' ) !== $client_id || empty( $doc['redirect_uris'] ) ) {
				return new WP_Error( 'invalid_client', 'Client metadata document is not valid for this client_id' );
			}
			$meta = array(
				'client_name'   => sanitize_text_field( (string) ( $doc['client_name'] ?? wp_parse_url( $client_id, PHP_URL_HOST ) ) ),
				'redirect_uris' => array_values( array_map( 'strval', (array) $doc['redirect_uris'] ) ),
				'auth_method'   => 'none',
				'secret_hash'   => null,
			);
			set_transient( 'wpba_cimd_' . md5( $client_id ), $meta, HOUR_IN_SECONDS );
			return $meta;
		}
		return new WP_Error( 'invalid_client', 'Unknown client_id' );
	}

	// --- authorize (consent screen, admin-post.php) -----------------------------------------------------

	private static function method() {
		return isset( $_SERVER['REQUEST_METHOD'] ) ? strtoupper( sanitize_key( wp_unslash( $_SERVER['REQUEST_METHOD'] ) ) ) : 'GET';
	}

	/** Send the browser to a client's registered redirect URI (validated against the registration above). */
	private static function redirect_to_client( $url ) {
		$host = wp_parse_url( $url, PHP_URL_HOST );
		add_filter( 'allowed_redirect_hosts', function ( $hosts ) use ( $host ) { $hosts[] = $host; return $hosts; } );
		wp_safe_redirect( $url );
		exit;
	}

	public static function authorize_login_redirect() {
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- OAuth authorization request parameters; the consent form that follows is nonce-protected.
		$back = admin_url( 'admin-post.php?' . http_build_query( array_map( 'sanitize_text_field', wp_unslash( $_GET ) ) ) );
		wp_safe_redirect( wp_login_url( $back ) );
		exit;
	}

	public static function authorize_screen() {
		if ( ! current_user_can( WPBA_Plugin::CAPABILITY ) ) {
			wp_die( 'Only an administrator can connect Claude to this site.', 'WP Builder Agent', array( 'response' => 403 ) );
		}
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended, WordPress.Security.NonceVerification.Missing -- OAuth authorization request; the POST (consent) branch below verifies the nonce.
		$q = array_map( 'sanitize_text_field', wp_unslash( 'POST' === self::method() ? $_POST : $_GET ) );
		$p = array();
		foreach ( array( 'client_id', 'redirect_uri', 'state', 'code_challenge', 'code_challenge_method', 'scope', 'resource', 'response_type' ) as $k ) {
			$p[ $k ] = isset( $q[ $k ] ) ? (string) $q[ $k ] : '';
		}
		$client = self::resolve_client( $p['client_id'] );
		if ( is_wp_error( $client ) ) {
			wp_die( esc_html( 'OAuth: ' . $client->get_error_message() ), 'WP Builder Agent', array( 'response' => 400 ) );
		}
		if ( ! in_array( $p['redirect_uri'], $client['redirect_uris'], true ) ) {
			wp_die( 'OAuth: redirect_uri is not registered for this client.', 'WP Builder Agent', array( 'response' => 400 ) );
		}
		// From here on errors go back to the client, as OAuth says.
		$fail = function ( $error, $desc ) use ( $p ) {
			self::redirect_to_client( add_query_arg( array( 'error' => $error, 'error_description' => rawurlencode( $desc ), 'state' => rawurlencode( $p['state'] ) ), $p['redirect_uri'] ) );
		};
		if ( 'code' !== $p['response_type'] ) {
			$fail( 'unsupported_response_type', 'response_type must be code' );
		}
		if ( 'S256' !== $p['code_challenge_method'] || ! preg_match( '/^[A-Za-z0-9_\-]{43,128}$/', $p['code_challenge'] ) ) {
			$fail( 'invalid_request', 'PKCE S256 code_challenge required' );
		}
		if ( $p['resource'] && untrailingslashit( $p['resource'] ) !== self::resource_uri() ) {
			$fail( 'invalid_target', 'resource must be ' . self::resource_uri() );
		}

		if ( 'POST' === self::method() ) {
			check_admin_referer( self::CONSENT_ACTION );
			if ( empty( $q['approve'] ) ) {
				$fail( 'access_denied', 'The site owner declined' );
			}
			$code = bin2hex( random_bytes( 32 ) );
			set_transient(
				'wpba_code_' . self::hash( $code ),
				array(
					'client_id'      => $p['client_id'],
					'redirect_uri'   => $p['redirect_uri'],
					'code_challenge' => $p['code_challenge'],
					'user_id'        => get_current_user_id(),
					'resource'       => self::resource_uri(),
					'client_name'    => $client['client_name'],
				),
				self::CODE_TTL
			);
			self::redirect_to_client( add_query_arg( array( 'code' => $code, 'state' => rawurlencode( $p['state'] ) ), $p['redirect_uri'] ) );
		}
		self::render_consent( $p, $client );
		exit;
	}

	private static function render_consent( array $p, array $client ) {
		$site = WPBA_Guard::site_name();
		$name = $client['client_name'] ? $client['client_name'] : $p['client_id'];
		$host = wp_parse_url( $p['redirect_uri'], PHP_URL_HOST );
		status_header( 200 );
		header( 'Content-Type: text/html; charset=utf-8' );
		?>
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Connect Claude to <?php echo esc_html( $site ); ?></title>
<style>body{font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f0f0f1;color:#1d2327;margin:0;display:flex;min-height:100vh;align-items:center;justify-content:center}
.card{background:#fff;border:1px solid #c3c4c7;border-radius:8px;padding:28px 32px;max-width:520px;width:92%}h1{font-size:20px;margin:0 0 8px}ul{margin:12px 0 20px 18px;padding:0}li{margin:4px 0}
.row{display:flex;gap:10px}button{font-size:15px;padding:10px 18px;border-radius:4px;border:1px solid #2271b1;background:#2271b1;color:#fff;cursor:pointer}button.secondary{background:#fff;color:#2271b1}
.muted{color:#646970;font-size:13px}code{background:#f6f7f7;padding:1px 5px;border-radius:3px}</style></head><body>
<form class="card" method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
<h1>Connect <?php echo esc_html( $name ); ?> to <?php echo esc_html( $site ); ?>?</h1>
<p>This lets Claude use WP Builder Agent on this site as <strong><?php echo esc_html( wp_get_current_user()->user_login ); ?></strong>. It will be able to:</p>
<ul><li>read Divi settings, page layouts and run records</li><li>propose and apply Customizer changes, rebuild pages into drafts, put drafts live, add CSS</li></ul>
<p class="muted">Every write still backs up first and needs the site name <code><?php echo esc_html( $site ); ?></code> given as confirmation. You can revoke this connection any time under Builder Agent &gt; Connect Claude. Redirects to <code><?php echo esc_html( $host ); ?></code>.</p>
<?php wp_nonce_field( self::CONSENT_ACTION ); ?>
<input type="hidden" name="action" value="<?php echo esc_attr( self::CONSENT_ACTION ); ?>">
<?php foreach ( $p as $k => $v ) : ?><input type="hidden" name="<?php echo esc_attr( $k ); ?>" value="<?php echo esc_attr( $v ); ?>"><?php endforeach; ?>
<div class="row"><button type="submit" name="approve" value="1">Allow</button><button type="submit" name="approve" value="" class="secondary">Deny</button></div>
</form></body></html>
		<?php
	}

	// --- token endpoint -------------------------------------------------------------------------------

	public static function oauth_error( $error, $desc, $status = 400 ) {
		$r = new WP_REST_Response( array( 'error' => $error, 'error_description' => $desc ), $status );
		$r->header( 'Cache-Control', 'no-store' );
		return $r;
	}

	/** POST /oauth/token (form-encoded or JSON) */
	public static function token( WP_REST_Request $r ) {
		$p = array_merge( (array) $r->get_body_params(), (array) ( $r->get_json_params() ?: array() ) );
		$grant = (string) ( $p['grant_type'] ?? '' );
		$client_id = (string) ( $p['client_id'] ?? '' );
		$client = self::resolve_client( $client_id );
		if ( is_wp_error( $client ) ) {
			return self::oauth_error( 'invalid_client', $client->get_error_message(), 401 );
		}
		if ( 'client_secret_post' === ( $client['auth_method'] ?? 'none' ) ) {
			if ( empty( $p['client_secret'] ) || self::hash( (string) $p['client_secret'] ) !== $client['secret_hash'] ) {
				return self::oauth_error( 'invalid_client', 'Bad client secret', 401 );
			}
		}
		if ( 'authorization_code' === $grant ) {
			$code = (string) ( $p['code'] ?? '' );
			$key  = 'wpba_code_' . self::hash( $code );
			$data = get_transient( $key );
			if ( ! is_array( $data ) ) {
				return self::oauth_error( 'invalid_grant', 'Unknown or expired code' );
			}
			delete_transient( $key ); // single use
			if ( $data['client_id'] !== $client_id || ( $p['redirect_uri'] ?? '' ) !== $data['redirect_uri'] ) {
				return self::oauth_error( 'invalid_grant', 'client_id or redirect_uri does not match the authorization request' );
			}
			$verifier = (string) ( $p['code_verifier'] ?? '' );
			$expected = rtrim( strtr( base64_encode( hash( 'sha256', $verifier, true ) ), '+/', '-_' ), '=' );
			if ( '' === $verifier || ! hash_equals( $data['code_challenge'], $expected ) ) {
				return self::oauth_error( 'invalid_grant', 'PKCE verification failed' );
			}
			if ( ! empty( $p['resource'] ) && untrailingslashit( (string) $p['resource'] ) !== $data['resource'] ) {
				return self::oauth_error( 'invalid_target', 'resource must be ' . $data['resource'] );
			}
			return self::issue_pair( $data['user_id'], $client_id, $data['client_name'] );
		}
		if ( 'refresh_token' === $grant ) {
			$row = self::lookup( (string) ( $p['refresh_token'] ?? '' ) );
			if ( ! $row || 'refresh' !== $row['type'] || $row['client_id'] !== $client_id ) {
				return self::oauth_error( 'invalid_grant', 'Unknown or expired refresh token' );
			}
			self::revoke_hash( $row['hash'] ); // rotation
			if ( ! empty( $row['access_hash'] ) ) {
				self::revoke_hash( $row['access_hash'] );
			}
			return self::issue_pair( $row['user_id'], $client_id, $row['client_name'] ?? '' );
		}
		return self::oauth_error( 'unsupported_grant_type', 'Use authorization_code or refresh_token' );
	}

	private static function issue_pair( $user_id, $client_id, $client_name ) {
		$meta    = array( 'client_id' => $client_id, 'client_name' => $client_name, 'resource' => self::resource_uri() );
		$access  = self::issue( 'access', $user_id, $meta, self::ACCESS_TTL );
		$refresh = self::issue( 'refresh', $user_id, $meta + array( 'access_hash' => self::hash( $access ) ), self::REFRESH_TTL );
		$r       = new WP_REST_Response(
			array(
				'access_token'  => $access,
				'token_type'    => 'Bearer',
				'expires_in'    => self::ACCESS_TTL,
				'refresh_token' => $refresh,
				'scope'         => 'wpba',
			),
			200
		);
		$r->header( 'Cache-Control', 'no-store' );
		$r->header( 'Pragma', 'no-cache' );
		return $r;
	}
}
