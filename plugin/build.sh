#!/usr/bin/env bash
# Build plugin/dist/builder-agent-for-divi.zip: syncs the shared component CSS from assets/ into the plugin, lints
# every PHP file, runs the PHP unit tests, then zips the plugin folder ready for Plugins > Add New > Upload.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLUGIN="$ROOT/plugin/builder-agent-for-divi"
cp "$ROOT"/assets/*.css "$PLUGIN/assets/components/"
for f in $(find "$PLUGIN" -name '*.php'); do php -l "$f" > /dev/null; done
php "$ROOT/tests/php/run.php" > /dev/null
mkdir -p "$ROOT/plugin/dist"
rm -f "$ROOT/plugin/dist/builder-agent-for-divi.zip"
( cd "$ROOT/plugin" && zip -qr dist/builder-agent-for-divi.zip builder-agent-for-divi -x '*.DS_Store' )
echo "Built $ROOT/plugin/dist/builder-agent-for-divi.zip ($(du -h "$ROOT/plugin/dist/builder-agent-for-divi.zip" | cut -f1))"
