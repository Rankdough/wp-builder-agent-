<?php
/**
 * Plugin Name:       Builder Agent for Divi
 * Plugin URI:        https://www.rankdough.com/builder-agent-for-divi/
 * Description:       Edits a Divi 4 site the way a careful human would: plans reviewed before they are applied, native-module page rebuilds into drafts, backups before every write, verification after. Connects to Claude as an MCP server.
 * Version:           0.1.0
 * Requires at least: 6.0
 * Requires PHP:      7.4
 * Author:            Rank Dough
 * Author URI:        https://www.rankdough.com
 * License:           GPLv2 or later
 * License URI:       https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain:       builder-agent-for-divi
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

define( 'WPBA_VERSION', '0.1.0' );
define( 'WPBA_FILE', __FILE__ );
define( 'WPBA_DIR', plugin_dir_path( __FILE__ ) );
define( 'WPBA_URL', plugin_dir_url( __FILE__ ) );

/**
 * Class autoloader: WPBA_Foo_Bar -> includes/(subdir/)class-wpba-foo-bar.php
 */
spl_autoload_register(
	function ( $class ) {
		if ( strpos( $class, 'WPBA_' ) !== 0 ) {
			return;
		}
		$file = 'class-' . strtolower( str_replace( '_', '-', $class ) ) . '.php';
		foreach ( array( 'includes/', 'includes/planner/', 'includes/layout/', 'includes/commands/' ) as $dir ) {
			if ( file_exists( WPBA_DIR . $dir . $file ) ) {
				require_once WPBA_DIR . $dir . $file;
				return;
			}
		}
	}
);

register_activation_hook( __FILE__, array( 'WPBA_Plugin', 'activate' ) );
register_deactivation_hook( __FILE__, array( 'WPBA_Plugin', 'deactivate' ) );

add_action( 'plugins_loaded', array( 'WPBA_Plugin', 'instance' ) );
