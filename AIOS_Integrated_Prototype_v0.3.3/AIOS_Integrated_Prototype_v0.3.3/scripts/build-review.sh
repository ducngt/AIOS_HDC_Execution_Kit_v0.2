#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/dist/review"
rm -rf "$OUT"
mkdir -p "$OUT/ui"
cp -a "$ROOT/ui/." "$OUT/ui/"
cp "$ROOT/index.html" "$OUT/index.html"
touch "$OUT/.nojekyll"
echo "AIOS static review created at: $OUT"
