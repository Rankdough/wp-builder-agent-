<?php
/**
 * Theme Options > Custom CSS: our component block replaces its earlier version and never touches other CSS.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class WPBA_Theme_CSS {

	const BLOCK_START = '/* wp-builder-agent: reusable components';
	const BLOCK_END   = '/* end wp-builder-agent components */';

	public static function merge_block( $before, $block ) {
		$start = strpos( $before, self::BLOCK_START );
		if ( false === $start ) {
			return ( trim( $before ) !== '' ? rtrim( $before ) . "\n\n" : '' ) . $block . "\n";
		}
		$end  = strpos( $before, self::BLOCK_END, $start );
		$tail = false !== $end ? substr( $before, $end + strlen( self::BLOCK_END ) ) : ''; // v1 had no end marker
		return substr( $before, 0, $start ) . $block . ( trim( $tail ) !== '' ? "\n" . ltrim( $tail, "\n" ) : "\n" );
	}
}
