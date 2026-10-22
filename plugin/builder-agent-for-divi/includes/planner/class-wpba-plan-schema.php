<?php
/**
 * Change plan schema. The planner must return this; code validates it before anything is applied.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class WPBA_Plan_Schema {

	// Highest rung first. The planner must use the first rung that works and log why higher ones were skipped.
	const EDIT_LADDER = array(
		'theme_options_or_customizer',
		'global_colours_or_presets',
		'theme_builder_template',
		'library_layout_or_global_module',
		'module_settings',
		'module_custom_css', // last resort: explicit approval + logged reason
		'theme_custom_css',  // last resort: explicit approval + logged reason
	);
	const CSS_RUNGS = array( 'module_custom_css', 'theme_custom_css' );

	const SETTING_ID = '/^[a-z0-9_]+(\[[a-z0-9_]+\])?$/';

	/** JSON schema for Claude's structured output. */
	public static function json_schema() {
		$str = array( 'type' => 'string' );
		return array(
			'type'                 => 'object',
			'additionalProperties' => false,
			'required'             => array( 'task', 'feasible', 'rung', 'skipped_rungs', 'changes', 'verify', 'pages_affected', 'side_effects', 'blocked_reason' ),
			'properties'           => array(
				'task'           => $str,
				'feasible'       => array( 'type' => 'boolean', 'description' => 'False if the task cannot be done with the supported actions' ),
				'rung'           => array( 'type' => array( 'string', 'null' ), 'enum' => array_merge( self::EDIT_LADDER, array( null ) ) ),
				'skipped_rungs'  => array( 'type' => 'array', 'items' => $str, 'description' => 'Why each higher rung was not used' ),
				'changes'        => array(
					'type'  => 'array',
					'items' => array(
						'type'                 => 'object',
						'additionalProperties' => false,
						'required'             => array( 'action', 'setting', 'old_value', 'new_value', 'reason' ),
						'properties'           => array(
							'action'    => array( 'type' => 'string', 'enum' => array( 'customizer_set' ) ),
							'setting'   => array( 'type' => 'string', 'description' => 'Customizer setting id, e.g. et_divi[all_buttons_bg_color]' ),
							'old_value' => array( 'type' => 'string', 'description' => 'Current value exactly as given in the context' ),
							'new_value' => $str,
							'reason'    => $str,
						),
					),
				),
				'verify'         => array(
					'type'  => 'array',
					'items' => array(
						'type'                 => 'object',
						'additionalProperties' => false,
						'required'             => array( 'page', 'selector', 'css_property', 'expected' ),
						'properties'           => array(
							'page'         => array( 'type' => 'string', 'description' => 'Front-end path starting with /' ),
							'selector'     => array( 'type' => 'string', 'description' => 'CSS selector of the element to measure, e.g. .et_pb_button_0' ),
							'css_property' => array( 'type' => 'string', 'description' => 'Computed style property, e.g. background-color, border-radius' ),
							'expected'     => array( 'type' => 'string', 'description' => 'Expected computed value, e.g. #ff8a3d or 6px' ),
						),
					),
				),
				'pages_affected' => array( 'type' => 'array', 'items' => $str ),
				'side_effects'   => array( 'type' => 'array', 'items' => $str, 'description' => 'What else changes, and what will NOT change' ),
				'blocked_reason' => array( 'type' => array( 'string', 'null' ) ),
			),
		);
	}

	/** Fill defaults and coerce types so a hand-written plan JSON and a Claude plan look the same. */
	public static function normalize( array $plan ) {
		$plan += array(
			'task'           => '',
			'feasible'       => false,
			'rung'           => null,
			'skipped_rungs'  => array(),
			'changes'        => array(),
			'verify'         => array(),
			'pages_affected' => array(),
			'side_effects'   => array(),
			'blocked_reason' => null,
		);
		$plan['feasible'] = (bool) $plan['feasible'];
		foreach ( array( 'skipped_rungs', 'changes', 'verify', 'pages_affected', 'side_effects' ) as $k ) {
			$plan[ $k ] = array_values( (array) $plan[ $k ] );
		}
		return $plan;
	}

	/**
	 * Reject plans that touch unknown settings, misstate current values or use CSS without approval.
	 * @return true|WP_Error
	 */
	public static function validate( array $plan, array $customizer, $allow_css = false ) {
		$plan = self::normalize( $plan );
		$err  = function ( $msg ) {
			return new WP_Error( 'wpba_plan', $msg );
		};
		if ( ! $plan['feasible'] ) {
			return $plan['changes'] ? $err( 'Infeasible plan must not contain changes' ) : true;
		}
		if ( ! $plan['changes'] ) {
			return $err( 'Feasible plan has no changes' );
		}
		if ( $plan['rung'] && ! in_array( $plan['rung'], self::EDIT_LADDER, true ) ) {
			return $err( 'Unknown rung: ' . $plan['rung'] );
		}
		if ( in_array( $plan['rung'], self::CSS_RUNGS, true ) && ! $allow_css ) {
			return $err( "Plan uses CSS rung '{$plan['rung']}'; needs explicit allow-css approval" );
		}
		if ( ! $plan['verify'] ) {
			return $err( 'Plan has no verification checks' );
		}
		$seen = array();
		foreach ( $plan['changes'] as $c ) {
			if ( ! isset( $c['action'], $c['setting'], $c['new_value'] ) || 'customizer_set' !== $c['action'] ) {
				return $err( 'Each change needs action=customizer_set, setting and new_value' );
			}
			$id = (string) $c['setting'];
			if ( ! preg_match( self::SETTING_ID, $id ) ) {
				return $err( "Invalid setting id: '$id'" );
			}
			if ( ! array_key_exists( $id, $customizer ) ) {
				return $err( "Unknown Customizer setting: $id" );
			}
			if ( isset( $seen[ $id ] ) ) {
				return $err( "Setting changed twice: $id" );
			}
			$seen[ $id ] = true;
			$current     = WPBA_Divi::current_value( $customizer, $id );
			$old         = isset( $c['old_value'] ) ? (string) $c['old_value'] : '';
			if ( $current !== $old ) {
				return $err( "$id: plan says old value '$old', site has '$current'" );
			}
			if ( preg_match( '/[<>{};]/', (string) $c['new_value'] ) ) {
				return $err( "$id: new value looks like code: '{$c['new_value']}'" );
			}
		}
		foreach ( $plan['verify'] as $v ) {
			if ( ! isset( $v['page'] ) || '/' !== substr( (string) $v['page'], 0, 1 ) ) {
				return $err( 'Verify page must be a path starting with /' );
			}
		}
		return true;
	}
}
