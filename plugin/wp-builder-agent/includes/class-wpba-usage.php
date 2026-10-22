<?php
/**
 * Claude API spend: every call is appended to the wpba_usage option with a running total.
 * Prices are USD per million tokens, Anthropic first-party rates (Oct 2026).
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class WPBA_Usage {

	const OPTION = 'wpba_usage';

	const PRICES = array(
		'claude-opus-5-5'   => array( 'input' => 4.00, 'output' => 20.00, 'cache_read' => 0.20, 'cache_write' => 5.00 ),
		'claude-sonnet-5-5' => array( 'input' => 2.00, 'output' => 10.00, 'cache_read' => 0.20, 'cache_write' => 2.50 ),
		'claude-haiku-5-5'  => array( 'input' => 0.10, 'output' => 0.50, 'cache_read' => 0.01, 'cache_write' => 0.125 ),
	);

	public static function cost_usd( $model, array $usage ) {
		$p = isset( self::PRICES[ $model ] ) ? self::PRICES[ $model ] : self::PRICES['claude-opus-5-5'];
		return (
			( (int) ( $usage['input_tokens'] ?? 0 ) ) * $p['input']
			+ ( (int) ( $usage['output_tokens'] ?? 0 ) ) * $p['output']
			+ ( (int) ( $usage['cache_read_input_tokens'] ?? 0 ) ) * $p['cache_read']
			+ ( (int) ( $usage['cache_creation_input_tokens'] ?? 0 ) ) * $p['cache_write']
		) / 1000000;
	}

	public static function record( $model, array $usage, $purpose, $run_id = null ) {
		$entry = array(
			't'                 => time(),
			'model'             => $model,
			'purpose'           => $purpose,
			'run_id'            => $run_id,
			'input_tokens'      => (int) ( $usage['input_tokens'] ?? 0 ),
			'output_tokens'     => (int) ( $usage['output_tokens'] ?? 0 ),
			'cache_read_tokens' => (int) ( $usage['cache_read_input_tokens'] ?? 0 ),
			'usd'               => round( self::cost_usd( $model, $usage ), 4 ),
		);
		$log   = get_option( self::OPTION, array() );
		$log   = is_array( $log ) ? $log : array();
		$log[] = $entry;
		if ( count( $log ) > 2000 ) {
			$log = array_slice( $log, -2000 );
		}
		update_option( self::OPTION, $log, 'no' );
		return $entry;
	}

	public static function total_usd() {
		$log = get_option( self::OPTION, array() );
		$sum = 0.0;
		foreach ( (array) $log as $e ) {
			$sum += (float) ( $e['usd'] ?? 0 );
		}
		return round( $sum, 4 );
	}

	public static function recent( $n = 20 ) {
		$log = get_option( self::OPTION, array() );
		return array_reverse( array_slice( (array) $log, -$n ) );
	}
}
