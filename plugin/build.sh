#!/usr/bin/env bash
# Build plugin/dist/wp-builder-agent.zip: syncs the shared component CSS from assets/ into the plugin, lints
# every PHP file, runs the PHP unit tests, then zips the plugin folder ready for Plugins > Add New > Upload.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLUGIN="$ROOT/plugin/wp-builder-agent"
cp "$ROOT"/assets/*.css "$PLUGIN/assets/components/"
for f in $(find "$PLUGIN" -name '*.php'); do php -l "$f" > /dev/null; done
php "$ROOT/tests/php/run.php" > /dev/null
mkdir -p "$ROOT/plugin/dist"
rm -f "$ROOT/plugin/dist/wp-builder-agent.zip"
( cd "$ROOT/plugin" && zip -qr dist/wp-builder-agent.zip wp-builder-agent -x '*.DS_Store' )
echo "Built $ROOT/plugin/dist/wp-builder-agent.zip ($(du -h "$ROOT/plugin/dist/wp-builder-agent.zip" | cut -f1))"
