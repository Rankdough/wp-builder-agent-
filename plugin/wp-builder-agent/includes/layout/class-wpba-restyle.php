<?php
/**
 * Role-aware restyle of a Divi layout: change colour and radius settings by what they are used for.
 * Only the attributes of Divi shortcode tags are touched; content inside modules (text, Code module HTML/SVG)
 * is never changed. A theme is [role => [old_value => new_value]] plus optional rules:
 *   "card": settings forced onto any card-like element whose background is one of "card_backgrounds"
 *   "button": settings forced onto every custom-styled Button module.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class WPBA_Restyle {

	const TAG_RE  = '/\[(et_pb_[a-z_]+)((?:\s+[a-z0-9_]+="[^"]*")*)\s*\]/';
	const ATTR_RE = '/([a-z0-9_]+)="([^"]*)"/';
	const CARD_TAGS = array(
		'et_pb_column', 'et_pb_column_inner', 'et_pb_row', 'et_pb_row_inner', 'et_pb_text', 'et_pb_blurb',
		'et_pb_testimonial', 'et_pb_toggle', 'et_pb_accordion', 'et_pb_team_member', 'et_pb_cta',
		'et_pb_pricing_table', 'et_pb_number_counter',
	);

	// Option A (picked 2026-10-13): dashboard look (navy page, slate borders, rounded cards), red kept as brand.
	const PAGE = '#070d19';
	const CARD = '#0a2540';
	const LINE = '#1e293b';

	public static function themes() {
		$navy_red = array(
			'background'       => array( '#000000' => self::PAGE, '#000' => self::PAGE, '#0b0d10' => self::PAGE, '#0a1120' => self::PAGE, '#14171b' => self::CARD, '#0f1c2e' => self::CARD ),
			'button_bg'        => array( '#000000' => self::PAGE, '#0a1120' => self::PAGE ),
			'border'           => array( '#23272d' => self::LINE, '#26292f' => self::LINE, '#1e3350' => self::LINE, '#000000' => self::PAGE, '#0a1120' => self::PAGE ),
			'text'             => array( '#b8bec6' => '#94a3b8', '#a3b1c6' => '#94a3b8', '#9aa0a6' => '#94a3b8', '#d4d8dd' => '#cbd5e1' ),
			'icon'             => array( '#ffffff' => '#f87171', '#fff' => '#f87171' ),
			'button_radius'    => array( '3px' => '8px', '4px' => '8px', '5px' => '8px', '6px' => '8px' ),
			'shadow'           => array( '#000000' => self::PAGE, '#0a1120' => self::PAGE ),
			'card_backgrounds' => array( self::CARD ),
			'card'             => array( 'border_width_all' => '1px', 'border_color_all' => self::LINE, 'border_style_all' => 'solid', 'border_radii' => 'on|16px|16px|16px|16px' ),
			'button'           => array( 'button_border_radius' => '8px' ),
		);
		$n_page = '#070c18'; $n_alt = '#0a2542'; $n_card = '#0f1729'; $n_line = '#1d283a'; $n_blue = '#3c83f6'; $n_muted = '#94a3b8'; $n_body = '#cbd5e1';
		$navy_blue = array(
			'background' => array( '#000000' => $n_page, '#0b0d10' => $n_alt, '#14171b' => $n_card ),
			'button_bg'  => array( '#e02b20' => $n_blue ),
			'border'     => array( '#23272d' => $n_line, '#2c3036' => $n_line, '#000000' => $n_page, '#f57600' => $n_blue ),
			'text'       => array( '#b8bec6' => $n_muted, '#d4d8dd' => $n_body ),
			'shadow'     => array( '#000000' => $n_page ),
			'gradient'   => array( 'rgba(224,43,32,0.28)' => 'rgba(60,131,246,0.28)' ),
			'code_css'   => array( '#e02b20' => $n_blue, '#14171b' => $n_card, '#23272d' => $n_line, '#2c3036' => $n_line, '#0b0d10' => $n_page, '#b8bec6' => $n_muted, '#d4d8dd' => $n_body ),
		);
		$themes = array( 'navy-red' => $navy_red, 'navy-blue' => $navy_blue );
		/** Sites can register their own themes: add_filter( 'wpba_restyle_themes', fn( $t ) => $t + [ 'mine' => [...] ] ). */
		return apply_filters( 'wpba_restyle_themes', $themes );
	}

	/** Map a Divi attribute name to the role its colour plays. */
	public static function role_of( $attr ) {
		if ( in_array( $attr, array( 'icon_color', 'icon_color_hover', 'circle_color' ), true ) ) {
			return 'icon';
		}
		if ( preg_match( '/(^|_)(button_)?(text|header(_\d)?|body|title|quote_icon|link)_?(text_)?color/', $attr ) && false === strpos( $attr, 'background' ) ) {
			return 'text';
		}
		if ( 0 === strpos( $attr, 'button_bg_color' ) ) {
			return 'button_bg';
		}
		if ( false !== strpos( $attr, 'background_color' ) && false === strpos( $attr, 'gradient' ) ) {
			return 'background';
		}
		if ( 0 === strpos( $attr, 'border_color' ) || 0 === strpos( $attr, 'button_border_color' ) || substr( $attr, -13 ) === '_border_color' ) {
			return 'border';
		}
		if ( 0 === strpos( $attr, 'button_border_radius' ) ) {
			return 'button_radius';
		}
		if ( false !== strpos( $attr, 'box_shadow_color' ) ) {
			return 'shadow';
		}
		return null;
	}

	private static function set_attrs( $attrs, array $values ) {
		foreach ( $values as $k => $v ) {
			$pat = '/(\s' . preg_quote( $k, '/' ) . '=")[^"]*(")/';
			if ( preg_match( $pat, $attrs ) ) {
				$attrs = preg_replace( $pat, '${1}' . $v . '${2}', $attrs, 1 );
			} else {
				$attrs .= ' ' . $k . '="' . $v . '"';
			}
		}
		return $attrs;
	}

	/** @return array [new_raw, counts] counts maps 'role:old->new' (or 'card:tag') to how many settings changed. */
	public static function restyle_layout( $raw, array $theme ) {
		$counts = array();
		$bump   = function ( $key ) use ( &$counts ) {
			$counts[ $key ] = ( $counts[ $key ] ?? 0 ) + 1;
		};
		$new = preg_replace_callback(
			self::TAG_RE,
			function ( $m ) use ( $theme, $bump ) {
				$name  = $m[1];
				$attrs = preg_replace_callback(
					self::ATTR_RE,
					function ( $a ) use ( $theme, $bump ) {
						$role = self::role_of( $a[1] );
						$val  = $a[2];
						$new  = $role && isset( $theme[ $role ][ strtolower( $val ) ] ) ? $theme[ $role ][ strtolower( $val ) ] : null;
						if ( null === $new || $new === $val ) {
							return $a[0];
						}
						$bump( "$role:" . strtolower( $val ) . "->$new" );
						return $a[1] . '="' . $new . '"';
					},
					$m[2]
				);
				preg_match_all( self::ATTR_RE, $attrs, $vm, PREG_SET_ORDER );
				$values = array();
				foreach ( $vm as $v ) {
					$values[ $v[1] ] = $v[2];
				}
				if ( ! empty( $theme['card'] ) && in_array( $name, self::CARD_TAGS, true )
					&& in_array( strtolower( $values['background_color'] ?? '' ), (array) ( $theme['card_backgrounds'] ?? array() ), true ) ) {
					$differs = false;
					foreach ( $theme['card'] as $k => $v ) {
						if ( ( $values[ $k ] ?? null ) !== $v ) {
							$differs = true;
						}
					}
					if ( $differs ) {
						$attrs = self::set_attrs( $attrs, $theme['card'] );
						$bump( "card:$name" );
					}
				}
				if ( ! empty( $theme['button'] ) && 'et_pb_button' === $name && ( $values['custom_button'] ?? '' ) === 'on' ) {
					$differs = false;
					foreach ( $theme['button'] as $k => $v ) {
						if ( ( $values[ $k ] ?? null ) !== $v ) {
							$differs = true;
						}
					}
					if ( $differs ) {
						$attrs = self::set_attrs( $attrs, $theme['button'] );
						$bump( 'button:radius' );
					}
				}
				return "[$name$attrs]";
			},
			$raw
		);
		return array( $new, $counts );
	}

	/** Change colour values inside Code modules' <style> blocks and style="" attributes only. Text is untouched. */
	public static function swap_code_colours( $raw, array $mapping ) {
		$n   = 0;
		$css = function ( $s ) use ( $mapping, &$n ) {
			return preg_replace_callback(
				'/#[0-9a-fA-F]{6}\b/',
				function ( $m ) use ( $mapping, &$n ) {
					$new = $mapping[ strtolower( $m[0] ) ] ?? null;
					if ( $new ) {
						$n++;
						return $new;
					}
					return $m[0];
				},
				$s
			);
		};
		$new = preg_replace_callback(
			'/(\[et_pb_code[^\]]*\])(.*?)(\[\/et_pb_code\])/s',
			function ( $m ) use ( $css ) {
				$body = preg_replace_callback( '/(<style[^>]*>)(.*?)(<\/style>)/s', function ( $s ) use ( $css ) { return $s[1] . $css( $s[2] ) . $s[3]; }, $m[2] );
				$body = preg_replace_callback( '/(style=")([^"]*)(")/', function ( $s ) use ( $css ) { return $s[1] . $css( $s[2] ) . $s[3]; }, $body );
				return $m[1] . $body . $m[3];
			},
			$raw
		);
		return array( $new, $n );
	}

	public static function swap_gradients( $raw, array $mapping ) {
		$n = 0;
		foreach ( $mapping as $old => $new ) {
			$n  += substr_count( $raw, $old );
			$raw = str_replace( $old, $new, $raw );
		}
		return array( $raw, $n );
	}

	/** Words a visitor reads: shortcode tags, <style> blocks and HTML tags removed. */
	public static function visible_text( $raw ) {
		$t = preg_replace( '/<style.*?<\/style>/s', ' ', $raw );
		$t = preg_replace( '/\[\/?et_pb_[^\]]*\]/', ' ', $t );
		$t = preg_replace( '/<[^>]+>/', ' ', $t );
		return trim( preg_replace( '/\s+/u', ' ', $t ) );
	}

	/** Apply a whole theme to a layout: attributes, then gradients and Code-module CSS if the theme has them. */
	public static function apply_theme( $raw, array $theme ) {
		list( $new, $counts ) = self::restyle_layout( $raw, $theme );
		if ( ! empty( $theme['gradient'] ) ) {
			list( $new, $n ) = self::swap_gradients( $new, $theme['gradient'] );
			if ( $n ) {
				$counts['gradient'] = $n;
			}
		}
		if ( ! empty( $theme['code_css'] ) ) {
			list( $new, $n ) = self::swap_code_colours( $new, $theme['code_css'] );
			if ( $n ) {
				$counts['code_css'] = $n;
			}
		}
		return array( $new, $counts );
	}
}
