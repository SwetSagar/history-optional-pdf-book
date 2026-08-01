#!/bin/bash
# OCR a folder of scanned PDFs into per-page JSON using pipeline/ocr/ocr.
#
#   ./pipeline/ocr/run.sh "<source folder>" <corpus name>
#
# Skips files already done, so it is safe to re-run after an interruption.
set -uo pipefail

SRC="${1:?usage: run.sh <source folder> <corpus name>}"
NAME="${2:?usage: run.sh <source folder> <corpus name>}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="$ROOT/corpus/$NAME"
BIN="$ROOT/pipeline/ocr/ocr"

[ -x "$BIN" ] || { echo "build first: swiftc -O pipeline/ocr/ocr.swift -o pipeline/ocr/ocr"; exit 1; }
mkdir -p "$OUT"

echo "file|pages|chars|empty_pages|confidence" > "$OUT/_summary.psv"
shopt -s nullglob
for pdf in "$SRC"/*.pdf; do
    base="$(basename "$pdf" .pdf)"
    dest="$OUT/$base.json"
    if [ -s "$dest" ]; then
        echo "skip (done): $base"
        continue
    fi
    echo "OCR: $base"
    if "$BIN" "$pdf" "$dest" 2.0 2>/dev/null >> "$OUT/_summary.psv"; then
        :
    else
        echo "  FAILED: $base" >&2
        rm -f "$dest"
    fi
done

echo
echo "done -> $OUT"
