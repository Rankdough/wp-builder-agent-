<?php
/**
 * Plugin settings and the site profile. The API key can also come from wp-config.php:
 *   define( 'WPBA_ANTHROPIC_API_KEY', 'sk-ant-...' );
 * which keeps it out of the database.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class WPBA_Settings {

	const OPTION  = 'wpba_settings';
	const PROFILE = 'wpba_site_profile';

	const MODELS = array( 'claude-opus-5-5', 'claude-sonnet-5-5', 'claude-haiku-5-5' );
	const EFFORT = array( 'low', 'medium', 'high', 'xhigh', 'max' );

	public static function defaults() {
		return array(
			'api_key'    => '',
			'model'      => 'claude-opus-5-5',
			'effort'     => 'high',
			'fallbacks'  => true,
			'is_staging' => false,
			'allow_css'  => false,
			'pages'      => array( '/' ),
		);
	}

	public static function all() {
		$saved = get_option( self::OPTION, array() );
		return array_merge( self::defaults(), is_array( $saved ) ? $saved : array() );
	}

	public static function get( $key ) {
		$all = self::all();
		return isset( $all[ $key ] ) ? $all[ $key ] : null;
	}

	/** Validate and store; returns the stored settings. The key is never echoed back in full. */
	public static function update( array $in ) {
		$cur = self::all();
		if ( array_key_exists( 'api_key', $in ) ) {
			$key = trim( (string) $in['api_key'] );
			if ( '' !== $key && ! preg_match( '/^sk-ant-[A-Za-z0-9_\-]{20,}$/', $key ) ) {
				return new WP_Error( 'wpba_bad_key', 'That does not look like an Anthropic API key (sk-ant-...).' );
			}
			if ( '' !== $key || empty( $in['keep_key'] ) ) {
				$cur['api_key'] = $key;
			}
		}
		if ( isset( $in['model'] ) && in_array( $in['model'], self::MODELS, true ) ) {
			$cur['model'] = $in['model'];
		}
		if ( isset( $in['effort'] ) && in_array( $in['effort'], self::EFFORT, true ) ) {
			$cur['effort'] = $in['effort'];
		}
		foreach ( array( 'fallbacks', 'is_staging', 'allow_css' ) as $flag ) {
			if ( array_key_exists( $flag, $in ) ) {
				$cur[ $flag ] = (bool) $in[ $flag ];
			}
		}
		if ( isset( $in['pages'] ) ) {
			$pages = is_array( $in['pages'] ) ? $in['pages'] : explode( ',', (string) $in['pages'] );
			$pages = array_values( array_filter( array_map( 'trim', $pages ) ) );
			foreach ( $pages as $p ) {
				if ( '/' !== substr( $p, 0, 1 ) ) {
					return new WP_Error( 'wpba_bad_page', "Page paths must start with '/': $p" );
				}
			}
			$cur['pages'] = $pages ? $pages : array( '/' );
		}
		update_option( self::OPTION, $cur, 'no' );
		return $cur;
	}

	/** The API key to use: wp-config constant first, then the stored setting. */
	public static function api_key() {
		if ( defined( 'WPBA_ANTHROPIC_API_KEY' ) && WPBA_ANTHROPIC_API_KEY ) {
			return WPBA_ANTHROPIC_API_KEY;
		}
		return (string) self::get( 'api_key' );
	}

	public static function key_source() {
		if ( defined( 'WPBA_ANTHROPIC_API_KEY' ) && WPBA_ANTHROPIC_API_KEY ) {
			return 'wp-config';
		}
		return self::get( 'api_key' ) ? 'settings' : 'missing';
	}

	/** Public view of the settings: key masked. */
	public static function public_view() {
		$all = self::all();
		$key = $all['api_key'];
		$all['api_key_masked'] = $key ? substr( $key, 0, 10 ) . '…' . substr( $key, -4 ) : '';
		$all['api_key_source'] = self::key_source();
		unset( $all['api_key'] );
		return $all;
	}

	// --- Site profile: learned, non-secret facts (design tokens, hero glow, dark header colours). ---

	public static function profile_defaults() {
		return array(
			'platform'           => array( 'notes' => '' ),
			'design_tokens'      => array(
				'brand_color'      => '#e02b20',
				'card_surface'     => '#14171b',
				'card_border'      => '#23272d',
				'muted_text'       => '#b8bec6',
				'content_width_px' => 1120,
				'hero_glow'        => array(
					'color'           => '#e02b20',
					'opacity'         => 0.28,
					'position'        => 'top right',
					'fade_at_percent' => 55,
				),
			),
			'dark_header_colors' => array( '#000000', '#0a0a0a', '#14171b' ),
			'components'         => array(
				'rd-pills'              => 'Text/Blurb module CSS class: a bullet list renders as pills',
				'rd-pills rd-pills--red' => 'Uppercase monospace tag pills',
				'rd-steps'              => 'Numbered list with red number circles; put an h3 + p inside each li',
			),
		);
	}

	public static function profile() {
		$saved = get_option( self::PROFILE, null );
		if ( ! is_array( $saved ) ) {
			return self::profile_defaults();
		}
		return $saved;
	}

	public static function update_profile( $json_or_array ) {
		$data = is_array( $json_or_array ) ? $json_or_array : json_decode( (string) $json_or_array, true );
		if ( ! is_array( $data ) ) {
			return new WP_Error( 'wpba_bad_profile', 'Site profile must be a JSON object.' );
		}
		update_option( self::PROFILE, $data, 'no' );
		return $data;
	}

	public static function hero_glow() {
		$p = self::profile();
		return isset( $p['design_tokens']['hero_glow'] ) ? $p['design_tokens']['hero_glow'] : null;
	}

	public static function dark_header_colors() {
		$p = self::profile();
		return array_map( 'strtolower', isset( $p['dark_header_colors'] ) ? (array) $p['dark_header_colors'] : array() );
	}
}
