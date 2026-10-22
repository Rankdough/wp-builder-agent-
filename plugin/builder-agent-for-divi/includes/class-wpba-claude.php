<?php
/**
 * Claude Messages API client over the WordPress HTTP API.
 *
 * A WordPress plugin is distributed without a Composer vendor tree, so this is a small raw-HTTP client rather
 * than the Anthropic PHP SDK. It supports what the agent needs: a system prompt, messages, adaptive thinking
 * with an effort level, structured output against a JSON schema, and the server-side refusal fallback.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class WPBA_Claude {

	const ENDPOINT    = 'https://api.anthropic.com/v1/messages';
	const API_VERSION = '2026-10-21';

	/**
	 * @param array $args {
	 *   system, messages, max_tokens, schema (JSON schema for structured output), purpose, run_id, model, effort
	 * }
	 * @return array|WP_Error { text, json, usage, stop_reason, stop_details, model, raw }
	 */
	public static function messages( array $args ) {
		$key = WPBA_Settings::api_key();
		if ( ! $key ) {
			return new WP_Error( 'wpba_no_key', 'No Anthropic API key. Add it under Builder Agent for Divi > Settings or define WPBA_ANTHROPIC_API_KEY in wp-config.php.' );
		}
		$model  = $args['model'] ?? WPBA_Settings::get( 'model' );
		$effort = $args['effort'] ?? WPBA_Settings::get( 'effort' );

		$body = array(
			'model'         => $model,
			'max_tokens'    => (int) ( $args['max_tokens'] ?? 16000 ),
			'messages'      => $args['messages'],
			'output_config' => array( 'effort' => $effort ),
		);
		if ( ! empty( $args['system'] ) ) {
			$body['system'] = $args['system'];
		}
		if ( ! empty( $args['schema'] ) ) {
			$body['output_config']['format'] = array(
				'type'   => 'json_schema',
				'schema' => $args['schema'],
			);
		}
		$headers = array(
			'content-type'      => 'application/json',
			'x-api-key'         => $key,
			'anthropic-version' => self::API_VERSION,
		);
		if ( WPBA_Settings::get( 'fallbacks' ) && 'claude-haiku-5-5' !== $model ) {
			// A safety-classifier refusal is re-run server-side on Anthropic's recommended fallback model.
			$body['fallbacks']         = 'default';
			$headers['anthropic-beta'] = 'server-side-fallback-2026-07-01';
		}

		// A page design can take several minutes; don't let PHP's own limit cut the request short.
		if ( function_exists( 'set_time_limit' ) ) {
			@set_time_limit( 0 ); // phpcs:ignore Squiz.PHP.DiscouragedFunctions.Discouraged, WordPress.PHP.NoSilencedErrors.Discouraged -- long Claude responses; admin-only request.
		}
		$response = wp_remote_post(
			self::ENDPOINT,
			array(
				'headers' => $headers,
				'body'    => wp_json_encode( $body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ),
				'timeout' => (int) apply_filters( 'wpba_api_timeout', 600 ),
			)
		);
		if ( is_wp_error( $response ) ) {
			return new WP_Error( 'wpba_api_connection', 'Could not reach the Claude API: ' . $response->get_error_message() );
		}
		$code = (int) wp_remote_retrieve_response_code( $response );
		$data = json_decode( wp_remote_retrieve_body( $response ), true );
		if ( 200 !== $code ) {
			$msg = isset( $data['error']['message'] ) ? $data['error']['message'] : wp_remote_retrieve_body( $response );
			$why = 429 === $code ? 'Rate limited' : ( $code >= 500 ? 'Claude API server error' : 'Claude API rejected the request' );
			return new WP_Error( 'wpba_api_' . $code, "$why (HTTP $code): " . substr( (string) $msg, 0, 500 ), array( 'status' => $code ) );
		}
		if ( ! is_array( $data ) || empty( $data['content'] ) ) {
			return new WP_Error( 'wpba_api_shape', 'Unexpected response from the Claude API.' );
		}

		$usage = isset( $data['usage'] ) ? (array) $data['usage'] : array();
		$entry = WPBA_Usage::record( (string) ( $data['model'] ?? $model ), $usage, (string) ( $args['purpose'] ?? 'call' ), $args['run_id'] ?? null );

		$stop = (string) ( $data['stop_reason'] ?? '' );
		if ( 'refusal' === $stop ) {
			$d = isset( $data['stop_details'] ) ? $data['stop_details'] : array();
			return new WP_Error( 'wpba_refusal', 'Claude declined this request' . ( isset( $d['explanation'] ) ? ': ' . $d['explanation'] : '.' ) );
		}
		if ( 'max_tokens' === $stop ) {
			return new WP_Error( 'wpba_max_tokens', 'Claude ran out of output tokens; raise max_tokens.' );
		}

		$text = '';
		foreach ( $data['content'] as $block ) {
			if ( isset( $block['type'] ) && 'text' === $block['type'] ) {
				$text .= $block['text'];
			}
		}
		$json = null;
		if ( ! empty( $args['schema'] ) ) {
			$json = json_decode( $text, true );
			if ( ! is_array( $json ) ) {
				return new WP_Error( 'wpba_api_json', 'Structured output was not valid JSON.' );
			}
		}
		return array(
			'text'         => $text,
			'json'         => $json,
			'usage'        => $entry,
			'stop_reason'  => $stop,
			'stop_details' => $data['stop_details'] ?? null,
			'model'        => $data['model'] ?? $model,
		);
	}

	/** Pull a JSON object out of a prose reply (used where the schema is too large for strict output). */
	public static function extract_json( $text ) {
		if ( preg_match( '/```(?:json)?\s*(\{.*\})\s*```/s', $text, $m ) ) {
			return $m[1];
		}
		$a = strpos( $text, '{' );
		$b = strrpos( $text, '}' );
		return ( false === $a || false === $b ) ? $text : substr( $text, $a, $b - $a + 1 );
	}
}
