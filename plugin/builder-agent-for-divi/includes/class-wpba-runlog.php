<?php
/**
 * Run records. Every command run creates one private wpba_run post holding:
 *   events  (JSON lines of what was read, decided and written)
 *   files   (named JSON documents: plan, context, spec, verify results)
 *   backups (named snapshots taken before any write: option values, page content)
 * This replaces the `runs/<site>/<time>-<command>/` folders of the CLI agent.
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class WPBA_RunLog {

	/** @var int */
	public $id;
	/** @var string */
	public $command;
	/** @var array */
	private $events = array();

	private function __construct( $id, $command ) {
		$this->id      = (int) $id;
		$this->command = $command;
	}

	public static function start( $command, array $meta = array() ) {
		$id = wp_insert_post(
			array(
				'post_type'   => WPBA_Plugin::RUN_POST_TYPE,
				'post_status' => 'private',
				'post_title'  => gmdate( 'Y-m-d H:i:s' ) . ' ' . $command,
			),
			true
		);
		if ( is_wp_error( $id ) ) {
			wp_die( esc_html( $id->get_error_message() ) );
		}
		update_post_meta( $id, '_wpba_command', $command );
		update_post_meta( $id, '_wpba_status', 'running' );
		update_post_meta( $id, '_wpba_site', WPBA_Guard::site_name() );
		$log = new self( $id, $command );
		$log->event( 'start', array_merge( array( 'command' => $command, 'site' => WPBA_Guard::site_name(), 'user' => get_current_user_id() ), $meta ) );
		return $log;
	}

	public static function open( $id ) {
		$post = get_post( (int) $id );
		if ( ! $post || WPBA_Plugin::RUN_POST_TYPE !== $post->post_type ) {
			return new WP_Error( 'wpba_no_run', "Run $id not found." );
		}
		$log         = new self( $post->ID, (string) get_post_meta( $post->ID, '_wpba_command', true ) );
		$log->events = (array) get_post_meta( $post->ID, '_wpba_events', true );
		return $log;
	}

	public function event( $type, array $data = array() ) {
		$entry          = array_merge( array( 't' => gmdate( 'c' ), 'type' => $type ), $data );
		$this->events[] = $entry;
		update_post_meta( $this->id, '_wpba_events', wp_slash( $this->events ) );
		return $entry;
	}

	/** Store a named JSON document (plan.json, context.json, spec.json ...). */
	public function write_json( $name, $data ) {
		update_post_meta( $this->id, '_wpba_file_' . sanitize_key( $name ), wp_slash( wp_json_encode( $data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) ) );
		$files = (array) get_post_meta( $this->id, '_wpba_files', true );
		if ( ! in_array( $name, $files, true ) ) {
			$files[] = $name;
			update_post_meta( $this->id, '_wpba_files', $files );
		}
	}

	public function read_json( $name ) {
		$raw = get_post_meta( $this->id, '_wpba_file_' . sanitize_key( $name ), true );
		return $raw ? json_decode( $raw, true ) : null;
	}

	/** Store a backup taken before a write. Backups are kept raw so they can be restored byte for byte. */
	public function backup( $name, $data ) {
		update_post_meta( $this->id, '_wpba_backup_' . sanitize_key( $name ), wp_slash( is_string( $data ) ? $data : wp_json_encode( $data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) ) );
		$list = (array) get_post_meta( $this->id, '_wpba_backups', true );
		if ( ! in_array( $name, $list, true ) ) {
			$list[] = $name;
			update_post_meta( $this->id, '_wpba_backups', $list );
		}
		$this->event( 'backup_saved', array( 'name' => $name, 'bytes' => strlen( is_string( $data ) ? $data : wp_json_encode( $data ) ) ) );
	}

	public function read_backup( $name, $decode = true ) {
		$raw = get_post_meta( $this->id, '_wpba_backup_' . sanitize_key( $name ), true );
		if ( '' === $raw || null === $raw ) {
			return null;
		}
		if ( ! $decode ) {
			return $raw;
		}
		$d = json_decode( $raw, true );
		return null === $d ? $raw : $d;
	}

	public function close( $status = 'done', array $data = array() ) {
		update_post_meta( $this->id, '_wpba_status', $status );
		$this->event( 'done', array_merge( array( 'status' => $status ), $data ) );
	}

	public function fail( $message ) {
		$this->close( 'failed', array( 'error' => (string) $message ) );
	}

	/** Summary for lists and the REST API. */
	public static function summary( $post ) {
		$post = get_post( $post );
		return array(
			'id'      => $post->ID,
			'title'   => $post->post_title,
			'command' => get_post_meta( $post->ID, '_wpba_command', true ),
			'status'  => get_post_meta( $post->ID, '_wpba_status', true ),
			'date'    => $post->post_date_gmt,
		);
	}

	public static function detail( $id ) {
		$post = get_post( (int) $id );
		if ( ! $post || WPBA_Plugin::RUN_POST_TYPE !== $post->post_type ) {
			return new WP_Error( 'wpba_no_run', "Run $id not found." );
		}
		$out            = self::summary( $post );
		$out['events']  = (array) get_post_meta( $post->ID, '_wpba_events', true );
		$out['files']   = array();
		$out['backups'] = (array) get_post_meta( $post->ID, '_wpba_backups', true );
		foreach ( (array) get_post_meta( $post->ID, '_wpba_files', true ) as $name ) {
			$out['files'][ $name ] = json_decode( (string) get_post_meta( $post->ID, '_wpba_file_' . sanitize_key( $name ), true ), true );
		}
		return $out;
	}

	public static function list_runs( $limit = 50 ) {
		$posts = get_posts(
			array(
				'post_type'   => WPBA_Plugin::RUN_POST_TYPE,
				'post_status' => 'private',
				'numberposts' => (int) $limit,
				'orderby'     => 'date',
				'order'       => 'DESC',
			)
		);
		return array_map( array( __CLASS__, 'summary' ), $posts );
	}
}
