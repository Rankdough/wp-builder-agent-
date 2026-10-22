<?php
/**
 * Clear caches after a change, the way a human would click each plugin's "clear" button.
 * Divi's static CSS cache first (Customizer and Custom CSS changes are compiled into it), then the object
 * cache and whichever page cache is installed. Each step is reported so the run log shows what was cleared.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class WPBA_Cache {

	public static function clear_all() {
		$cleared = array();

		if ( class_exists( 'ET_Core_PageResource' ) && method_exists( 'ET_Core_PageResource', 'remove_static_resources' ) ) {
			ET_Core_PageResource::remove_static_resources( 'all', 'all' );
			$cleared[] = 'divi_static_css';
		}
		if ( function_exists( 'et_core_clear_transients' ) ) {
			et_core_clear_transients();
			$cleared[] = 'divi_transients';
		}
		wp_cache_flush();
		$cleared[] = 'object_cache';

		if ( function_exists( 'wpfc_clear_all_cache' ) ) {
			wpfc_clear_all_cache( true );
			$cleared[] = 'wp_fastest_cache';
		}
		if ( function_exists( 'rocket_clean_domain' ) ) {
			rocket_clean_domain();
			$cleared[] = 'wp_rocket';
		}
		if ( function_exists( 'w3tc_flush_all' ) ) {
			w3tc_flush_all();
			$cleared[] = 'w3_total_cache';
		}
		if ( function_exists( 'wp_cache_clear_cache' ) ) {
			wp_cache_clear_cache();
			$cleared[] = 'wp_super_cache';
		}
		if ( has_action( 'litespeed_purge_all' ) ) {
			do_action( 'litespeed_purge_all' );
			$cleared[] = 'litespeed';
		}
		if ( class_exists( 'autoptimizeCache' ) && method_exists( 'autoptimizeCache', 'clearall' ) ) {
			autoptimizeCache::clearall();
			$cleared[] = 'autoptimize';
		}
		do_action( 'wpba_after_clear_caches', $cleared );
		return $cleared;
	}
}
