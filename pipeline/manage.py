"""Unified Command-Line Manager for the UPSC History Optional eBook Pipeline.

Usage:
    python3 pipeline/manage.py build [--all]    Assemble the EPUB eBook
    python3 pipeline/manage.py extract           Rebuild site records and indices from raw sheets
    python3 pipeline/manage.py validate          Cross-check coordinates against state bounding boxes
    python3 pipeline/manage.py link-sources      Auto-link candidate corpus citations to frontmatter
    python3 pipeline/manage.py draft             Draft 4-anchor UPSC entries for missing/thin entries
    python3 pipeline/manage.py cover             Generate high-DPI Modernist book cover image
    python3 pipeline/manage.py test              Run automated unit test suite
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

    if action == "build":
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
        return run_script("render_cover.py", extra_args)
    elif action == "test":
        cmd = [sys.executable, "-m", "unittest", str(PIPELINE / "test_pipeline.py")]
        return subprocess.call(cmd)
    else:
        print(f"Unknown action {action!r}\n")
        print(__doc__)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
