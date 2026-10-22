<?php
/**
 * Front-end verification. Computed styles need a browser, so those checks run in the admin screen: the page
 * is loaded in a same-origin iframe and getComputedStyle is read there, then the results are recorded here.
 * Server-side checks fetch the page as a logged-out visitor and look at the HTML and inline CSS.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class WPBA_Verify {

	/** Turn #rgb, #rrggbb, rgb() and rgba(...,1) into rgb(r, g, b); keep other values trimmed. */
	public static function normalize( $value ) {
		$v = strtolower( trim( (string) $value ) );
		if ( preg_match( '/^#([0-9a-f]{3}|[0-9a-f]{6})$/', $v, $m ) ) {
			$h = $m[1];
			if ( 3 === strlen( $h ) ) {
				$h = $h[0] . $h[0] . $h[1] . $h[1] . $h[2] . $h[2];
			}
			return sprintf( 'rgb(%d, %d, %d)', hexdec( substr( $h, 0, 2 ) ), hexdec( substr( $h, 2, 2 ) ), hexdec( substr( $h, 4, 2 ) ) );
		}
		if ( preg_match( '/^rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)$/', $v, $m ) ) {
			if ( ! isset( $m[4] ) || '' === $m[4] || 1.0 === (float) $m[4] ) {
				return sprintf( 'rgb(%d, %d, %d)', $m[1], $m[2], $m[3] );
			}
			return sprintf( 'rgba(%d, %d, %d, %s)', $m[1], $m[2], $m[3], WPBA_Header_Glow::g( $m[4] ) );
		}
		return $v;
	}

	/** Compare a measured value with the expected one. */
	public static function passes( $expected, $actual ) {
		return null !== $actual && self::normalize( $actual ) === self::normalize( $expected );
	}

	/** Fetch a front-end path as a visitor (no cookies), cache-busted. @return string|WP_Error HTML */
	public static function fetch_front( $path ) {
		$url = home_url( $path );
		$url .= ( false === strpos( $url, '?' ) ? '?' : '&' ) . 'wpagent=' . time();
		$r   = wp_remote_get( $url, array( 'timeout' => 60, 'sslverify' => apply_filters( 'wpba_sslverify', true ) ) );
		if ( is_wp_error( $r ) ) {
			return $r;
		}
		$code = (int) wp_remote_retrieve_response_code( $r );
		if ( 200 !== $code ) {
			return new WP_Error( 'wpba_front', "Front end returned HTTP $code for $path" );
		}
		return (string) wp_remote_retrieve_body( $r );
	}

	/**
	 * Does the front end serve this string? Looks in the page HTML and, because Divi can move module styles into
	 * static files under wp-content/et-cache/, in every stylesheet the page links from there.
	 * @return bool|WP_Error
	 */
	public static function front_contains( $path, $needle ) {
		$html = self::fetch_front( $path );
		if ( is_wp_error( $html ) ) {
			return $html;
		}
		if ( false !== strpos( $html, $needle ) ) {
			return true;
		}
		if ( preg_match_all( '/<link[^>]+href=["\']([^"\']*et-cache[^"\']*\.css[^"\']*)["\']/i', $html, $m ) ) {
			foreach ( array_unique( $m[1] ) as $href ) {
				$css = wp_remote_get( html_entity_decode( $href ), array( 'timeout' => 30 ) );
				if ( ! is_wp_error( $css ) && false !== strpos( (string) wp_remote_retrieve_body( $css ), $needle ) ) {
					return true;
				}
			}
		}
		return false;
	}

	/** Record browser-measured computed-style results against a run. */
	public static function record( WPBA_RunLog $log, array $results ) {
		$clean = array();
		foreach ( $results as $r ) {
			$row = array(
				'page'     => (string) ( $r['page'] ?? '' ),
				'selector' => (string) ( $r['selector'] ?? '' ),
				'property' => (string) ( $r['property'] ?? '' ),
				'expected' => (string) ( $r['expected'] ?? '' ),
				'actual'   => isset( $r['actual'] ) ? (string) $r['actual'] : null,
			);
			$row['pass'] = self::passes( $row['expected'], $row['actual'] );
			$clean[]     = $row;
			$log->event( 'verify', $row );
		}
		$log->write_json( 'verify', $clean );
		$ok = $clean && ! in_array( false, array_column( $clean, 'pass' ), true );
		update_post_meta( $log->id, '_wpba_verified', $ok ? 'pass' : 'fail' );
		return array( 'pass' => $ok, 'results' => $clean );
	}
}
