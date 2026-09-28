#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/dist/review"
BACKEND_URL="${AIOS_BACKEND_URL:-}"

rm -rf "$OUT"
mkdir -p "$OUT/ui"

cp -a "$ROOT/ui/." "$OUT/ui/"
cp "$ROOT/index.html" "$OUT/index.html"
cp "$ROOT/app.js" "$OUT/app.js"
cp "$ROOT/app.css" "$OUT/app.css"

cat > "$OUT/runtime-config.js" <<EOF
window.AIOS_BACKEND_URL = '${BACKEND_URL}';
EOF

# Ensure the root Page loads runtime configuration before app.js.
python - "$OUT/index.html" <<'PY'
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")
if "runtime-config.js" not in s:
    s = s.replace(
        '<script src="./app.js"></script>',
        '<script src="./runtime-config.js"></script>\n'
        '  <script src="./app.js"></script>'
    )
p.write_text(s, encoding="utf-8")
PY

touch "$OUT/.nojekyll"
echo "AIOS static review created at: $OUT"
