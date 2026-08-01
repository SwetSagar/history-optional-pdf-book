"""Write drafted prose into site records.

    python3 pipeline/apply_prose.py <prose_file.py>

The prose file defines PROSE = {slug: text}. Each entry replaces the record's
body and moves its status to `written`. Frontmatter is otherwise untouched, and
a slug that matches no record is reported rather than silently dropped.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import dump_frontmatter, load_frontmatter  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SITES = ROOT / "sites"


def load_prose(path: Path) -> dict[str, str]:
    spec = importlib.util.spec_from_file_location("prose_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.PROSE


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    prose = load_prose(Path(sys.argv[1]))
    index = {p.stem: p for p in SITES.rglob("*.md")}

    written, missing = 0, []
    for slug, text in prose.items():
        md = index.get(slug)
        if md is None:
            missing.append(slug)
            continue
        meta, _ = load_frontmatter(md.read_text(encoding="utf-8"))
        meta["status"] = "written"
        md.write_text(dump_frontmatter(meta) + "\n\n" + " ".join(text.split()) + "\n",
                      encoding="utf-8")
        written += 1

    print(f"written : {written}")
    if missing:
        print(f"no such record: {missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
