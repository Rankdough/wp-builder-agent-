<?php
require __DIR__ . '/bootstrap.php';
@mkdir( WPBA_Components::site_folder(), 0777, true );
array_map( 'unlink', glob( WPBA_Components::site_folder() . '*.css' ) ?: array() );

function spec( array $modules, $structure = '4_4', $ncols = 1 ) {
	$cols = array( array( 'modules' => $modules ) );
	for ( $i = 1; $i < $ncols; $i++ ) { $cols[] = array( 'modules' => array() ); }
	return array( 'sections' => array( array( 'admin_label' => 'Hero', 'background_color' => '#14171b', 'padding_top' => 80, 'rows' => array( array( 'structure' => $structure, 'columns' => $cols ) ) ) ) );
}
$TEXT   = array( 'type' => 'text', 'html' => '<h1>GSC Connector</h1><p>Ask <a href="https://x.com">Claude</a>.</p>', 'text_color' => '#ffffff', 'h1_size' => 56 );
$BUTTON = array( 'type' => 'button', 'text' => 'Download free on GitHub', 'url' => 'https://github.com/Rankdough/gsc-for-claude', 'bg_color' => '#e02b20', 'text_color' => '#ffffff', 'border_radius' => 6 );
$CODE   = array( 'type' => 'code', 'jsonld' => json_encode( array( '@context' => 'https://schema.org', '@graph' => array( array( '@type' => 'FAQPage' ) ) ) ) );
$MEDIA  = 'https://www.example.com/wp-content/uploads/';

echo "== layout spec + render ==\n";
test( 'valid spec renders native modules', function () use ( $TEXT, $BUTTON, $CODE ) {
	$s = spec( array( $TEXT, $BUTTON, $CODE ) );
	no_err( WPBA_Spec::validate( $s ) );
	$out = WPBA_Render::render( $s );
	ok( 0 === strpos( $out, '[et_pb_section ' ) && substr( $out, -16 ) === '[/et_pb_section]' );
	contains( $out, 'column_structure="4_4"' ); contains( $out, 'type="4_4"' );
	contains( $out, 'header_font_size="56px"' ); contains( $out, 'text_text_color="#ffffff"' );
	contains( $out, 'button_bg_color="#e02b20"' ); contains( $out, 'custom_button="on"' );
	contains( $out, '<script type="application/ld+json">{"@context": "https://schema.org", "@graph": [{"@type": "FAQPage"}]}</script>' );
	not_contains( $out, 'style=' ); not_contains( $out, 'class=' );
} );
$bad = array(
	array( array( 'type' => 'text', 'html' => "<div class='x'>hi</div>" ), 'not allowed' ),
	array( array( 'type' => 'text', 'html' => "<p style='color:red'>hi</p>" ), 'not allowed' ),
	array( array( 'type' => 'text', 'html' => '<p>see [et_pb_code]</p>' ), 'brackets' ),
	array( array( 'type' => 'text', 'html' => '<style>p{}</style>' ), 'not allowed' ),
	array( array( 'type' => 'text', 'html' => "<a href='javascript:alert(1)'>x</a>" ), 'javascript' ),
	array( array( 'type' => 'button', 'text' => 'Go', 'url' => 'javascript:x' ), 'url' ),
	array( array( 'type' => 'image', 'src' => 'https://evil.example/x.png', 'alt' => 'x' ), 'media library' ),
	array( array( 'type' => 'code', 'jsonld' => '{not json' ), 'valid JSON' ),
	array( array( 'type' => 'code', 'jsonld' => '{"a": "</script><script>alert(1)"}' ), 'script' ),
	array( array( 'type' => 'text', 'html' => '<p>x</p>', 'text_color' => 'red' ), '#rrggbb' ),
	array( array( 'type' => 'text', 'html' => '<p>x</p>', 'font_size' => 999 ), '0-400' ),
	array( array( 'type' => 'text', 'html' => '<p>x</p>', 'css_class' => 'my-random-class' ), 'unknown component' ),
	array( array( 'type' => 'blurb', 'title' => 'a <b>', 'body_html' => '<p>x</p>' ), 'markup' ),
);
foreach ( $bad as $i => $case ) {
	test( "bad module rejected #$i ({$case[1]})", function () use ( $case, $MEDIA ) { is_err( WPBA_Spec::validate( spec( array( $case[0] ) ), $MEDIA ), $case[1] ); } );
}
test( 'only one code module', function () use ( $CODE ) { is_err( WPBA_Spec::validate( spec( array( $CODE, $CODE ) ) ), 'only one' ); } );
test( 'column count must match structure', function () use ( $TEXT ) { is_err( WPBA_Spec::validate( spec( array( $TEXT ), '1_2,1_2', 1 ) ), 'needs 2 columns' ); } );
test( 'attribute values are encoded', function () use ( $MEDIA ) {
	is_err( WPBA_Spec::validate( spec( array( array( 'type' => 'button', 'text' => 'Say "hi"', 'url' => 'https://x.com/?a=1' ) ) ) ) );
	$out = WPBA_Render::render( spec( array( array( 'type' => 'image', 'src' => $MEDIA . 'a.png', 'alt' => 'a "b" [c]' ) ) ) );
	contains( $out, 'alt="a %22b%22 %91c%93"' );
} );
test( 'portability json shape', function () {
	$d = json_decode( WPBA_Render::portability_json( '[et_pb_section][/et_pb_section]', 3798, array() ), true );
	eq( $d['context'], 'et_builder' ); eq( $d['data'], array( '3798' => '[et_pb_section][/et_pb_section]' ) );
	$k = array_keys( $d ); sort( $k ); eq( $k, array( 'context', 'data', 'global_colors', 'images', 'presets', 'thumbnails' ) );
	eq( $d['presets'], array() );
} );
test( 'new fields render', function () {
	$s = array( 'sections' => array( array( 'admin_label' => 'Setup', 'css_id' => 'setup', 'rows' => array( array( 'structure' => '4_4', 'max_width' => 1120, 'columns' => array( array( 'modules' => array(
		array( 'type' => 'button', 'text' => 'Download', 'url' => 'https://x.com', 'bg_color' => '#e02b20', 'show_arrow' => true ),
		array( 'type' => 'toggle', 'title' => 'Is it free?', 'body_html' => '<p>Yes.</p>' ) ) ) ) ) ) ) ) );
	no_err( WPBA_Spec::validate( $s ) );
	$out = WPBA_Render::render( $s );
	contains( $out, 'module_id="setup"' ); contains( $out, 'max_width="1120px"' );
	contains( $out, 'button_use_icon="on"' ); contains( $out, 'button_on_hover="off"' ); contains( $out, 'title_level="h3"' );
} );
test( 'straighten quotes keeps jsonld', function () {
	$s = spec( array( array( 'type' => 'text', 'html' => '<p>Claude’s “app”</p>' ), array( 'type' => 'code', 'jsonld' => json_encode( array( 'name' => 'It’s' ), JSON_UNESCAPED_UNICODE ) ) ) );
	$o = WPBA_Spec::straighten_quotes( $s );
	$mods = $o['sections'][0]['rows'][0]['columns'][0]['modules'];
	eq( $mods[0]['html'], '<p>Claude\'s "app"</p>' ); contains( $mods[1]['jsonld'], '’' );
} );
test( 'glow renders native gradient', function () {
	$s = array( 'sections' => array( array( 'admin_label' => 'Hero', 'background_color' => '#000000', 'glow' => array( 'color' => '#e02b20', 'opacity' => 0.28, 'position' => 'top right', 'fade_at_percent' => 55 ),
		'rows' => array( array( 'structure' => '4_4', 'columns' => array( array( 'modules' => array( array( 'type' => 'text', 'html' => '<p>x</p>' ) ) ) ) ) ) ) ) );
	no_err( WPBA_Spec::validate( $s ) );
	$out = WPBA_Render::render( $s );
	contains( $out, 'use_background_color_gradient="on"' ); contains( $out, 'background_color_gradient_type="circular"' );
	contains( $out, 'background_color_gradient_stops="rgba(224,43,32,0.28) 0%|rgba(0,0,0,0) 55%"' ); contains( $out, 'background_color="#000000"' );
} );
test( 'row gutter and equal heights', function () {
	$col = array( 'modules' => array( array( 'type' => 'text', 'html' => '<p>a</p>' ) ) );
	$s = array( 'sections' => array( array( 'admin_label' => 'Cards', 'rows' => array( array( 'structure' => '1_3,1_3,1_3', 'gutter' => 2, 'equal_heights' => true, 'padding' => array( 11, 0, 11, 0 ), 'columns' => array( $col, $col, $col ) ) ) ) ) );
	no_err( WPBA_Spec::validate( $s ) );
	$out = WPBA_Render::render( $s );
	contains( $out, 'use_custom_gutter="on"' ); contains( $out, 'gutter_width="2"' ); contains( $out, 'make_equal="on"' ); contains( $out, 'custom_padding="11px|0px|11px|0px|false|false"' );
} );
test( 'component classes only from allowlist', function () {
	$s = spec( array( array( 'type' => 'text', 'css_class' => 'rd-pills rd-pills--red', 'html' => '<ul><li>Free tool</li></ul>' ) ) );
	no_err( WPBA_Spec::validate( $s ) );
	contains( WPBA_Render::render( $s ), 'module_class="rd-pills rd-pills--red"' );
} );
test( 'missing text detects dropped words', function () {
	$src  = array( array( 'text' => 'The connectors we tried needed paid plans or never finished authorising.' ), array( 'text' => 'Get the code from . It is free under the MIT licence.' ) );
	$full = spec( array( array( 'type' => 'text', 'html' => '<p>The connectors we tried needed paid plans or never finished authorising.</p><p>Get the code from <a href=\'https://x.com\'>GitHub</a>. It is free under the MIT licence.</p>' ) ) );
	$cut  = spec( array( array( 'type' => 'text', 'html' => '<p>The connectors we tried needed paid plans.</p><p>Get the code from <a href=\'https://x.com\'>GitHub</a>. It is free under the MIT licence.</p>' ) ) );
	eq( WPBA_Spec::missing_text( $src, $full ), array() );
	eq( WPBA_Spec::missing_text( $src, $cut ), array( 'The connectors we tried needed paid plans or never finished authorising.' ) );
} );
test( 'button url schemes', function () {
	$b = function ( $url ) { return spec( array( array( 'type' => 'button', 'text' => 'Email us', 'url' => $url ) ) ); };
	no_err( WPBA_Spec::validate( $b( 'mailto:info@example.com?subject=Hi%20there' ) ) );
	foreach ( array( 'javascript:alert(1)', 'mailto:a b', 'data:text/html,x' ) as $bad ) { is_err( WPBA_Spec::validate( $b( $bad ) ) ); }
} );
test( 'span colour only', function () {
	no_err( WPBA_Spec::check_html( '<h1>Get <span style="color:#3c83f6">cited</span></h1>', 't' ) );
	foreach ( array( '<span style="color:red">x</span>', '<span style="color:#3c83f6;background:url(x)">x</span>', '<span class="x">x</span>', '<span style="position:fixed">x</span>' ) as $bad ) { is_err( WPBA_Spec::check_html( $bad, 't' ) ); }
} );
test( 'json schema is well-formed and lists every module type', function () {
	$js = WPBA_Spec::json_schema();
	$types = array_map( function ( $m ) { return $m['properties']['type']['const']; }, $js['properties']['sections']['items']['properties']['rows']['items']['properties']['columns']['items']['properties']['modules']['items']['oneOf'] );
	eq( $types, array( 'text', 'button', 'image', 'blurb', 'toggle', 'code' ) );
	ok( strlen( json_encode( $js ) ) > 2000 );
} );

echo "== restyle ==\n";
$T = WPBA_Restyle::themes(); $NR = $T['navy-red']; $PAGE = WPBA_Restyle::PAGE; $CARD = WPBA_Restyle::CARD; $LINE = WPBA_Restyle::LINE;
test( 'roles', function () {
	eq( WPBA_Restyle::role_of( 'background_color' ), 'background' ); eq( WPBA_Restyle::role_of( 'open_toggle_background_color' ), 'background' );
	eq( WPBA_Restyle::role_of( 'text_text_color' ), 'text' ); eq( WPBA_Restyle::role_of( 'header_2_text_color' ), 'text' );
	eq( WPBA_Restyle::role_of( 'icon_color' ), 'icon' ); eq( WPBA_Restyle::role_of( 'border_color_all' ), 'border' ); eq( WPBA_Restyle::role_of( 'button_border_color' ), 'border' );
	eq( WPBA_Restyle::role_of( 'button_bg_color' ), 'button_bg' ); eq( WPBA_Restyle::role_of( 'button_border_radius' ), 'button_radius' );
	eq( WPBA_Restyle::role_of( 'background_color_gradient_stops' ), null ); eq( WPBA_Restyle::role_of( 'admin_label' ), null );
} );
test( 'black background becomes navy but black text stays', function () use ( $NR, $PAGE ) {
	$raw = '[et_pb_section background_color="#000000"][et_pb_text text_text_color="#000000"]<p style="color:#000000">x</p>[/et_pb_text][/et_pb_section]';
	list( $new, $counts ) = WPBA_Restyle::restyle_layout( $raw, $NR );
	contains( $new, "[et_pb_section background_color=\"$PAGE\"]" ); contains( $new, 'text_text_color="#000000"' ); contains( $new, '<p style="color:#000000">x</p>' );
	eq( $counts, array( "background:#000000->$PAGE" => 1 ) );
} );
test( 'cards get border and rounding', function () use ( $NR, $CARD, $LINE ) {
	list( $new, $counts ) = WPBA_Restyle::restyle_layout( '[et_pb_column type="1_3" background_color="#14171b" border_radii="on|0px|0px|0px|0px"]x[/et_pb_column]', $NR );
	contains( $new, "background_color=\"$CARD\"" ); contains( $new, "border_color_all=\"$LINE\"" ); contains( $new, 'border_radii="on|16px|16px|16px|16px"' ); contains( $new, 'border_width_all="1px"' );
	eq( $counts["background:#14171b->$CARD"], 1 ); eq( $counts['card:et_pb_column'], 1 );
} );
test( 'sections are not cards', function () use ( $NR ) {
	list( $new, $counts ) = WPBA_Restyle::restyle_layout( '[et_pb_section background_color="#14171b"][/et_pb_section]', $NR );
	not_contains( $new, 'border_radii' ); ok( ! isset( $counts['card:et_pb_section'] ) );
} );
test( 'buttons icons red and code svg untouched', function () use ( $NR ) {
	$raw = '[et_pb_button custom_button="on" button_bg_color="#e02b20"][/et_pb_button][et_pb_blurb icon_color="#ffffff" header_text_color="#ffffff"][/et_pb_blurb][et_pb_code]<svg><rect fill="#000000" stroke="#26292f"/></svg>[/et_pb_code]';
	list( $new, $counts ) = WPBA_Restyle::restyle_layout( $raw, $NR );
	contains( $new, 'button_bg_color="#e02b20"' ); contains( $new, 'button_border_radius="8px"' ); contains( $new, 'icon_color="#f87171"' ); contains( $new, 'header_text_color="#ffffff"' );
	contains( $new, '<rect fill="#000000" stroke="#26292f"/>' );
	ksort( $counts ); eq( $counts, array( 'button:radius' => 1, 'icon:#ffffff->#f87171' => 1 ) );
} );
test( 'black shadow stays invisible', function () use ( $NR, $PAGE ) { list( $new ) = WPBA_Restyle::restyle_layout( '[et_pb_row box_shadow_color="#000000"][/et_pb_row]', $NR ); contains( $new, "box_shadow_color=\"$PAGE\"" ); } );
test( 'idempotent and upgrades first pilot values', function () use ( $NR, $PAGE, $CARD ) {
	$raw = '[et_pb_section background_color="#0a1120"][et_pb_column background_color="#0f1c2e"]x[/et_pb_column][/et_pb_section]';
	list( $once ) = WPBA_Restyle::restyle_layout( $raw, $NR ); list( $twice, $counts ) = WPBA_Restyle::restyle_layout( $once, $NR );
	contains( $once, $PAGE ); contains( $once, $CARD ); eq( $once, $twice ); eq( $counts, array() );
} );
test( 'navy-blue swaps code css and gradients but not text', function () use ( $T ) {
	$raw = '[et_pb_section background_color_gradient_stops="rgba(224,43,32,0.28) 0%|rgba(0,0,0,0) 55%"][et_pb_code]<style>.a{color:#e02b20}</style><p style="color:#b8bec6">#e02b20 stays in text</p>[/et_pb_code][/et_pb_section]';
	list( $new, $counts ) = WPBA_Restyle::apply_theme( $raw, $T['navy-blue'] );
	contains( $new, 'rgba(60,131,246,0.28)' ); contains( $new, '.a{color:#3c83f6}' ); contains( $new, 'style="color:#94a3b8"' ); contains( $new, '#e02b20 stays in text' );
	eq( $counts['gradient'], 1 ); eq( $counts['code_css'], 2 );
	eq( WPBA_Restyle::visible_text( $new ), WPBA_Restyle::visible_text( $raw ) );
} );

echo "== header glow ==\n";
$GLOW = array( 'color' => '#e02b20', 'opacity' => 0.28, 'position' => 'top right', 'fade_at_percent' => 55 );
$BODY = '[et_pb_row][et_pb_column type="4_4"][et_pb_text]Hi[/et_pb_text][/et_pb_column][/et_pb_row][/et_pb_section]';
test( 'adds gradient to first section only', function () use ( $GLOW, $BODY ) {
	$raw = '[et_pb_section fb_built="1" background_color="#000000"]' . $BODY . '[et_pb_section background_color="#000000"]x[/et_pb_section]';
	list( $new, $status ) = WPBA_Header_Glow::add_glow( $raw, $GLOW );
	eq( $status, 'change' );
	$first = substr( $new, 0, strpos( $new, ']' ) ); $rest = substr( $new, strpos( $new, ']' ) + 1 );
	contains( $first, 'use_background_color_gradient="on"' ); contains( $first, 'background_color="#000000"' ); contains( $first, 'rgba(224,43,32,0.28) 0%|rgba(0,0,0,0) 55%' );
	eq( $rest, substr( $raw, strpos( $raw, ']' ) + 1 ) ); eq( substr_count( $new, 'use_background_color_gradient' ), 1 );
} );
test( 'skips', function () use ( $GLOW, $BODY ) {
	ok( 0 === strpos( WPBA_Header_Glow::add_glow( '[et_pb_section background_color="#ffffff"]' . $BODY, $GLOW )[1], 'skip: header background' ) );
	eq( WPBA_Header_Glow::add_glow( '[et_pb_section background_color="#000000" background_image="x.jpg"]' . $BODY, $GLOW )[1], 'skip: section has a background image' );
	eq( WPBA_Header_Glow::add_glow( '[et_pb_section background_color="#000000" use_background_color_gradient="on"]' . $BODY, $GLOW )[1], 'skip: already has a gradient' );
	eq( WPBA_Header_Glow::add_glow( '<p>classic content</p>', $GLOW )[1], 'skip: no Divi section' );
} );
test( 'opacity formatting like %g', function () { eq( WPBA_Header_Glow::g( 1.0 ), '1' ); eq( WPBA_Header_Glow::g( 0.28 ), '0.28' ); eq( WPBA_Header_Glow::g( 0.5 ), '0.5' ); } );

echo "== theme css merge ==\n";
$END = WPBA_Theme_CSS::BLOCK_END;
$V1 = "/* wp-builder-agent: reusable components. Added 2026-10-09. */\n.rd-pills li{border-radius:999px}";
$V2 = "/* wp-builder-agent: reusable components v2 */\n.rd-pills li{border-radius:6px}\n" . $END;
test( 'append to empty', function () use ( $V2 ) { eq( WPBA_Theme_CSS::merge_block( '', $V2 ), $V2 . "\n" ); } );
test( 'replace v1 without end marker', function () use ( $V1, $V2 ) { $out = WPBA_Theme_CSS::merge_block( $V1 . "\n", $V2 ); not_contains( $out, '999px' ); eq( trim( $out ), $V2 ); } );
test( 'replace v2 keeps other css before and after', function () use ( $V2 ) {
	$before = ".mine{color:red}\n\n" . $V2 . "\n.after{color:blue}\n"; $v3 = str_replace( '6px', '4px', $V2 );
	$out = WPBA_Theme_CSS::merge_block( $before, $v3 );
	ok( 0 === strpos( $out, '.mine{color:red}' ) ); contains( $out, '.after{color:blue}' ); contains( $out, '4px' ); not_contains( $out, '6px' );
} );

echo "== plan validation + normalize ==\n";
$CUST = array( 'et_divi[all_buttons_bg_color]' => 'rgba(0,0,0,0)', 'et_divi[all_buttons_border_radius]' => '3', 'et_divi[all_buttons_border_radius_hover]' => false );
$VERIFY = array( array( 'page' => '/', 'selector' => '.et_pb_button_0', 'css_property' => 'border-radius', 'expected' => '6px' ) );
function change( $setting = 'et_divi[all_buttons_border_radius]', $old = '3', $new = '6' ) { return array( 'action' => 'customizer_set', 'setting' => $setting, 'old_value' => $old, 'new_value' => $new, 'reason' => 'r' ); }
function plan( array $changes, $rung = 'theme_options_or_customizer', $verify = null, $feasible = true ) { global $VERIFY; return array( 'task' => 't', 'feasible' => $feasible, 'rung' => $rung, 'changes' => $changes, 'verify' => null === $verify ? $VERIFY : $verify ); }
test( 'valid plan passes', function () use ( $CUST ) { no_err( WPBA_Plan_Schema::validate( plan( array( change() ) ), $CUST ) ); } );
test( 'false setting reads as empty old value', function () use ( $CUST ) { no_err( WPBA_Plan_Schema::validate( plan( array( change( 'et_divi[all_buttons_border_radius_hover]', '', '6' ) ) ), $CUST ) ); } );
$badplans = array(
	array( plan( array( change( 'et_divi[all_buttons_border_radius]', '4' ) ) ), 'old value' ),
	array( plan( array( change( 'et_divi[made_up]' ) ) ), 'Unknown' ),
	array( plan( array( change( 'custom_css' ) ) ), 'Unknown' ),
	array( plan( array( change( 'et_divi[all_buttons_border_radius]', '3', '6px;}body{display:none' ) ) ), 'code' ),
	array( plan( array( change(), change() ) ), 'twice' ),
	array( plan( array( change() ), 'theme_custom_css' ), 'CSS' ),
	array( plan( array( change() ), 'theme_options_or_customizer', array() ), 'verification' ),
	array( plan( array() ), 'no changes' ),
	array( plan( array( change() ), 'theme_options_or_customizer', null, false ), 'Infeasible' ),
	array( plan( array( change() ), 'theme_options_or_customizer', array( array( 'page' => 'home' ) ) ), 'path' ),
);
foreach ( $badplans as $i => $c ) { test( "bad plan rejected #$i ({$c[1]})", function () use ( $c, $CUST ) { is_err( WPBA_Plan_Schema::validate( $c[0], $CUST ), $c[1] ); } ); }
test( 'css rung allowed with explicit flag', function () use ( $CUST ) { no_err( WPBA_Plan_Schema::validate( plan( array( change() ), 'module_custom_css' ), $CUST, true ) ); } );
test( 'plan json schema is a closed object', function () { $s = WPBA_Plan_Schema::json_schema(); eq( $s['additionalProperties'], false ); ok( in_array( 'changes', $s['required'], true ) ); } );

echo "== verify normalize ==\n";
foreach ( array( array( '#ff8a3d', 'rgb(255, 138, 61)' ), array( '#FFF', 'rgb(255, 255, 255)' ), array( 'rgba(255,138,61,1)', 'rgb(255, 138, 61)' ), array( 'rgba(0, 0, 0, 0)', 'rgba(0,0,0,0)' ), array( ' 6px ', '6px' ) ) as $pair ) {
	test( "normalize {$pair[0]} == {$pair[1]}", function () use ( $pair ) { eq( WPBA_Verify::normalize( $pair[0] ), WPBA_Verify::normalize( $pair[1] ) ); } );
}

echo "== components ==\n";
test( 'registry reads assets', function () { $r = WPBA_Components::registered(); ok( in_array( 'rd-pills', $r, true ) ); ok( in_array( 'rd-kpi', $r, true ) ); ok( in_array( 'rd-steps', $r, true ) ); } );
test( 'bundle has markers', function () { $b = WPBA_Components::bundle(); ok( 0 === strpos( $b, WPBA_Theme_CSS::BLOCK_START ) ); contains( $b, WPBA_Theme_CSS::BLOCK_END ); contains( $b, '.rd-pills' ); } );
test( 'valid new component', function () { no_err( WPBA_NewComponents::check( array( 'name' => 'rd-score-ring', 'usage' => 't', 'css' => '.rd-score-ring{border-radius:50%}.rd-score-ring--red p{color:#f87171}@media (max-width:767px){.rd-score-ring{width:80px}}.rd-score-ring::after{background:url("data:image/svg+xml,%3Csvg%3E%3C/svg%3E")}' ) ) ); } );
$badcss = array( array( 'body{color:red}', 'must start with' ), array( '.rd-score-ring, .et_pb_button{color:red}', 'must start with' ), array( '.rd-score-ringx{color:red}', 'must start with' ), array( '.rd-score-ring a[href]{color:red}', 'brackets' ), array( '@import url(x.css);.rd-score-ring{}', 'imports' ), array( '.rd-score-ring{background:url(https://evil.example/x.png)}', 'data:image' ), array( '.rd-score-ring{position: fixed}', 'fixed' ) );
foreach ( $badcss as $i => $c ) { test( "bad component rejected #$i ({$c[1]})", function () use ( $c ) { is_err( WPBA_NewComponents::check( array( 'name' => 'rd-score-ring', 'usage' => 't', 'css' => $c[0] ) ), $c[1] ); } ); }
test( 'bad name and existing', function () { is_err( WPBA_NewComponents::check( array( 'name' => 'Foo', 'usage' => 't', 'css' => '.Foo{}' ) ), 'names' ); is_err( WPBA_NewComponents::check( array( 'name' => 'rd-kpi', 'usage' => 't', 'css' => '.rd-kpi{}' ) ), 'already exists' ); } );
test( 'saved component registers its class', function () {
	no_err( WPBA_NewComponents::save( array( array( 'name' => 'rd-testring', 'usage' => 'u', 'css' => '.rd-testring{color:#fff}' ) ) ) );
	ok( in_array( 'rd-testring', WPBA_Components::registered(), true ) );
	no_err( WPBA_Spec::validate( spec( array( array( 'type' => 'text', 'css_class' => 'rd-testring', 'html' => '<p>x</p>' ) ) ) ) );
} );
test( 'extract json from prose', function () { eq( WPBA_Claude::extract_json( "Sure:\n```json\n{\"a\": 1}\n```" ), '{"a": 1}' ); eq( WPBA_Claude::extract_json( 'x {"a": {"b": 2}} y' ), '{"a": {"b": 2}}' ); } );

$t = $GLOBALS['wpba_tests'];
echo "\n{$t['pass']} passed, {$t['fail']} failed\n";
exit( $t['fail'] ? 1 : 0 );
