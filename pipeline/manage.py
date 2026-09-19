"""Unified Command-Line Manager for the UPSC History Optional eBook Pipeline.

Usage:
    python3 pipeline/manage.py pdf [--all]       Assemble the A4 print PDF
    python3 pipeline/manage.py notes [--write]   Condense each entry to a 30-50 word exam note
    python3 pipeline/manage.py exam              Assemble the A4 revision booklet
    python3 pipeline/manage.py build [--all]     Assemble the EPUB eBook
    python3 pipeline/manage.py maps [--print]    Render one locator map per site
    python3 pipeline/manage.py web [--write]     Export canonical records for Sarvam
    python3 pipeline/manage.py extract           Rebuild site records and indices from raw sheets
    python3 pipeline/manage.py validate          Cross-check coordinates against state bounding boxes
    python3 pipeline/manage.py link-sources      Auto-link candidate corpus citations to frontmatter
    python3 pipeline/manage.py draft             Draft 4-anchor UPSC entries for missing/thin entries
    python3 pipeline/manage.py cover             Render the cover (every located site plotted)
    python3 pipeline/manage.py test              Run automated unit test suite

A PDF from nothing is three steps, in this order:

    python3 pipeline/manage.py maps --print      locators drawn for 31mm of paper
    python3 pipeline/manage.py cover             build/cover.png
    python3 pipeline/manage.py pdf

The revision booklet is two, and the first must come first — `exam` refuses to
build from a stale data/exam-notes.json rather than printing old wording:

    python3 pipeline/manage.py notes --write     data/exam-notes.json
    python3 pipeline/manage.py exam
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIPELINE = ROOT / "pipeline"


def run_script(script_name: str, args: list[str]) -> int:
    cmd = [sys.executable, str(PIPELINE / script_name)] + args
    print(f"Executing: {' '.join(cmd)}\n")
    return subprocess.call(cmd)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    action = sys.argv[1].lower()
    extra_args = sys.argv[2:]

    if action == "pdf":
        return run_script("build_pdf.py", extra_args)
    elif action == "notes":
        return run_script("exam_notes.py", extra_args)
    elif action == "exam":
        return run_script("build_exam_pdf.py", extra_args)
    elif action == "maps":
        return run_script("render_maps.py", extra_args)
    elif action == "web":
        return run_script("export_web.py", extra_args)
    elif action == "build":
        return run_script("build_epub.py", extra_args)
    elif action == "extract":
        return run_script("extract.py", extra_args)
    elif action == "validate":
        return run_script("validate.py", extra_args)
    elif action == "link-sources":
        if "--write" not in extra_args and "--apply" not in extra_args:
            extra_args.append("--write")
        return run_script("link_sources.py", extra_args)
    elif action == "draft":
        if "--write" not in extra_args and "--apply" not in extra_args:
            extra_args.append("--write")
        return run_script("draft_corpus.py", extra_args)
    elif action == "cover":
        # the atlas cover — the book's own data as the artwork. render_cover.py
        # is the alternative, a typographic cover with no map on it.
        return run_script("make_cover.py", extra_args)
    elif action == "test":
        cmd = [sys.executable, "-m", "unittest", str(PIPELINE / "test_pipeline.py")]
        return subprocess.call(cmd)
    else:
        print(f"Unknown action {action!r}\n")
        print(__doc__)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
