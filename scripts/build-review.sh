#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/dist/review"

rm -rf "$OUT"
mkdir -p "$OUT"

cp -R "$ROOT/ui/." "$OUT/"

mkdir -p "$OUT/tasks/T00"
mkdir -p "$OUT/governance/decisions"

cp "$ROOT/tasks/T00/task.json" \
   "$OUT/tasks/T00/task.json"

cp "$ROOT/governance/decisions/T00_HUMAN_GATE.md" \
   "$OUT/governance/decisions/T00_HUMAN_GATE.md"

echo "Review build created at:"
echo "$OUT"
