<?php
/**
 * Divi 4 adapter. Inside WordPress the agent does not need a browser: Theme Options and Customizer values
 * live in the `et_divi` option, pages are posts whose content is Divi's shortcode layout, and the Library is
 * the `et_pb_layout` post type. Every write here takes a backup into the run log first.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class WPBA_Divi {

	const OPTION            = 'et_divi';
	const CUSTOM_CSS_KEY    = 'divi_custom_css';
	const GLOBAL_COLORS_OPT = 'et_global_colors';
	const LIBRARY_POST_TYPE = 'et_pb_layout';

	// --- detect -------------------------------------------------------------------------------------

	public static function detect() {
		$theme  = wp_get_theme();
		$parent = $theme->parent();
		return array(
			'wordpress'    => get_bloginfo( 'version' ),
			'theme'        => $theme->get( 'Name' ),
			'version'      => $theme->get( 'Version' ),
			'parent'       => $parent ? $parent->get( 'Name' ) : null,
			'divi_builder' => defined( 'ET_BUILDER_VERSION' ) ? ET_BUILDER_VERSION : ( defined( 'ET_CORE_VERSION' ) ? ET_CORE_VERSION : null ),
			'divi_present' => WPBA_Plugin::divi_present(),
			'divi5'        => defined( 'ET_BUILDER_5_VERSION' ) || function_exists( 'et_builder_d5_enabled' ),
			'site'         => home_url(),
			'php'          => PHP_VERSION,
		);
	}

	// --- Theme Options / Customizer (one option array) --------------------------------------------

	/** All scalar settings as `et_divi[key]` => value, the ids the Customizer uses. */
	public static function customizer_settings() {
		$opt = get_option( self::OPTION, array() );
		$out = array();
		foreach ( (array) $opt as $k => $v ) {
			if ( is_scalar( $v ) || null === $v ) {
				$out[ 'et_divi[' . $k . ']' ] = $v;
			}
		}
		ksort( $out );
		return $out;
	}

	public static function button_globals( array $settings ) {
		$out = array();
		foreach ( $settings as $k => $v ) {
			if ( 0 === strpos( $k, 'et_divi[all_buttons_' ) ) {
				$out[ $k ] = $v;
			}
		}
		return $out;
	}

	/** Current value as the planner sees it: '' for unset/false, else the string. */
	public static function current_value( array $settings, $id ) {
		if ( ! array_key_exists( $id, $settings ) ) {
			return null;
		}
		$v = $settings[ $id ];
		return ( null === $v || false === $v ) ? '' : (string) $v;
	}

	/**
	 * Apply customizer_set changes: [ 'et_divi[key]' => 'value', ... ]. Backs up the whole option first.
	 * @return array|WP_Error the option keys written
	 */
	public static function customizer_set( array $changes, WPBA_RunLog $log ) {
		$ok = WPBA_Guard::check_option( self::OPTION );
		if ( is_wp_error( $ok ) ) {
			return $ok;
		}
		$opt = get_option( self::OPTION, array() );
		$opt = is_array( $opt ) ? $opt : array();
		$log->backup( 'et_divi-option', $opt );
		$written = array();
		foreach ( $changes as $id => $value ) {
			if ( ! preg_match( '/^et_divi\[([a-z0-9_]+)\]$/', $id, $m ) ) {
				return new WP_Error( 'wpba_bad_setting', "Not a Divi Customizer setting id: $id" );
			}
			$opt[ $m[1] ] = $value;
			$written[]    = $m[1];
			$log->event( 'customizer_set', array( 'setting' => $id, 'value' => $value ) );
		}
		update_option( self::OPTION, $opt );
		return $written;
	}

	/** Restore the whole option from a backup (rollback of a Customizer run). */
	public static function restore_option_backup( array $backup, WPBA_RunLog $log ) {
		$log->backup( 'et_divi-option-before-rollback', get_option( self::OPTION, array() ) );
		update_option( self::OPTION, $backup );
		$log->event( 'option_restored', array( 'option' => self::OPTION, 'keys' => count( $backup ) ) );
		return true;
	}

	public static function custom_css_get() {
		$opt = get_option( self::OPTION, array() );
		return isset( $opt[ self::CUSTOM_CSS_KEY ] ) ? (string) $opt[ self::CUSTOM_CSS_KEY ] : '';
	}

	public static function custom_css_set( $css, WPBA_RunLog $log ) {
		$opt = get_option( self::OPTION, array() );
		$opt = is_array( $opt ) ? $opt : array();
		$log->backup( 'custom-css-before', isset( $opt[ self::CUSTOM_CSS_KEY ] ) ? (string) $opt[ self::CUSTOM_CSS_KEY ] : '' );
		$opt[ self::CUSTOM_CSS_KEY ] = (string) $css;
		update_option( self::OPTION, $opt );
		$log->event( 'custom_css_saved', array( 'bytes' => strlen( $css ) ) );
		return true;
	}

	public static function global_colors() {
		$gc = get_option( self::GLOBAL_COLORS_OPT, array() );
		return is_array( $gc ) ? $gc : array();
	}

	public static function media_base() {
		$u = wp_upload_dir();
		return trailingslashit( $u['baseurl'] );
	}

	// --- Pages ----------------------------------------------------------------------------------------

	public static function list_pages( array $only = array(), $status = 'publish' ) {
		$args = array(
			'post_type'   => 'page',
			'post_status' => $status,
			'numberposts' => -1,
			'orderby'     => 'ID',
			'order'       => 'ASC',
		);
		if ( $only ) {
			$args['post__in'] = array_map( 'intval', $only );
		}
		$out = array();
		foreach ( get_posts( $args ) as $p ) {
			$out[] = array(
				'id'      => $p->ID,
				'title'   => $p->post_title,
				'status'  => $p->post_status,
				'url'     => get_permalink( $p ),
				'path'    => wp_parse_url( get_permalink( $p ), PHP_URL_PATH ),
				'builder' => 'on' === get_post_meta( $p->ID, '_et_pb_use_builder', true ),
			);
		}
		return $out;
	}

	public static function page_content( $post_id ) {
		$post = WPBA_Guard::check_post( $post_id );
		return is_wp_error( $post ) ? $post : (string) $post->post_content;
	}

	/** Replace a page's layout. Backs the old content up as <id>-before. Keeps status unless given. */
	public static function page_update_content( $post_id, $content, WPBA_RunLog $log, $status = null ) {
		$post = WPBA_Guard::check_post( $post_id );
		if ( is_wp_error( $post ) ) {
			return $post;
		}
		$log->backup( $post->ID . '-before', (string) $post->post_content );
		$args = array( 'ID' => $post->ID, 'post_content' => $content );
		if ( $status ) {
			$args['post_status'] = $status;
		}
		$r = wp_update_post( wp_slash( $args ), true );
		if ( is_wp_error( $r ) ) {
			return $r;
		}
		self::ensure_builder_meta( $post->ID );
		$log->event( 'page_saved', array( 'post_id' => $post->ID, 'status' => $status ?: $post->post_status, 'bytes' => strlen( $content ) ) );
		return $post->ID;
	}

	public static function ensure_builder_meta( $post_id ) {
		update_post_meta( $post_id, '_et_pb_use_builder', 'on' );
		if ( ! get_post_meta( $post_id, '_et_pb_built_for_post_type', true ) ) {
			update_post_meta( $post_id, '_et_pb_built_for_post_type', 'page' );
		}
	}

	/** Duplicate a page into a new draft (what Duplicate Post's "New Draft" does), copying its meta. */
	public static function clone_as_draft( $post_id, WPBA_RunLog $log ) {
		$post = WPBA_Guard::check_post( $post_id );
		if ( is_wp_error( $post ) ) {
			return $post;
		}
		$new_id = wp_insert_post(
			wp_slash(
				array(
					'post_type'    => $post->post_type,
					'post_status'  => 'draft',
					'post_title'   => $post->post_title . ' (copy)',
					'post_content' => $post->post_content,
					'post_excerpt' => $post->post_excerpt,
					'post_parent'  => $post->post_parent,
					'menu_order'   => $post->menu_order,
					'post_author'  => get_current_user_id() ?: $post->post_author,
				)
			),
			true
		);
		if ( is_wp_error( $new_id ) ) {
			return $new_id;
		}
		$skip = array( '_edit_lock', '_edit_last', '_wp_old_slug', '_wp_old_date' );
		foreach ( (array) get_post_meta( $post->ID ) as $key => $values ) {
			if ( in_array( $key, $skip, true ) ) {
				continue;
			}
			foreach ( $values as $v ) {
				add_post_meta( $new_id, $key, maybe_unserialize( $v ) );
			}
		}
		$log->event( 'cloned', array( 'source' => $post->ID, 'draft' => $new_id ) );
		return $new_id;
	}

	public static function create_draft_page( $title, $content, WPBA_RunLog $log ) {
		$id = wp_insert_post(
			wp_slash(
				array(
					'post_type'    => 'page',
					'post_status'  => 'draft',
					'post_title'   => $title,
					'post_content' => $content,
				)
			),
			true
		);
		if ( is_wp_error( $id ) ) {
			return $id;
		}
		self::ensure_builder_meta( $id );
		$log->event( 'draft_created', array( 'post_id' => $id ) );
		return $id;
	}

	/** Move a draft to Trash. Refuses anything that is not a draft; never deletes permanently. */
	public static function trash_draft( $post_id, WPBA_RunLog $log ) {
		$post = WPBA_Guard::check_post( $post_id, 'draft' );
		if ( is_wp_error( $post ) ) {
			return $post;
		}
		$log->backup( $post->ID . '-trashed-content', (string) $post->post_content );
		if ( ! wp_trash_post( $post->ID ) ) {
			return new WP_Error( 'wpba_trash', "Could not trash draft $post_id." );
		}
		$log->event( 'trashed', array( 'post_id' => $post->ID ) );
		return true;
	}

	/** Copy a verified draft's layout onto the live page, then trash the draft. */
	public static function golive( $live_id, $draft_id, WPBA_RunLog $log ) {
		$live  = WPBA_Guard::check_post( $live_id, 'publish' );
		$draft = WPBA_Guard::check_post( $draft_id, 'draft' );
		if ( is_wp_error( $live ) ) {
			return $live;
		}
		if ( is_wp_error( $draft ) ) {
			return $draft;
		}
		$r = self::page_update_content( $live->ID, $draft->post_content, $log );
		if ( is_wp_error( $r ) ) {
			return $r;
		}
		return self::trash_draft( $draft->ID, $log );
	}

	// --- Divi Library ---------------------------------------------------------------------------------

	/** Save a layout, section, row or module to the Divi Library. */
	public static function save_to_library( $name, $layout, $type, WPBA_RunLog $log, $global = false ) {
		if ( ! in_array( $type, array( 'layout', 'section', 'row', 'module' ), true ) ) {
			return new WP_Error( 'wpba_bad_type', "Library type must be layout, section, row or module; got $type" );
		}
		$id = wp_insert_post(
			wp_slash(
				array(
					'post_type'    => self::LIBRARY_POST_TYPE,
					'post_status'  => 'publish',
					'post_title'   => $name,
					'post_content' => $layout,
				)
			),
			true
		);
		if ( is_wp_error( $id ) ) {
			return $id;
		}
		wp_set_object_terms( $id, $type, 'layout_type' );
		wp_set_object_terms( $id, $global ? 'global' : 'not_global', 'scope' );
		wp_set_object_terms( $id, 'regular', 'module_width' );
		update_post_meta( $id, '_et_pb_built_for_post_type', 'page' );
		$log->event( 'library_saved', array( 'post_id' => $id, 'type' => $type, 'name' => $name ) );
		return $id;
	}

	// --- Page dump: content tree of a page hand-coded inside one Code module ----------------------------

	/**
	 * Mirror of scripts/dump_code_module.py, read from the stored layout instead of the rendered DOM:
	 * nodes (tag, class, own text, href/src/alt, depth), the <style> and <script> contents.
	 */
	public static function page_dump( $post_id ) {
		$raw = self::page_content( $post_id );
		if ( is_wp_error( $raw ) ) {
			return $raw;
		}
		if ( ! preg_match_all( '/\[et_pb_code[^\]]*\](.*?)\[\/et_pb_code\]/s', $raw, $m ) ) {
			return new WP_Error( 'wpba_no_code', "Page $post_id has no Code module to rebuild from." );
		}
		$html  = implode( "\n", $m[1] );
		$style = $script = '';
		if ( preg_match_all( '/<style[^>]*>(.*?)<\/style>/is', $html, $s ) ) {
			$style = implode( "\n", $s[1] );
		}
		if ( preg_match_all( '/<script[^>]*>(.*?)<\/script>/is', $html, $s ) ) {
			$script = implode( "\n", $s[1] );
		}
		$nodes = array();
		if ( class_exists( 'DOMDocument' ) ) {
			$doc = new DOMDocument();
			libxml_use_internal_errors( true );
			$doc->loadHTML( '<?xml encoding="utf-8" ?><div id="wpba-root">' . $html . '</div>' );
			libxml_clear_errors();
			$root = $doc->getElementById( 'wpba-root' );
			if ( $root ) {
				self::walk_dom( $root, 0, $nodes );
			}
		}
		return array(
			'post_id'          => (int) $post_id,
			'title'            => get_the_title( $post_id ),
			'meta_description' => get_post_meta( $post_id, '_yoast_wpseo_metadesc', true ) ?: null,
			'nodes'            => $nodes,
			'style'            => $style,
			'script'           => $script,
		);
	}

	private static function walk_dom( DOMNode $parent, $depth, array &$nodes ) {
		foreach ( $parent->childNodes as $c ) {
			if ( XML_ELEMENT_NODE !== $c->nodeType ) {
				continue;
			}
			$tag = strtolower( $c->nodeName );
			if ( in_array( $tag, array( 'style', 'script' ), true ) ) {
				continue;
			}
			$own = array();
			foreach ( $c->childNodes as $x ) {
				if ( XML_TEXT_NODE === $x->nodeType ) {
					$t = trim( $x->textContent );
					if ( '' !== $t ) {
						$own[] = $t;
					}
				}
			}
			$node = array(
				'depth' => $depth,
				'tag'   => $tag,
				'cls'   => $c->getAttribute( 'class' ),
				'text'  => mb_substr( implode( ' ', $own ), 0, 300 ),
			);
			foreach ( array( 'href', 'src', 'alt' ) as $a ) {
				if ( $c->hasAttribute( $a ) ) {
					$node[ $a ] = $c->getAttribute( $a );
				}
			}
			$nodes[] = $node;
			self::walk_dom( $c, $depth + 1, $nodes );
		}
	}

	/** Public attachment URLs under the uploads folder, for the designer's image list. */
	public static function media_urls( $limit = 300 ) {
		$ids = get_posts(
			array(
				'post_type'      => 'attachment',
				'post_mime_type' => 'image',
				'post_status'    => 'inherit',
				'numberposts'    => (int) $limit,
				'fields'         => 'ids',
			)
		);
		$out = array();
		foreach ( $ids as $id ) {
			$url = wp_get_attachment_url( $id );
			if ( $url ) {
				$out[] = array( 'id' => $id, 'url' => $url, 'alt' => (string) get_post_meta( $id, '_wp_attachment_image_alt', true ) );
			}
		}
		return $out;
	}
}
