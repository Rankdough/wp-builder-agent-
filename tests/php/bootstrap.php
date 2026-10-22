<?php
/**
 * Minimal WordPress stand-ins so the plugin's pure classes (spec, render, restyle, glow, CSS merge, plan
 * validation) can be tested with plain `php tests/php/run.php`. Nothing here touches a database.
 */
define( 'ABSPATH', '/nonexistent/' );
define( 'WPBA_DIR', dirname( __DIR__, 2 ) . '/plugin/builder-agent-for-divi/' );
define( 'WPBA_URL', 'http://example.test/wp-content/plugins/builder-agent-for-divi/' );
define( 'WPBA_VERSION', 'test' );
define( 'WPBA_FILE', WPBA_DIR . 'builder-agent-for-divi.php' );
define( 'WPBA_TEST_UPLOADS', sys_get_temp_dir() . '/wpba-test-uploads' );

class WP_Error {
	public $errors = array();
	public $error_data = array();
	public function __construct( $code = '', $message = '', $data = '' ) {
		if ( $code ) { $this->errors[ $code ][] = $message; if ( $data ) { $this->error_data[ $code ] = $data; } }
	}
	public function get_error_code() { $k = array_keys( $this->errors ); return $k ? $k[0] : ''; }
	public function get_error_message( $code = '' ) { $code = $code ?: $this->get_error_code(); return isset( $this->errors[ $code ] ) ? $this->errors[ $code ][0] : ''; }
	public function get_error_data( $code = '' ) { $code = $code ?: $this->get_error_code(); return $this->error_data[ $code ] ?? null; }
}
function is_wp_error( $t ) { return $t instanceof WP_Error; }
function wp_json_encode( $d, $f = 0 ) { return json_encode( $d, $f ); }
function apply_filters( $tag, $value ) { return $value; }
function do_action() {}
function has_action() { return false; }
function trailingslashit( $s ) { return rtrim( $s, '/\\' ) . '/'; }
function wp_upload_dir() { return array( 'basedir' => WPBA_TEST_UPLOADS, 'baseurl' => 'https://www.example.com/wp-content/uploads' ); }
function wp_mkdir_p( $d ) { return is_dir( $d ) || mkdir( $d, 0777, true ); }
function home_url( $p = '' ) { return 'https://www.example.com' . $p; }
function wp_parse_url( $u, $c = -1 ) { return parse_url( $u, $c ); }
function sanitize_key( $k ) { return preg_replace( '/[^a-z0-9_\-]/', '', strtolower( $k ) ); }
function current_user_can() { return true; }

spl_autoload_register( function ( $class ) {
	if ( strpos( $class, 'WPBA_' ) !== 0 ) { return; }
	$file = 'class-' . strtolower( str_replace( '_', '-', $class ) ) . '.php';
	foreach ( array( 'includes/', 'includes/planner/', 'includes/layout/', 'includes/commands/' ) as $dir ) {
		if ( file_exists( WPBA_DIR . $dir . $file ) ) { require_once WPBA_DIR . $dir . $file; return; }
	}
} );

// --- tiny test runner ---
$GLOBALS['wpba_tests'] = array( 'pass' => 0, 'fail' => 0, 'failures' => array() );
function test( $name, callable $fn ) {
	try { $fn(); $GLOBALS['wpba_tests']['pass']++; echo "  ok  $name\n"; }
	catch ( Throwable $e ) { $GLOBALS['wpba_tests']['fail']++; $GLOBALS['wpba_tests']['failures'][] = $name; echo "FAIL  $name\n      " . $e->getMessage() . "\n"; }
}
function ok( $cond, $msg = 'assertion' ) { if ( ! $cond ) { throw new Exception( $msg ); } }
function eq( $a, $b, $msg = '' ) { if ( $a !== $b ) { throw new Exception( ( $msg ? "$msg: " : '' ) . 'expected ' . var_export( $b, true ) . ' got ' . var_export( $a, true ) ); } }
function contains( $hay, $needle, $msg = '' ) { if ( false === strpos( $hay, $needle ) ) { throw new Exception( ( $msg ? "$msg: " : '' ) . "'$needle' not found in: " . substr( $hay, 0, 400 ) ); } }
function not_contains( $hay, $needle, $msg = '' ) { if ( false !== strpos( $hay, $needle ) ) { throw new Exception( ( $msg ? "$msg: " : '' ) . "'$needle' unexpectedly found" ); } }
function is_err( $r, $match = null ) { if ( ! is_wp_error( $r ) ) { throw new Exception( 'expected WP_Error, got ' . var_export( $r, true ) ); } if ( $match && false === stripos( $r->get_error_message(), $match ) ) { throw new Exception( "error '" . $r->get_error_message() . "' does not match '$match'" ); } }
function no_err( $r ) { if ( is_wp_error( $r ) ) { throw new Exception( 'unexpected error: ' . $r->get_error_message() ); } return $r; }
