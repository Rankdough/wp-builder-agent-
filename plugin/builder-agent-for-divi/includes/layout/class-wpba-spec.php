<?php
/**
 * Layout spec: native Divi sections, rows, columns and modules with design values only.
 * Claude fills this in; code validates it; WPBA_Render turns it into Divi's own layout format.
 * This is the PHP twin of wpagent/layout/spec.py: the JSON schema is handed to Claude, and validate()
 * enforces the same rules the Pydantic models and validate_spec() did.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class WPBA_Spec {

	const HEX_RE            = '/^#[0-9a-fA-F]{6}$/';
	const COLUMN_STRUCTURES = array( '4_4', '1_2,1_2', '1_3,1_3,1_3', '1_4,1_4,1_4,1_4', '2_3,1_3', '1_3,2_3', '3_5,2_5', '2_5,3_5' );
	const GLOW_POSITIONS    = array( 'center', 'top left', 'top', 'top right', 'right', 'bottom right', 'bottom', 'bottom left', 'left' );
	const ALLOWED_TAGS      = array( 'p', 'h1', 'h2', 'h3', 'h4', 'strong', 'em', 'a', 'ul', 'ol', 'li', 'br', 'span' );
	const SPAN_COLOUR_RE    = '/^color:\s*#[0-9a-fA-F]{6};?$/';
	const CURLY             = array( '‘' => "'", '’' => "'", '“' => '"', '”' => '"' );

	// --- JSON schema (what Claude is shown) -----------------------------------------------------------

	private static function hex( $desc = null ) {
		$a = array( 'type' => array( 'string', 'null' ), 'pattern' => '^#[0-9a-fA-F]{6}$' );
		if ( $desc ) {
			$a['description'] = $desc;
		}
		return $a;
	}

	private static function px( $desc = null, $min = 0, $max = 400 ) {
		$a = array( 'type' => array( 'integer', 'null' ), 'minimum' => $min, 'maximum' => $max );
		if ( $desc ) {
			$a['description'] = $desc;
		}
		return $a;
	}

	private static function box_props() {
		return array(
			'background_color' => self::hex(),
			'padding'          => array( 'type' => array( 'array', 'null' ), 'items' => self::px(), 'minItems' => 4, 'maxItems' => 4, 'description' => '[top, right, bottom, left] in px' ),
			'margin_bottom'    => self::px(),
			'border_width'     => self::px(),
			'border_color'     => self::hex(),
			'border_style'     => array( 'type' => array( 'string', 'null' ), 'enum' => array( 'solid', 'dashed', 'dotted', null ) ),
			'border_radius'    => self::px(),
		);
	}

	public static function json_schema() {
		$str      = array( 'type' => 'string' );
		$nstr     = array( 'type' => array( 'string', 'null' ) );
		$align    = array( 'type' => array( 'string', 'null' ), 'enum' => array( 'left', 'center', 'right', null ) );
		$html_doc = 'Only p, h1-h4, strong, em, a[href], ul, ol, li, br. No attributes except href. No square brackets.';
		$modules  = array(
			array(
				'type'       => 'object',
				'properties' => array_merge( self::box_props(), array(
					'type'           => array( 'const' => 'text' ),
					'css_class'      => array_merge( $nstr, array( 'description' => 'Space-separated registered component classes, e.g. rd-kpi rd-kpi--green' ) ),
					'html'           => array_merge( $str, array( 'description' => $html_doc ) ),
					'text_color'     => self::hex(),
					'font_size'      => self::px(),
					'line_height_em' => array( 'type' => array( 'number', 'null' ), 'minimum' => 1, 'maximum' => 3 ),
					'heading_color'  => self::hex(),
					'h1_size'        => self::px(),
					'h2_size'        => self::px(),
					'h3_size'        => self::px(),
					'align'          => $align,
				) ),
				'required'   => array( 'type', 'html' ),
			),
			array(
				'type'       => 'object',
				'properties' => array(
					'type'          => array( 'const' => 'button' ),
					'text'          => $str,
					'url'           => $str,
					'new_window'    => array( 'type' => 'boolean' ),
					'align'         => $align,
					'text_color'    => self::hex(),
					'bg_color'      => self::hex(),
					'border_color'  => self::hex(),
					'border_width'  => self::px(),
					'border_radius' => self::px(),
					'font_size'     => self::px(),
					'show_arrow'    => array( 'type' => 'boolean', 'description' => "Show Divi's arrow icon after the text at all times" ),
				),
				'required'   => array( 'type', 'text', 'url' ),
			),
			array(
				'type'       => 'object',
				'properties' => array_merge( self::box_props(), array(
					'type'  => array( 'const' => 'image' ),
					'src'   => $str,
					'alt'   => $str,
					'title' => $nstr,
				) ),
				'required'   => array( 'type', 'src', 'alt' ),
			),
			array(
				'type'       => 'object',
				'properties' => array_merge( self::box_props(), array(
					'type'        => array( 'const' => 'blurb' ),
					'css_class'   => $nstr,
					'title'       => $str,
					'body_html'   => array_merge( $str, array( 'description' => 'Same tag rules as text html' ) ),
					'title_color' => self::hex(),
					'title_size'  => self::px(),
					'text_color'  => self::hex(),
					'font_size'   => self::px(),
				) ),
				'required'   => array( 'type', 'title', 'body_html' ),
			),
			array(
				'type'       => 'object',
				'properties' => array_merge( self::box_props(), array(
					'type'        => array( 'const' => 'toggle' ),
					'title'       => $str,
					'body_html'   => $str,
					'open'        => array( 'type' => 'boolean' ),
					'title_color' => self::hex(),
					'text_color'  => self::hex(),
					'icon_color'  => self::hex(),
				) ),
				'required'   => array( 'type', 'title', 'body_html' ),
			),
			array(
				'type'       => 'object',
				'properties' => array(
					'type'   => array( 'const' => 'code' ),
					'jsonld' => array_merge( $str, array( 'description' => 'The JSON-LD object only, without the <script> tag' ) ),
				),
				'required'   => array( 'type', 'jsonld' ),
			),
		);
		return array(
			'type'       => 'object',
			'required'   => array( 'sections' ),
			'properties' => array(
				'sections'       => array(
					'type'  => 'array',
					'items' => array(
						'type'       => 'object',
						'required'   => array( 'admin_label', 'rows' ),
						'properties' => array(
							'admin_label'      => $str,
							'css_id'           => array( 'type' => array( 'string', 'null' ), 'pattern' => '^[a-z][a-z0-9-]{0,40}$', 'description' => 'Anchor id, e.g. setup for #setup links' ),
							'background_color' => self::hex(),
							'glow'             => array(
								'type'       => array( 'object', 'null' ),
								'description' => 'Divi native background gradient (Background > Gradient > Circular)',
								'required'   => array( 'color', 'opacity', 'position', 'fade_at_percent' ),
								'properties' => array(
									'color'           => array( 'type' => 'string', 'pattern' => '^#[0-9a-fA-F]{6}$' ),
									'opacity'         => array( 'type' => 'number', 'minimum' => 0, 'maximum' => 1 ),
									'position'        => array( 'type' => 'string', 'enum' => self::GLOW_POSITIONS ),
									'fade_at_percent' => array( 'type' => 'integer', 'minimum' => 1, 'maximum' => 100 ),
								),
							),
							'padding_top'      => self::px(),
							'padding_bottom'   => self::px(),
							'rows'             => array(
								'type'  => 'array',
								'items' => array(
									'type'       => 'object',
									'required'   => array( 'structure', 'columns' ),
									'properties' => array_merge( self::box_props(), array(
										'structure'     => array( 'type' => 'string', 'enum' => self::COLUMN_STRUCTURES ),
										'max_width'     => self::px( 'Row max width in px; null = theme default', 320, 2000 ),
										'gutter'        => array( 'type' => array( 'integer', 'null' ), 'enum' => array( 1, 2, 3, 4, null ), 'description' => 'Divi gutter width: 1=0%, 2=3%, 3=5.5%, 4=8%' ),
										'equal_heights' => array( 'type' => 'boolean', 'description' => 'Equalize column heights (cards in a grid)' ),
										'columns'       => array(
											'type'  => 'array',
											'items' => array(
												'type'       => 'object',
												'required'   => array( 'modules' ),
												'properties' => array_merge( self::box_props(), array(
													'modules' => array( 'type' => 'array', 'items' => array( 'oneOf' => $modules ) ),
												) ),
											),
										),
									) ),
								),
							),
						),
					),
				),
				'notes'          => array( 'type' => 'array', 'items' => $str, 'description' => 'Where the rebuild differs visually from the original, and why' ),
				'new_components' => array(
					'type'  => 'array',
					'items' => array(
						'type'       => 'object',
						'required'   => array( 'name', 'usage', 'css' ),
						'properties' => array(
							'name'  => array_merge( $str, array( 'description' => 'Base class, e.g. rd-score-ring. Modifiers must start with it, e.g. rd-score-ring--red' ) ),
							'usage' => array_merge( $str, array( 'description' => 'What to put in the Text module and which classes to add' ) ),
							'css'   => array_merge( $str, array( 'description' => 'CSS rules; every selector starts with .<name> (or one of its --modifiers)' ) ),
						),
					),
				),
			),
		);
	}

	// --- validation -----------------------------------------------------------------------------------

	private static function err( $msg ) {
		return new WP_Error( 'wpba_spec', $msg );
	}

	private static function check_hex( $v, $where, $field ) {
		if ( null !== $v && ! ( is_string( $v ) && preg_match( self::HEX_RE, $v ) ) ) {
			return self::err( "$where: $field must be #rrggbb" );
		}
		return true;
	}

	private static function check_px( $v, $where, $field, $min = 0, $max = 400 ) {
		if ( null !== $v && ! ( is_int( $v ) && $v >= $min && $v <= $max ) ) {
			return self::err( "$where: $field must be an integer $min-$max" );
		}
		return true;
	}

	private static function check_enum( $v, array $allowed, $where, $field ) {
		if ( null !== $v && ! in_array( $v, $allowed, true ) ) {
			return self::err( "$where: $field must be one of " . implode( ', ', array_map( 'strval', $allowed ) ) );
		}
		return true;
	}

	private static function check_box( array $b, $where ) {
		foreach ( array( 'background_color', 'border_color' ) as $f ) {
			$r = self::check_hex( $b[ $f ] ?? null, $where, $f );
			if ( is_wp_error( $r ) ) {
				return $r;
			}
		}
		foreach ( array( 'margin_bottom', 'border_width', 'border_radius' ) as $f ) {
			$r = self::check_px( $b[ $f ] ?? null, $where, $f );
			if ( is_wp_error( $r ) ) {
				return $r;
			}
		}
		if ( isset( $b['padding'] ) ) {
			if ( ! is_array( $b['padding'] ) || 4 !== count( $b['padding'] ) ) {
				return self::err( "$where: padding must be [top, right, bottom, left]" );
			}
			foreach ( $b['padding'] as $p ) {
				$r = self::check_px( $p, $where, 'padding' );
				if ( is_wp_error( $r ) ) {
					return $r;
				}
			}
		}
		return self::check_enum( $b['border_style'] ?? null, array( 'solid', 'dashed', 'dotted' ), $where, 'border_style' );
	}

	/** @return true|WP_Error */
	public static function check_html( $fragment, $where ) {
		if ( false !== strpos( $fragment, '[' ) || false !== strpos( $fragment, ']' ) ) {
			return self::err( "$where: square brackets would break Divi shortcodes" );
		}
		$errors = array();
		if ( preg_match_all( '/<\s*([a-zA-Z][a-zA-Z0-9]*)((?:\s+[^\s=>\/]+(?:\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+))?)*)\s*\/?>/', $fragment, $tags, PREG_SET_ORDER ) ) {
			foreach ( $tags as $t ) {
				$tag = strtolower( $t[1] );
				if ( ! in_array( $tag, self::ALLOWED_TAGS, true ) ) {
					$errors[] = "tag <$tag> not allowed";
				}
				if ( preg_match_all( '/([^\s=]+)(?:\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+)))?/', trim( $t[2] ), $attrs, PREG_SET_ORDER ) ) {
					foreach ( $attrs as $a ) {
						$k = strtolower( $a[1] );
						$v = isset( $a[2] ) && '' !== $a[2] ? $a[2] : ( isset( $a[3] ) && '' !== $a[3] ? $a[3] : ( $a[4] ?? '' ) );
						if ( 'span' === $tag && 'style' === $k && preg_match( self::SPAN_COLOUR_RE, trim( $v ) ) ) {
							continue;
						}
						if ( ! ( 'a' === $tag && in_array( $k, array( 'href', 'target', 'rel' ), true ) ) ) {
							$errors[] = "attribute $k= on <$tag> not allowed";
						}
						if ( 'href' === $k && 0 === strpos( strtolower( trim( $v ) ), 'javascript:' ) ) {
							$errors[] = 'javascript: link not allowed';
						}
					}
				}
			}
		}
		if ( preg_match_all( '/<\/\s*([a-zA-Z][a-zA-Z0-9]*)\s*>/', $fragment, $closes ) ) {
			foreach ( $closes[1] as $tag ) {
				if ( ! in_array( strtolower( $tag ), self::ALLOWED_TAGS, true ) ) {
					$errors[] = 'tag <' . strtolower( $tag ) . '> not allowed';
				}
			}
		}
		if ( $errors ) {
			$errors = array_unique( $errors );
			sort( $errors );
			return self::err( "$where: " . implode( '; ', $errors ) );
		}
		return true;
	}

	/**
	 * Validate a spec (structure, types, HTML, URLs, images, JSON-LD). media_base: images must start with it.
	 * @return true|WP_Error
	 */
	public static function validate( array $spec, $media_base = null ) {
		if ( ! isset( $spec['sections'] ) || ! is_array( $spec['sections'] ) ) {
			return self::err( 'spec needs a sections array' );
		}
		$codes = 0;
		foreach ( $spec['sections'] as $si => $sec ) {
			$sw = "section $si";
			if ( empty( $sec['admin_label'] ) || ! is_string( $sec['admin_label'] ) ) {
				return self::err( "$sw: admin_label required" );
			}
			if ( isset( $sec['css_id'] ) && ! preg_match( '/^[a-z][a-z0-9-]{0,40}$/', (string) $sec['css_id'] ) ) {
				return self::err( "$sw: css_id must be lowercase letters, digits and dashes" );
			}
			foreach ( array( array( 'background_color', 'hex' ), array( 'padding_top', 'px' ), array( 'padding_bottom', 'px' ) ) as $f ) {
				$r = 'hex' === $f[1] ? self::check_hex( $sec[ $f[0] ] ?? null, $sw, $f[0] ) : self::check_px( $sec[ $f[0] ] ?? null, $sw, $f[0] );
				if ( is_wp_error( $r ) ) {
					return $r;
				}
			}
			if ( isset( $sec['glow'] ) ) {
				$g = $sec['glow'];
				if ( ! is_array( $g ) || ! isset( $g['color'], $g['opacity'], $g['position'], $g['fade_at_percent'] ) ) {
					return self::err( "$sw: glow needs color, opacity, position, fade_at_percent" );
				}
				if ( ! preg_match( self::HEX_RE, (string) $g['color'] ) || ! is_numeric( $g['opacity'] ) || $g['opacity'] < 0 || $g['opacity'] > 1
					|| ! in_array( $g['position'], self::GLOW_POSITIONS, true ) || ! is_int( $g['fade_at_percent'] ) || $g['fade_at_percent'] < 1 || $g['fade_at_percent'] > 100 ) {
					return self::err( "$sw: glow values out of range" );
				}
			}
			if ( ! isset( $sec['rows'] ) || ! is_array( $sec['rows'] ) ) {
				return self::err( "$sw: rows required" );
			}
			foreach ( $sec['rows'] as $ri => $row ) {
				$rw = "$sw row $ri";
				if ( ! isset( $row['structure'] ) || ! in_array( $row['structure'], self::COLUMN_STRUCTURES, true ) ) {
					return self::err( "$rw: structure must be one of " . implode( ' ', self::COLUMN_STRUCTURES ) );
				}
				$r = self::check_box( $row, $rw );
				if ( is_wp_error( $r ) ) {
					return $r;
				}
				$r = self::check_px( $row['max_width'] ?? null, $rw, 'max_width', 320, 2000 );
				if ( is_wp_error( $r ) ) {
					return $r;
				}
				$r = self::check_enum( $row['gutter'] ?? null, array( 1, 2, 3, 4 ), $rw, 'gutter' );
				if ( is_wp_error( $r ) ) {
					return $r;
				}
				$want = count( explode( ',', $row['structure'] ) );
				$cols = isset( $row['columns'] ) && is_array( $row['columns'] ) ? $row['columns'] : array();
				if ( count( $cols ) !== $want ) {
					return self::err( "$rw: structure {$row['structure']} needs $want columns, got " . count( $cols ) );
				}
				foreach ( $cols as $ci => $col ) {
					$cw = "$rw col $ci";
					$r  = self::check_box( is_array( $col ) ? $col : array(), $cw );
					if ( is_wp_error( $r ) ) {
						return $r;
					}
					if ( ! isset( $col['modules'] ) || ! is_array( $col['modules'] ) ) {
						return self::err( "$cw: modules required" );
					}
					foreach ( $col['modules'] as $mi => $m ) {
						$type  = isset( $m['type'] ) ? $m['type'] : '?';
						$where = "$cw module $mi ($type)";
						$r     = self::validate_module( $m, $where, $media_base, $codes );
						if ( is_wp_error( $r ) ) {
							return $r;
						}
					}
				}
			}
		}
		if ( $codes > 1 ) {
			return self::err( "$codes Code modules; only one (the JSON-LD) is allowed" );
		}
		return true;
	}

	private static function validate_module( $m, $where, $media_base, &$codes ) {
		if ( ! is_array( $m ) || empty( $m['type'] ) ) {
			return self::err( "$where: module needs a type" );
		}
		$type = $m['type'];
		if ( in_array( $type, array( 'text', 'image', 'blurb', 'toggle' ), true ) ) {
			$r = self::check_box( $m, $where );
			if ( is_wp_error( $r ) ) {
				return $r;
			}
		}
		if ( in_array( $type, array( 'text', 'blurb' ), true ) && isset( $m['css_class'] ) ) {
			$r = WPBA_Components::check_classes( $m['css_class'] );
			if ( is_wp_error( $r ) ) {
				return self::err( "$where: " . $r->get_error_message() );
			}
		}
		switch ( $type ) {
			case 'text':
				if ( ! isset( $m['html'] ) || ! is_string( $m['html'] ) ) {
					return self::err( "$where: html required" );
				}
				foreach ( array( 'text_color', 'heading_color' ) as $f ) {
					$r = self::check_hex( $m[ $f ] ?? null, $where, $f );
					if ( is_wp_error( $r ) ) {
						return $r;
					}
				}
				foreach ( array( 'font_size', 'h1_size', 'h2_size', 'h3_size' ) as $f ) {
					$r = self::check_px( $m[ $f ] ?? null, $where, $f );
					if ( is_wp_error( $r ) ) {
						return $r;
					}
				}
				if ( isset( $m['line_height_em'] ) && ( ! is_numeric( $m['line_height_em'] ) || $m['line_height_em'] < 1 || $m['line_height_em'] > 3 ) ) {
					return self::err( "$where: line_height_em must be 1-3" );
				}
				$r = self::check_enum( $m['align'] ?? null, array( 'left', 'center', 'right' ), $where, 'align' );
				if ( is_wp_error( $r ) ) {
					return $r;
				}
				return self::check_html( $m['html'], $where );
			case 'button':
				if ( ! isset( $m['text'], $m['url'] ) || ! is_string( $m['text'] ) || ! is_string( $m['url'] ) ) {
					return self::err( "$where: text and url required" );
				}
				if ( preg_match( '/[<>\[\]"]/', $m['text'] ) || ! preg_match( '/^(https?:\/\/|#|\/|mailto:[^\s<>"]+$)/', $m['url'] ) ) {
					return self::err( "$where: bad button text or url" );
				}
				foreach ( array( 'text_color', 'bg_color', 'border_color' ) as $f ) {
					$r = self::check_hex( $m[ $f ] ?? null, $where, $f );
					if ( is_wp_error( $r ) ) {
						return $r;
					}
				}
				foreach ( array( 'border_width', 'border_radius', 'font_size' ) as $f ) {
					$r = self::check_px( $m[ $f ] ?? null, $where, $f );
					if ( is_wp_error( $r ) ) {
						return $r;
					}
				}
				return self::check_enum( $m['align'] ?? null, array( 'left', 'center', 'right' ), $where, 'align' );
			case 'image':
				if ( ! isset( $m['src'], $m['alt'] ) || ! is_string( $m['src'] ) ) {
					return self::err( "$where: src and alt required" );
				}
				if ( 0 !== strpos( $m['src'], $media_base ? $media_base : 'https://' ) ) {
					return self::err( "$where: image must come from the site's media library" );
				}
				return true;
			case 'blurb':
			case 'toggle':
				if ( ! isset( $m['title'], $m['body_html'] ) || ! is_string( $m['title'] ) || ! is_string( $m['body_html'] ) ) {
					return self::err( "$where: title and body_html required" );
				}
				if ( preg_match( '/[<>\[\]]/', $m['title'] ) ) {
					return self::err( "$where: title contains markup" );
				}
				foreach ( array( 'title_color', 'text_color', 'icon_color' ) as $f ) {
					$r = self::check_hex( $m[ $f ] ?? null, $where, $f );
					if ( is_wp_error( $r ) ) {
						return $r;
					}
				}
				foreach ( array( 'title_size', 'font_size' ) as $f ) {
					$r = self::check_px( $m[ $f ] ?? null, $where, $f );
					if ( is_wp_error( $r ) ) {
						return $r;
					}
				}
				return self::check_html( $m['body_html'], $where );
			case 'code':
				$codes++;
				if ( ! isset( $m['jsonld'] ) || ! is_string( $m['jsonld'] ) ) {
					return self::err( "$where: jsonld required" );
				}
				json_decode( $m['jsonld'] );
				if ( JSON_ERROR_NONE !== json_last_error() ) {
					return self::err( "$where: jsonld is not valid JSON (" . json_last_error_msg() . ')' );
				}
				if ( false !== stripos( $m['jsonld'], '</script' ) ) {
					return self::err( "$where: jsonld must not contain a script tag" );
				}
				return true;
			default:
				return self::err( "$where: unknown module type '$type'" );
		}
	}

	// --- helpers ----------------------------------------------------------------------------------------

	/** Turn curly quotes back into straight ones (when the source page used straight quotes). JSON-LD is kept. */
	public static function straighten_quotes( array $spec ) {
		$walk = function ( $v ) use ( &$walk ) {
			if ( is_string( $v ) ) {
				return strtr( $v, self::CURLY );
			}
			if ( is_array( $v ) ) {
				if ( isset( $v['type'] ) && 'code' === $v['type'] ) {
					return $v;
				}
				return array_map( $walk, $v );
			}
			return $v;
		};
		return $walk( $spec );
	}

	public static function plain( $html ) {
		$t = preg_replace( '/<[^>]+>/', ' ', (string) $html );
		$t = strtr( html_entity_decode( $t, ENT_QUOTES | ENT_HTML5, 'UTF-8' ), self::CURLY );
		return trim( preg_replace( '/\s+/u', ' ', $t ) );
	}

	/** Every module of a spec, flattened, with its location. */
	public static function modules( array $spec ) {
		$out = array();
		foreach ( $spec['sections'] ?? array() as $sec ) {
			foreach ( $sec['rows'] ?? array() as $row ) {
				foreach ( $row['columns'] ?? array() as $col ) {
					foreach ( $col['modules'] ?? array() as $m ) {
						$out[] = $m;
					}
				}
			}
		}
		return $out;
	}

	public static function count_modules( array $spec ) {
		$counts = array();
		foreach ( self::modules( $spec ) as $m ) {
			$counts[ $m['type'] ] = ( $counts[ $m['type'] ] ?? 0 ) + 1;
		}
		return $counts;
	}

	/**
	 * Source passages (own text of each element, >= min_len chars) that do not appear verbatim in the spec.
	 * Link text is excluded from source nodes, so a passage is split at links: check each piece.
	 */
	public static function missing_text( array $source_nodes, array $spec, $min_len = 20 ) {
		$parts = array();
		foreach ( self::modules( $spec ) as $m ) {
			foreach ( array( 'html', 'body_html', 'title', 'text' ) as $f ) {
				if ( ! empty( $m[ $f ] ) ) {
					$parts[] = self::plain( $m[ $f ] );
				}
			}
		}
		$blob    = implode( ' ', $parts );
		$missing = array();
		foreach ( $source_nodes as $n ) {
			$text = self::plain( $n['text'] ?? '' );
			if ( mb_strlen( $text ) < $min_len ) {
				continue;
			}
			$pieces = array();
			foreach ( preg_split( '/\s{2,}| \. |(?<=from) \./', $text ) as $p ) {
				$p = trim( $p, ' .' );
				if ( mb_strlen( $p ) >= 8 ) {
					$pieces[] = $p;
				}
			}
			foreach ( $pieces as $p ) {
				if ( false === strpos( $blob, $p ) ) {
					$missing[] = $text;
					break;
				}
			}
		}
		return $missing;
	}
}
