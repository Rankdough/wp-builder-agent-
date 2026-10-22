<?php
/**
 * MCP server (Streamable HTTP, JSON-RPC 2.0) so Claude itself drives the agent: claude.ai and Claude Desktop
 * as a custom connector, Claude Code with `claude mcp add --transport http`, Cowork through connectors.
 *
 * In this mode the Claude you are talking to is the planner and the page designer: the tools hand it the same
 * context and schemas the CLI agent gave the API, and the same validators check what it sends back before
 * anything is written. The site's own API key is optional (only `plan_with_api` uses it).
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class WPBA_MCP {

	const PROTOCOL_VERSIONS = array( '2025-11-25', '2025-06-18', '2025-03-26', '2024-11-05' );
	const DEFAULT_PROTOCOL  = '2025-06-18';

	const INSTRUCTIONS = <<<'TXT'
Builder Agent for Divi edits a Divi 4 WordPress site carefully. Rules the tools enforce and you should follow:
- Read before you write: site_status, get_plan_context or get_page_dump first.
- Plans: write the plan yourself from get_plan_context (edit ladder: Customizer first, Custom CSS last),
  submit it with propose_plan (validated, nothing written), show it to the user, and only apply_plan after
  they approve. Rebuilds: get_spec_schema, write the spec, rebuild_page with spec_only=true first.
- Every production write needs confirm_site set to the site name shown by site_status. Ask the user to confirm
  the site name in their own words before passing it; never fill it in on your own.
- Writes back up first and are recorded as runs (list_runs / get_run). rollback undoes an apply_plan run.
TXT;

	public static function register_routes( $perm_admin ) {
		register_rest_route( WPBA_Rest::NS, '/mcp', array(
			array( 'methods' => 'POST', 'callback' => array( __CLASS__, 'handle' ), 'permission_callback' => '__return_true' ),
			array( 'methods' => array( 'GET', 'DELETE', 'OPTIONS' ), 'callback' => array( __CLASS__, 'handle_other' ), 'permission_callback' => '__return_true' ),
		) );
		register_rest_route( WPBA_Rest::NS, '/oauth/register', array( 'methods' => 'POST', 'callback' => array( 'WPBA_OAuth', 'register' ), 'permission_callback' => '__return_true' ) );
		register_rest_route( WPBA_Rest::NS, '/oauth/token', array( 'methods' => 'POST', 'callback' => array( 'WPBA_OAuth', 'token' ), 'permission_callback' => '__return_true' ) );
		// 202 Accepted must have no body; WordPress would print "null".
		add_filter( 'rest_pre_serve_request', function ( $served, $result, $request ) {
			if ( '/' . WPBA_Rest::NS . '/mcp' === $request->get_route() && $result instanceof WP_REST_Response && 202 === $result->get_status() ) {
				return true;
			}
			return $served;
		}, 10, 3 );
	}

	public static function handle_other( WP_REST_Request $r ) {
		if ( 'OPTIONS' === $r->get_method() ) {
			return new WP_REST_Response( null, 204 );
		}
		$res = new WP_REST_Response( array( 'error' => 'This server answers JSON-RPC over POST only; no SSE stream and no sessions.' ), 405 );
		$res->header( 'Allow', 'POST' );
		return $res;
	}

	private static function rpc_error( $id, $code, $message, $status = 200 ) {
		return new WP_REST_Response( array( 'jsonrpc' => '2.0', 'id' => $id, 'error' => array( 'code' => $code, 'message' => $message ) ), $status );
	}

	public static function handle( WP_REST_Request $r ) {
		// DNS-rebinding guard: a browser Origin must be this site; MCP clients normally send none.
		$origin = $r->get_header( 'origin' );
		if ( $origin && wp_parse_url( $origin, PHP_URL_HOST ) !== wp_parse_url( home_url(), PHP_URL_HOST ) ) {
			return self::rpc_error( null, -32600, 'Origin not allowed', 403 );
		}
		$user = WPBA_OAuth::authenticate( $r );
		if ( is_wp_error( $user ) ) {
			$status = (int) ( $user->get_error_data()['status'] ?? 401 );
			$res    = self::rpc_error( null, -32001, $user->get_error_message(), $status );
			if ( 401 === $status ) {
				$res->header( 'WWW-Authenticate', WPBA_OAuth::www_authenticate_header() );
			}
			return $res;
		}
		$pv = $r->get_header( 'mcp-protocol-version' );
		if ( $pv && ! in_array( $pv, self::PROTOCOL_VERSIONS, true ) ) {
			return self::rpc_error( null, -32600, 'Unsupported MCP-Protocol-Version', 400 );
		}
		$msg = json_decode( $r->get_body(), true );
		if ( ! is_array( $msg ) || ( $msg['jsonrpc'] ?? '' ) !== '2.0' ) {
			return self::rpc_error( null, -32700, 'Parse error: a single JSON-RPC 2.0 message is required', 400 );
		}
		$id     = array_key_exists( 'id', $msg ) ? $msg['id'] : null;
		$method = (string) ( $msg['method'] ?? '' );
		$params = isset( $msg['params'] ) && is_array( $msg['params'] ) ? $msg['params'] : array();

		if ( null === $id || '' === $method ) {
			return new WP_REST_Response( null, 202 ); // notification or a response to a server request: accepted, nothing to say
		}
		switch ( $method ) {
			case 'initialize':
				$want = (string) ( $params['protocolVersion'] ?? self::DEFAULT_PROTOCOL );
				$result = array(
					'protocolVersion' => in_array( $want, self::PROTOCOL_VERSIONS, true ) ? $want : self::DEFAULT_PROTOCOL,
					'capabilities'    => array( 'tools' => array( 'listChanged' => false ) ),
					'serverInfo'      => array( 'name' => 'builder-agent-for-divi', 'title' => 'Builder Agent for Divi (' . WPBA_Guard::site_name() . ')', 'version' => WPBA_VERSION ),
					'instructions'    => self::INSTRUCTIONS,
				);
				break;
			case 'ping':
				$result = new stdClass();
				break;
			case 'tools/list':
				$result = array( 'tools' => WPBA_MCP_Tools::definitions() );
				break;
			case 'tools/call':
				$name = (string) ( $params['name'] ?? '' );
				$args = isset( $params['arguments'] ) && is_array( $params['arguments'] ) ? $params['arguments'] : array();
				if ( ! WPBA_MCP_Tools::exists( $name ) ) {
					return self::rpc_error( $id, -32602, "Unknown tool: $name" );
				}
				$result = self::tool_result( WPBA_MCP_Tools::call( $name, $args ) );
				break;
			default:
				return self::rpc_error( $id, -32601, "Method not found: $method" );
		}
		$res = new WP_REST_Response( array( 'jsonrpc' => '2.0', 'id' => $id, 'result' => $result ), 200 );
		$res->header( 'Cache-Control', 'no-store' );
		return $res;
	}

	/** Arrays become JSON text + structuredContent; strings pass through; WP_Error becomes isError. */
	private static function tool_result( $out ) {
		if ( is_wp_error( $out ) ) {
			$data = $out->get_error_data();
			$text = 'Error: ' . $out->get_error_message();
			if ( is_array( $data ) ) {
				foreach ( array( 'missing', 'expected', 'plan', 'run_id' ) as $k ) {
					if ( isset( $data[ $k ] ) ) {
						$text .= "\n" . $k . ': ' . ( is_scalar( $data[ $k ] ) ? $data[ $k ] : wp_json_encode( $data[ $k ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) );
					}
				}
			}
			return array( 'content' => array( array( 'type' => 'text', 'text' => $text ) ), 'isError' => true );
		}
		if ( is_string( $out ) ) {
			return array( 'content' => array( array( 'type' => 'text', 'text' => $out ) ), 'isError' => false );
		}
		$json = wp_json_encode( $out, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT );
		$res  = array( 'content' => array( array( 'type' => 'text', 'text' => $json ) ), 'isError' => false );
		if ( is_array( $out ) && ( array() === $out || array_keys( $out ) !== range( 0, count( $out ) - 1 ) ) ) {
			$res['structuredContent'] = $out ?: new stdClass();
		}
		return $res;
	}
}
