#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/dist/review"

rm -rf "$OUT"

mkdir -p \
  "$OUT/i18n" \
  "$OUT/tasks" \
  "$OUT/change-packages" \
  "$OUT/engineering-evidence" \
  "$OUT/acceptance-packages" \
  "$OUT/governance/decisions"

cp "$ROOT/ui/index.html" "$OUT/index.html"
cp "$ROOT/ui/app.css" "$OUT/app.css"
cp "$ROOT/ui/app.js" "$OUT/app.js"

cp -R "$ROOT/ui/i18n/." "$OUT/i18n/"

python - "$ROOT" "$OUT" <<'PY'
import json
import shutil
import sys
from pathlib import Path

root = Path(sys.argv[1])
out = Path(sys.argv[2])

registry = []

for task_dir in sorted((root / "tasks").glob("T[0-9][0-9]")):
    task_file = task_dir / "task.json"

    if not task_file.exists():
        continue

    task = json.loads(task_file.read_text(encoding="utf-8"))

    task_id = task["task_id"]

    out_task_dir = out / "tasks" / task_id
    out_task_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(
        task_file,
        out_task_dir / "task.json"
    )

    item = {
        "task_id": task_id,
        "title": task["title"],
        "status": task["status"],
        "task_path": f"./tasks/{task_id}/task.json",
        "change_path": None,
        "evidence_path": None,
        "acceptance_path": None
    }

    gate = task.get("human_gate", {}).get("record")
    if gate:
        src = root / gate
        if src.exists():
            dst = out / gate
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    cp = root / "change-packages" / f"CP-{task_id}.json"
    if cp.exists():
        shutil.copy2(
            cp,
            out / "change-packages" / cp.name
        )
        item["change_path"] = \
            f"./change-packages/{cp.name}"

    ee = root / "engineering-evidence" / f"EE-{task_id}.json"
    if ee.exists():
        shutil.copy2(
            ee,
            out / "engineering-evidence" / ee.name
        )
        item["evidence_path"] = \
            f"./engineering-evidence/{ee.name}"

    ap = root / "acceptance-packages" / f"AP-{task_id}.json"
    if ap.exists():
        shutil.copy2(
            ap,
            out / "acceptance-packages" / ap.name
        )
        item["acceptance_path"] = \
            f"./acceptance-packages/{ap.name}"

    registry.append(item)

(out / "tasks" / "index.json").write_text(
    json.dumps(registry, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8"
)

print(
    f"Review registry contains {len(registry)} task(s): "
    + ", ".join(x["task_id"] for x in registry)
)
PY

touch "$OUT/.nojekyll"

echo "Review build created at:"
echo "$OUT"
