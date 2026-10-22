<?php
/**
 * Admin screen: one page under the top-level "Builder Agent" menu, driven by admin/js/admin.js over REST.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class WPBA_Admin {

	const SLUG = 'wp-builder-agent';

	public static function init() {
		add_action( 'admin_menu', array( __CLASS__, 'menu' ) );
		add_action( 'admin_enqueue_scripts', array( __CLASS__, 'assets' ) );
		add_action( 'admin_notices', array( __CLASS__, 'notices' ) );
		add_filter( 'plugin_action_links_' . plugin_basename( WPBA_FILE ), array( __CLASS__, 'action_links' ) );
	}

	public static function menu() {
		add_menu_page( 'WP Builder Agent', 'Builder Agent', WPBA_Plugin::CAPABILITY, self::SLUG, array( __CLASS__, 'render' ), 'dashicons-hammer', 61 );
	}

	public static function action_links( $links ) {
		array_unshift( $links, '<a href="' . esc_url( admin_url( 'admin.php?page=' . self::SLUG ) ) . '">Open</a>' );
		return $links;
	}

	public static function notices() {
		$screen = function_exists( 'get_current_screen' ) ? get_current_screen() : null;
		if ( ! $screen || false === strpos( (string) $screen->id, self::SLUG ) ) {
			return;
		}
		if ( ! WPBA_Plugin::divi_present() ) {
			echo '<div class="notice notice-warning"><p><strong>WP Builder Agent:</strong> Divi 4 is not active. The agent reads and writes Divi\'s own settings and layouts, so most commands will have nothing to work on.</p></div>';
		}
		if ( 'missing' === WPBA_Settings::key_source() ) {
			echo '<div class="notice notice-info"><p><strong>WP Builder Agent:</strong> no Anthropic API key yet. Planning and rebuilds need one; snapshots, header glow, restyle and Custom CSS work without it.</p></div>';
		}
	}

	public static function assets( $hook ) {
		if ( false === strpos( (string) $hook, self::SLUG ) ) {
			return;
		}
		wp_enqueue_style( 'wpba-admin', WPBA_URL . 'admin/css/admin.css', array(), WPBA_VERSION );
		wp_enqueue_script( 'wpba-admin', WPBA_URL . 'admin/js/admin.js', array( 'wp-api-fetch' ), WPBA_VERSION, true );
		wp_localize_script(
			'wpba-admin',
			'wpbaData',
			array(
				'rest'     => esc_url_raw( rest_url( WPBA_Rest::NS ) ),
				'nonce'    => wp_create_nonce( 'wp_rest' ),
				'site'     => WPBA_Guard::site_name(),
				'home'     => home_url(),
				'settings' => WPBA_Settings::public_view(),
				'profile'  => WPBA_Settings::profile(),
				'divi'     => WPBA_Plugin::divi_present(),
				'models'   => WPBA_Settings::MODELS,
				'efforts'  => WPBA_Settings::EFFORT,
				'themes'   => array_keys( WPBA_Restyle::themes() ),
			)
		);
	}

	public static function render() {
		if ( ! current_user_can( WPBA_Plugin::CAPABILITY ) ) {
			wp_die( 'Sorry, you are not allowed to access this page.' );
		}
		$tabs = array(
			'plan'      => 'Plan & apply',
			'pages'     => 'Page rebuilds',
			'sitewide'  => 'Site-wide',
			'css'       => 'CSS & components',
			'runs'      => 'Runs',
			'settings'  => 'Settings',
		);
		?>
		<div class="wrap wpba-wrap" id="wpba-app">
			<h1>WP Builder Agent <small class="wpba-site"><?php echo esc_html( WPBA_Guard::site_name() ); ?></small></h1>
			<p class="wpba-intro">Plans are shown before anything is saved. Every write backs up first, clears caches after, and is recorded as a run. Production writes need the site name typed as confirmation.</p>
			<nav class="nav-tab-wrapper wpba-tabs">
				<?php foreach ( $tabs as $id => $label ) : ?>
					<a href="#<?php echo esc_attr( $id ); ?>" class="nav-tab" data-tab="<?php echo esc_attr( $id ); ?>"><?php echo esc_html( $label ); ?></a>
				<?php endforeach; ?>
			</nav>
			<div id="wpba-panels"><div class="wpba-loading">Loading…</div></div>
			<div id="wpba-iframes" aria-hidden="true"></div>
		</div>
		<?php
	}
}
