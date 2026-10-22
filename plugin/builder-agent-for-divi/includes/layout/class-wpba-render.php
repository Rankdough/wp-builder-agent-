<?php
/**
 * Render a validated spec into Divi 4's layout format (the same format Portability exports).
 * Attribute names follow Divi 4.27.4 as stored by the builder.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class WPBA_Render {

	const V = '4.27.4';

	/** Divi encodes quotes and brackets inside shortcode attributes like this. */
	public static function attr( $value ) {
		return str_replace( array( '"', '[', ']', '<', '>' ), array( '%22', '%91', '%93', '%3C', '%3E' ), (string) $value );
	}

	private static function attrs( array $d ) {
		$out = array();
		foreach ( $d as $k => $v ) {
			if ( null === $v || '' === $v ) {
				continue;
			}
			$out[] = $k . '="' . self::attr( is_bool( $v ) ? ( $v ? 'on' : 'off' ) : $v ) . '"';
		}
		return implode( ' ', $out );
	}

	private static function px( $v ) {
		return null === $v ? null : $v . 'px';
	}

	private static function box( array $b ) {
		$a = array( 'background_color' => $b['background_color'] ?? null );
		if ( ! empty( $b['padding'] ) ) {
			list( $t, $r, $bt, $l ) = $b['padding'];
			$a['custom_padding'] = "{$t}px|{$r}px|{$bt}px|{$l}px|false|false";
		}
		if ( isset( $b['margin_bottom'] ) ) {
			$a['custom_margin'] = '||' . $b['margin_bottom'] . 'px||false|false';
		}
		if ( isset( $b['border_width'] ) ) {
			$a['border_width_all'] = $b['border_width'] . 'px';
		}
		$a['border_color_all'] = $b['border_color'] ?? null;
		$a['border_style_all'] = $b['border_style'] ?? null;
		if ( isset( $b['border_radius'] ) ) {
			$r               = $b['border_radius'];
			$a['border_radii'] = "on|{$r}px|{$r}px|{$r}px|{$r}px";
		}
		return $a;
	}

	private static function module( array $m ) {
		$base = array( '_builder_version' => self::V, '_module_preset' => 'default' );
		$g    = function ( $k ) use ( $m ) {
			return isset( $m[ $k ] ) ? $m[ $k ] : null;
		};
		switch ( $m['type'] ) {
			case 'text':
				$a = array_merge( $base, self::box( $m ), array(
					'text_text_color'     => $g( 'text_color' ),
					'text_font_size'      => self::px( $g( 'font_size' ) ),
					'text_line_height'    => $g( 'line_height_em' ) ? $g( 'line_height_em' ) . 'em' : null,
					'header_text_color'   => $g( 'heading_color' ),
					'header_font_size'    => self::px( $g( 'h1_size' ) ),
					'header_2_text_color' => $g( 'heading_color' ),
					'header_2_font_size'  => self::px( $g( 'h2_size' ) ),
					'header_3_text_color' => $g( 'heading_color' ),
					'header_3_font_size'  => self::px( $g( 'h3_size' ) ),
					'text_orientation'    => $g( 'align' ),
					'module_class'        => $g( 'css_class' ),
				) );
				return '[et_pb_text ' . self::attrs( $a ) . ']' . $m['html'] . '[/et_pb_text]';
			case 'button':
				$custom = false;
				foreach ( array( 'text_color', 'bg_color', 'border_color', 'border_width', 'border_radius', 'font_size' ) as $k ) {
					if ( null !== $g( $k ) ) {
						$custom = true;
					}
				}
				$arrow = ! empty( $m['show_arrow'] );
				$a     = array_merge( $base, array(
					'button_text'          => $m['text'],
					'button_url'           => $m['url'],
					'url_new_window'       => ! empty( $m['new_window'] ) ? 'on' : 'off',
					'button_alignment'     => $g( 'align' ),
					'custom_button'        => $custom ? 'on' : 'off',
					'button_text_color'    => $g( 'text_color' ),
					'button_bg_color'      => $g( 'bg_color' ),
					'button_border_color'  => $g( 'border_color' ),
					'button_border_width'  => self::px( $g( 'border_width' ) ),
					'button_border_radius' => self::px( $g( 'border_radius' ) ),
					'button_text_size'     => self::px( $g( 'font_size' ) ),
					'button_use_icon'      => $arrow ? 'on' : ( $custom ? 'off' : null ),
					'button_on_hover'      => $arrow ? 'off' : null,
				) );
				return '[et_pb_button ' . self::attrs( $a ) . '][/et_pb_button]';
			case 'image':
				$a = array_merge( $base, self::box( $m ), array( 'src' => $m['src'], 'alt' => $m['alt'], 'title_text' => $g( 'title' ) ?: $m['alt'] ) );
				return '[et_pb_image ' . self::attrs( $a ) . '][/et_pb_image]';
			case 'blurb':
				$a = array_merge( $base, self::box( $m ), array(
					'title'             => $m['title'],
					'use_icon'          => 'off',
					'header_level'      => 'h3',
					'header_text_color' => $g( 'title_color' ),
					'header_font_size'  => self::px( $g( 'title_size' ) ),
					'body_text_color'   => $g( 'text_color' ),
					'body_font_size'    => self::px( $g( 'font_size' ) ),
					'module_class'      => $g( 'css_class' ),
				) );
				return '[et_pb_blurb ' . self::attrs( $a ) . ']' . $m['body_html'] . '[/et_pb_blurb]';
			case 'toggle':
				$a = array_merge( $base, self::box( $m ), array(
					'title'                         => $m['title'],
					'title_level'                   => 'h3',
					'open'                          => ! empty( $m['open'] ) ? 'on' : 'off',
					'title_text_color'              => $g( 'title_color' ),
					'body_text_color'               => $g( 'text_color' ),
					'icon_color'                    => $g( 'icon_color' ),
					'open_toggle_background_color'  => $g( 'background_color' ),
					'closed_toggle_background_color' => $g( 'background_color' ),
				) );
				return '[et_pb_toggle ' . self::attrs( $a ) . ']' . $m['body_html'] . '[/et_pb_toggle]';
			case 'code':
				$compact = self::compact_json( $m['jsonld'] );
				$a       = array_merge( $base, array( 'admin_label' => 'Schema (JSON-LD)' ) );
				return '[et_pb_code ' . self::attrs( $a ) . ']<script type="application/ld+json">' . $compact . '</script>[/et_pb_code]';
		}
		return '';
	}

	/** JSON with ", " and ": " separators, like Python's json.dumps(separators=(", ", ": ")). */
	public static function compact_json( $jsonld ) {
		$data = json_decode( $jsonld );
		$pretty = json_encode( $data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT );
		// Collapse the pretty print back to one line with single spaces after , and :
		$out  = '';
		$in   = false;
		$esc  = false;
		$len  = strlen( $pretty );
		for ( $i = 0; $i < $len; $i++ ) {
			$ch = $pretty[ $i ];
			if ( $in ) {
				$out .= $ch;
				if ( $esc ) {
					$esc = false;
				} elseif ( '\\' === $ch ) {
					$esc = true;
				} elseif ( '"' === $ch ) {
					$in = false;
				}
				continue;
			}
			if ( '"' === $ch ) {
				$in   = true;
				$out .= $ch;
			} elseif ( "\n" === $ch || ' ' === $ch || "\t" === $ch ) {
				continue;
			} elseif ( ',' === $ch ) {
				$out .= ', ';
			} elseif ( ':' === $ch ) {
				$out .= ': ';
			} else {
				$out .= $ch;
			}
		}
		return $out;
	}

	public static function render( array $spec ) {
		$out = array();
		foreach ( $spec['sections'] as $sec ) {
			$pad = ( isset( $sec['padding_top'] ) || isset( $sec['padding_bottom'] ) )
				? ( $sec['padding_top'] ?? 0 ) . 'px||' . ( $sec['padding_bottom'] ?? 0 ) . 'px|||' : null;
			$sa  = array(
				'fb_built'         => '1',
				'admin_label'      => $sec['admin_label'],
				'module_id'        => $sec['css_id'] ?? null,
				'_builder_version' => self::V,
				'_module_preset'   => 'default',
				'background_color' => $sec['background_color'] ?? null,
				'custom_padding'   => $pad,
			);
			if ( ! empty( $sec['glow'] ) ) {
				$sa = array_merge( $sa, WPBA_Header_Glow::glow_attrs( $sec['glow'] ) );
			}
			$out[] = '[et_pb_section ' . self::attrs( $sa ) . ']';
			foreach ( $sec['rows'] as $row ) {
				$ra = array_merge(
					array(
						'column_structure' => $row['structure'],
						'_builder_version' => self::V,
						'_module_preset'   => 'default',
						'max_width'        => self::px( $row['max_width'] ?? null ),
					),
					self::box( $row ),
					array(
						'use_custom_gutter' => ! empty( $row['gutter'] ) ? 'on' : null,
						'gutter_width'      => $row['gutter'] ?? null,
						'make_equal'        => ! empty( $row['equal_heights'] ) ? 'on' : null,
					)
				);
				$out[] = '[et_pb_row ' . self::attrs( $ra ) . ']';
				$types = explode( ',', $row['structure'] );
				foreach ( $row['columns'] as $i => $col ) {
					$ca    = array_merge( array( 'type' => $types[ $i ], '_builder_version' => self::V, '_module_preset' => 'default' ), self::box( $col ) );
					$out[] = '[et_pb_column ' . self::attrs( $ca ) . ']';
					foreach ( $col['modules'] as $m ) {
						$out[] = self::module( $m );
					}
					$out[] = '[/et_pb_column]';
				}
				$out[] = '[/et_pb_row]';
			}
			$out[] = '[/et_pb_section]';
		}
		return implode( '', $out );
	}

	/** Divi Portability import file for one post, for anyone who wants to import by hand. */
	public static function portability_json( $layout, $post_id, array $global_colors ) {
		return wp_json_encode(
			array(
				'context'       => 'et_builder',
				'data'          => array( (string) $post_id => $layout ),
				'presets'       => new stdClass(),
				'global_colors' => $global_colors,
				'images'        => new stdClass(),
				'thumbnails'    => array(),
			),
			JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES
		);
	}
}
