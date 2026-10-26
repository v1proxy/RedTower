#!/usr/bin/env bash
# Runs the whole chain from the source .blend: build, finalize, the repaints and the furniture. About 4 minutes.
#   ./rebuild_all.sh path/to/redtower.blend path/to/ha-floorplan [blender]
set -euo pipefail
SRC="$1"; OUT="$2"; BLENDER="${3:-blender}"; S="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$OUT"; LOG="$OUT/rebuild.log"
echo build > "$LOG"
"$BLENDER" -b "$SRC" --python "$S/build_ha.py" -- "$OUT" >> "$LOG" 2>&1
echo finalize >> "$LOG"
"$BLENDER" -b "$OUT/redtower_ha.blend" --python "$S/finalize.py" -- "$OUT" >> "$LOG" 2>&1
for p in repaint.py repaint2.py repaint3.py repaint4.py repaint5.py furnish_bedroom.py furnish_living.py furnish_car.py; do
  echo "$p" >> "$LOG"
  "$BLENDER" -b "$OUT/redtower_ha.blend" --python "$S/$p" -- "$OUT" >> "$LOG" 2>&1
done
rm -f "$OUT/redtower_ha.blend1"; echo DONE >> "$LOG"
