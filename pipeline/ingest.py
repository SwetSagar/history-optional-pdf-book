"""Ingest the works listed in data/sources.json into corpus/.

    python3 pipeline/ingest.py            ingest anything not already done
    python3 pipeline/ingest.py --list     show status without doing work

Uses pipeline/ocr/ocr, which takes the PDF's own text layer where one exists
and falls back to Vision OCR for scanned pages. Already-ingested files are
skipped, so this is safe to re-run.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "pipeline" / "ocr" / "ocr"
CORPUS = ROOT / "corpus"
MANIFEST = ROOT / "data" / "sources.json"


def targets(work: dict, lib: Path) -> list[Path]:
    src = lib / work["path"]
    if work["kind"] == "folder":
        return sorted(src.glob("*.pdf"))
    return [src] if src.exists() else []


def main() -> int:
    if not BIN.exists():
        print("build first: swiftc -O pipeline/ocr/ocr.swift -o pipeline/ocr/ocr",
              file=sys.stderr)
        return 1
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    lib = Path(manifest["library_root"])
    listing = "--list" in sys.argv
    bib = json.loads((ROOT / "data" / "bibliography.json").read_text(encoding="utf-8"))

    todo: list[tuple[dict, Path, Path]] = []
    for work in manifest["works"]:
        if work["key"] not in bib:
            print(f"  ! {work['key']} is not in bibliography.json", file=sys.stderr)
        out_dir = CORPUS / work["corpus"]
        found = targets(work, lib)
        if not found:
            print(f"  MISSING  {work['key']}: {work['path']}")
            continue
        for pdf in found:
            dest = out_dir / (pdf.stem + ".json")
            state = "done" if dest.exists() and dest.stat().st_size > 0 else "todo"
            if listing:
                print(f"  {state:<5} {work['corpus']}/{pdf.stem[:52]}")
            elif state == "todo":
                todo.append((work, pdf, dest))

    if listing:
        return 0
    if not todo:
        print("nothing to do — corpus is up to date")
        return 0

    print(f"ingesting {len(todo)} file(s)")
    for work, pdf, dest in todo:
        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"  {work['corpus']}: {pdf.name[:60]}", flush=True)
        r = subprocess.run([str(BIN), str(pdf), str(dest), "2.0"],
                           capture_output=True, text=True)
        if r.returncode != 0 or not dest.exists():
            print(f"    FAILED: {r.stderr.strip()[:160]}", file=sys.stderr)
            dest.unlink(missing_ok=True)
            continue
        parts = r.stdout.strip().split("|")
        if len(parts) >= 5:
            print(f"    {parts[1]} pages · {int(parts[2]):,} chars · conf {parts[4]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
