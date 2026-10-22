<?php
/**
 * Component registry: every `rd-*` class defined in a component stylesheet (the plugin's assets/components/
 * folder, or the site's own uploads/builder-agent-for-divi/components/ folder) is allowed as a module css_class.
 * To add a component, write its CSS with an `rd-` class; nothing else can be smuggled in as a class.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class WPBA_Components {

	const CLASS_RE = '/\.(rd-[a-z0-9-]+)/';

	/** @var array|null */
	private static $cache = null;

	public static function site_folder() {
		$u = wp_upload_dir();
		return trailingslashit( $u['basedir'] ) . 'builder-agent-for-divi/components/';
	}

	/** @return string[] stylesheet paths, shared assets first */
	public static function stylesheets() {
		$files = glob( WPBA_DIR . 'assets/components/*.css' ) ?: array();
		sort( $files );
		$site = glob( self::site_folder() . '*.css' ) ?: array();
		sort( $site );
		return array_merge( $files, $site );
	}

	private static function strip_comments( $css ) {
		return preg_replace( '#/\*.*?\*/#s', '', $css );
	}

	/** @return string[] registered class names */
	public static function registered() {
		if ( null !== self::$cache ) {
			return self::$cache;
		}
		$names = array();
		foreach ( self::stylesheets() as $f ) {
			if ( preg_match_all( self::CLASS_RE, self::strip_comments( (string) file_get_contents( $f ) ), $m ) ) {
				foreach ( $m[1] as $n ) {
					$names[ $n ] = true;
				}
			}
		}
		self::$cache = array_keys( $names );
		return self::$cache;
	}

	public static function clear_cache() {
		self::$cache = null;
	}

	/** @return string|WP_Error normalized class list */
	public static function check_classes( $value ) {
		$tokens  = preg_split( '/\s+/', trim( (string) $value ), -1, PREG_SPLIT_NO_EMPTY );
		$unknown = array_diff( $tokens, self::registered() );
		if ( ! $tokens || $unknown ) {
			return new WP_Error( 'wpba_class', 'unknown component class(es): ' . implode( ' ', $unknown ?: array( $value ) ) . '; define them in a component stylesheet first' );
		}
		return implode( ' ', $tokens );
	}

	/** Each stylesheet's leading comment (usage notes) plus the classes it defines, for the page designer. */
	public static function catalogue() {
		$out = array();
		foreach ( self::stylesheets() as $f ) {
			$css = (string) file_get_contents( $f );
			$doc = preg_match( '#^\s*/\*(.*?)\*/#s', $css, $m ) ? trim( $m[1] ) : '';
			preg_match_all( self::CLASS_RE, self::strip_comments( $css ), $c );
			$classes = array_values( array_unique( $c[1] ) );
			sort( $classes );
			$out[] = array( 'file' => basename( $f ), 'usage' => $doc, 'classes' => $classes );
		}
		return $out;
	}

	/** All component CSS as one Theme Options block. */
	public static function bundle() {
		$parts = array( '/* wp-builder-agent: reusable components (bundle). Classes: see each part. */' );
		foreach ( self::stylesheets() as $f ) {
			$css = (string) file_get_contents( $f );
			$css = preg_replace( '#/\* end wp-builder-agent[^*]*\*/#', '', $css );
			$css = preg_replace( '#^/\* wp-builder-agent: reusable components[^*]*\*/#', '', trim( $css ) );
			$parts[] = '/* --- ' . basename( $f ) . " --- */\n" . trim( $css );
		}
		$parts[] = '/* end wp-builder-agent components */';
		return implode( "\n", $parts ) . "\n";
	}
}
