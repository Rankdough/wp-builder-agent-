<?php
/**
 * New components the page designer may define while copying a design. Each is checked before it can be used:
 * every selector must start with its own rd- class (so it can't restyle anything else), no square brackets
 * (they break Divi shortcodes), no imports, no external URLs (only inline data: SVG), no fixed positioning or
 * script-like content. Accepted components are written to uploads/wp-builder-agent/components/<name>.css.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class WPBA_NewComponents {

	const NAME_RE = '/^rd-[a-z0-9]+(-[a-z0-9]+)*$/';

	/** @param array $c { name, usage, css } @return true|WP_Error */
	public static function check( array $c ) {
		$name = isset( $c['name'] ) ? (string) $c['name'] : '';
		$css  = isset( $c['css'] ) ? (string) $c['css'] : '';
		$err  = function ( $m ) {
			return new WP_Error( 'wpba_component', $m );
		};
		if ( ! preg_match( self::NAME_RE, $name ) ) {
			return $err( "'$name': names are rd- plus lowercase words" );
		}
		if ( in_array( $name, WPBA_Components::registered(), true ) ) {
			return $err( "$name already exists; use it instead of redefining it" );
		}
		$css   = preg_replace( '#/\*.*?\*/#s', '', $css );
		$flat  = strtolower( str_replace( ' ', '', $css ) );
		$rules = array(
			'['              => 'square brackets break Divi shortcodes',
			']'              => 'square brackets break Divi shortcodes',
			'@import'        => 'no imports',
			'position:fixed' => 'no fixed positioning',
			'expression('    => 'no script-like CSS',
			'javascript:'    => 'no script-like CSS',
			'</'             => 'no HTML',
		);
		foreach ( $rules as $bad => $why ) {
			if ( false !== strpos( $flat, $bad ) ) {
				return $err( "$name: $why" );
			}
		}
		if ( preg_match_all( '/url\(\s*[\'"]?([^\'")]+)/', $css, $m ) ) {
			foreach ( $m[1] as $url ) {
				if ( 0 !== strpos( $url, 'data:image/svg+xml' ) ) {
					return $err( "$name: only inline data:image/svg+xml URLs are allowed, not " . substr( $url, 0, 40 ) );
				}
			}
		}
		$body = preg_replace( '/@media[^{]*\{/', '', $css );
		if ( preg_match_all( '/([^{}]+)\{/', $body, $m ) ) {
			foreach ( $m[1] as $list ) {
				foreach ( explode( ',', $list ) as $sel ) {
					$sel = trim( $sel );
					if ( '' !== $sel && ! preg_match( '/^\.' . preg_quote( $name, '/' ) . '(--[a-z0-9-]+)?(?![a-z0-9-])/', $sel ) ) {
						return $err( "$name: selector '$sel' must start with .$name" );
					}
				}
			}
		}
		return true;
	}

	/** @return string[]|WP_Error saved paths */
	public static function save( array $comps ) {
		$folder = WPBA_Components::site_folder();
		if ( ! wp_mkdir_p( $folder ) ) {
			return new WP_Error( 'wpba_fs', "Cannot create $folder" );
		}
		$paths = array();
		foreach ( $comps as $c ) {
			$ok = self::check( $c );
			if ( is_wp_error( $ok ) ) {
				return $ok;
			}
			$p = $folder . $c['name'] . '.css';
			file_put_contents( $p, '/* ' . $c['name'] . ': ' . str_replace( '*/', '* /', (string) ( $c['usage'] ?? '' ) ) . " */\n" . trim( $c['css'] ) . "\n" );
			$paths[] = $p;
		}
		WPBA_Components::clear_cache();
		return $paths;
	}
}
