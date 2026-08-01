"""One entry point for the whole pipeline.

    python3 pipeline/manage.py <command> [args]

    extract        rebuild records and reports from the source folders
    validate       cross-check coordinates against stated regions
    maps           render one locator map per site
    cover          regenerate the cover art
    epub           assemble the eBook
    build          maps + cover + epub, in order
    all            extract + validate + build
    test           run the regression suite

    cite <args>    search the source corpus            (cite.py)
    sources <args> propose / confirm citations         (link_sources.py)
    gazetteer <a>  resolve coordinates against Wikidata
    pyq            mine the past papers
    ingest         OCR library works into corpus/
    evidence <ch>  evidence pack for writing a chapter
    status         one-screen summary of where the book stands
"""
from __future__ import annotations

import json
import runpy
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIPE = ROOT / "pipeline"


def run(script: str, args: list[str] | None = None) -> int:
    r = subprocess.run([sys.executable, str(PIPE / script), *(args or [])], cwd=ROOT)
    return r.returncode


def status(_args: list[str]) -> int:
    sys.path.insert(0, str(PIPE))
    from common import load_frontmatter
    from collections import Counter

    counts: Counter[str] = Counter()
    coords = sourced = thin = 0
    for p in (ROOT / "sites").rglob("*.md"):
        meta, body = load_frontmatter(p.read_text(encoding="utf-8"))
        counts[str(meta.get("status"))] += 1
        if meta.get("coords"):
            coords += 1
        if meta.get("sources"):
            sourced += 1
        if meta.get("status") != "missing" and len(body.split()) < 30:
            thin += 1

    total = sum(counts.values())
    print(f"records            {total}")
    for k in ("missing", "raw", "written", "sourced", "final"):
        if counts.get(k):
            print(f"  {k:<16} {counts[k]}")
    print(f"with a coordinate  {coords}")
    print(f"with a citation    {sourced}")
    print(f"under 30 words     {thin}")

    epub = ROOT / "build" / "Map Entries for History Optional.epub"
    if epub.exists():
        mb = epub.stat().st_size / 1e6
        print(f"eBook              {epub.name}  {mb:.1f} MB")
    gaz = ROOT / "data" / "gazetteer.json"
    if gaz.exists():
        g = json.loads(gaz.read_text(encoding="utf-8"))
        c = Counter(v["verdict"] for v in g.values())
        print(f"gazetteer          {c['confirmed']} confirmed, {c['review']} to review, "
              f"{c['unresolved']} unresolved")
    return 0


def build(_args: list[str]) -> int:
    for script in ("render_maps.py", "make_cover.py", "build_epub.py"):
        if run(script):
            return 1
    return 0


def everything(_args: list[str]) -> int:
    for script in ("extract.py", "validate.py"):
        if run(script):
            return 1
    return build([])


COMMANDS = {
    "extract":   lambda a: run("extract.py", a),
    "validate":  lambda a: run("validate.py", a),
    "maps":      lambda a: run("render_maps.py", a),
    "cover":     lambda a: run("make_cover.py", a),
    "epub":      lambda a: run("build_epub.py", a),
    "build":     build,
    "all":       everything,
    "test":      lambda a: run("test_pipeline.py", a),
    "cite":      lambda a: run("cite.py", a),
    "sources":   lambda a: run("link_sources.py", a),
    "gazetteer": lambda a: run("gazetteer.py", a),
    "pyq":       lambda a: run("pyq.py", a),
    "ingest":    lambda a: run("ingest.py", a),
    "evidence":  lambda a: run("evidence.py", a),
    "status":    status,
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"unknown command {cmd!r}\n", file=sys.stderr)
        print(__doc__)
        return 2
    return COMMANDS[cmd](sys.argv[2:])


if __name__ == "__main__":
    raise SystemExit(main())
