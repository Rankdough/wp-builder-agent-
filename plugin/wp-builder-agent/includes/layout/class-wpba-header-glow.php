<?php
/**
 * Hero glow: Divi's native background gradient (circular) on the first section of a page with a dark header.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class WPBA_Header_Glow {

	const SECTION_OPEN = '/\[et_pb_section((?:\s+[a-z0-9_]+="[^"]*")*)\s*\]/';
	const DARK_DEFAULT = array( '#000000', '#000', '#0a0a0a', '#0b0d10', '#111111', '#14171b' );

	public static function glow_attrs( array $glow ) {
		$hex = ltrim( $glow['color'], '#' );
		$r   = hexdec( substr( $hex, 0, 2 ) );
		$g   = hexdec( substr( $hex, 2, 2 ) );
		$b   = hexdec( substr( $hex, 4, 2 ) );
		return array(
			'use_background_color_gradient'             => 'on',
			'background_color_gradient_type'            => 'circular',
			'background_color_gradient_direction_radial' => $glow['position'],
			'background_color_gradient_stops'           => sprintf( 'rgba(%d,%d,%d,%s) 0%%|rgba(0,0,0,0) %d%%', $r, $g, $b, self::g( $glow['opacity'] ), (int) $glow['fade_at_percent'] ),
			'background_color_gradient_unit'            => '%',
			'background_color_gradient_repeat'          => 'off',
		);
	}

	/** Python's %g for the opacity: 0.28 -> "0.28", 1.0 -> "1". */
	public static function g( $n ) {
		$s = rtrim( rtrim( sprintf( '%.6f', (float) $n ), '0' ), '.' );
		return '' === $s ? '0' : $s;
	}

	/** @return array [new_raw, status]. Only the first section's opening tag changes. */
	public static function add_glow( $raw, array $glow, array $dark = null ) {
		$dark = $dark ? $dark : self::DARK_DEFAULT;
		if ( ! preg_match( self::SECTION_OPEN, $raw, $m, PREG_OFFSET_CAPTURE ) ) {
			return array( $raw, 'skip: no Divi section' );
		}
		$tag   = $m[0][0];
		$start = $m[0][1];
		preg_match_all( '/([a-z0-9_]+)="([^"]*)"/', $m[1][0], $am, PREG_SET_ORDER );
		$attrs = array();
		foreach ( $am as $a ) {
			$attrs[ $a[1] ] = $a[2];
		}
		if ( ( $attrs['use_background_color_gradient'] ?? '' ) === 'on' ) {
			return array( $raw, 'skip: already has a gradient' );
		}
		if ( ! empty( $attrs['background_image'] ) ) {
			return array( $raw, 'skip: section has a background image' );
		}
		$bg = strtolower( $attrs['background_color'] ?? '' );
		if ( ! in_array( $bg, $dark, true ) ) {
			return array( $raw, 'skip: header background ' . ( $bg ? $bg : 'not set' ) . ' is not dark' );
		}
		$extra = '';
		foreach ( self::glow_attrs( $glow ) as $k => $v ) {
			$extra .= ' ' . $k . '="' . $v . '"';
		}
		$new_tag = rtrim( substr( $tag, 0, -1 ) ) . $extra . ']';
		return array( substr( $raw, 0, $start ) . $new_tag . substr( $raw, $start + strlen( $tag ) ), 'change' );
	}
}
