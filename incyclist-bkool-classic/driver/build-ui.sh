#!/usr/bin/env bash
# Rebuild the patched Incyclist interface (incyclist/web-ui) with the Bkool Classic driver.
# Requires git and Node.js 22+. Works on Linux, macOS and Windows (Git Bash / WSL).
#
#   bash build-ui.sh [web-ui tag] [devices tag]
#
# Defaults match Incyclist desktop 26.10.1, whose bundled interface is web-ui v26.10.10 using
# incyclist-devices 3.0.42. Pick the web-ui tag that matches your Incyclist version and the
# devices version from that tag's package-lock.json.
set -euo pipefail
WEBUI_TAG="${1:-v26.10.10}"
DEVICES_TAG="${2:-v3.0.42}"
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${WORK:-$HERE/../build-work}"
OUT="$HERE/../incyclist/incyclist-bkool-ui"

mkdir -p "$WORK"
cd "$WORK"
rm -rf devices web-ui

echo "== incyclist/devices $DEVICES_TAG + Bkool Classic adapter"
git clone -q --depth 1 --branch "$DEVICES_TAG" https://github.com/incyclist/devices.git devices
cd devices
git -c user.name=build -c user.email=build@localhost am -q --3way "$HERE/0001-bkool-classic-adapter.patch"
npm ci --no-audit --no-fund --ignore-scripts
npm run build
cd ..

echo "== incyclist/web-ui $WEBUI_TAG"
git clone -q --depth 1 --branch "$WEBUI_TAG" https://github.com/incyclist/web-ui.git web-ui
cd web-ui
npm ci --no-audit --no-fund --ignore-scripts
rm -rf node_modules/incyclist-devices/lib
cp -r ../devices/lib node_modules/incyclist-devices/lib
PROD=1 npx vite build

rm -rf "$OUT"
cp -r build "$OUT"
echo "== done: $OUT"
