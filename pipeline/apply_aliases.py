"""Weave historical and modern place-names into the entry prose.

    python3 pipeline/apply_aliases.py            preview
    python3 pipeline/apply_aliases.py --write    apply

Readers meet these sites under one name in the exam and a different one in the
sources — the cards say Kozhikode, Satish Chandra says Calicut. Naming both in
the entry closes that gap.

Only genuinely different names are added. A spelling variant of the record's own
name (Nashik/Nasik) tells the reader nothing, and an alias already present in the
name or body is skipped.
"""
from __future__ import annotations

import difflib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import dump_frontmatter, load_frontmatter, match_keys  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SIMILAR = 0.82        # above this, an "alias" is just a respelling


def variant_of(a: str, b: str) -> bool:
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio() >= SIMILAR


def main() -> int:
    write = "--write" in sys.argv
    al = json.loads((ROOT / "data" / "aliases.json").read_text(encoding="utf-8"))["aliases"]

    records = {}
    for p in sorted((ROOT / "sites").rglob("*.md")):
        meta, body = load_frontmatter(p.read_text(encoding="utf-8"))
        if meta.get("status") == "missing":
            continue
        records[p] = (meta, body, match_keys(meta.get("name", "")))

    planned, skipped, nomatch, conflicts = [], [], [], []
    for modern, historicals in al.items():
        group = [modern] + list(historicals)
        target = None
        for member in group:
            mk = match_keys(member)
            for p, (meta, body, keys) in records.items():
                if mk & keys:
                    target = (p, meta, body, member)
                    break
            if target:
                break
        if not target:
            nomatch.append(modern)
            continue

        p, meta, body, matched = target
        name = meta.get("name", "")
        now_names, old_names = [], []
        for o in group:
            if o.lower() == matched.lower():
                continue
            if re.search(rf"\b{re.escape(o.lower())}\b", name.lower()):
                continue                                  # already in the title
            if re.search(rf"\b{re.escape(o.lower())}\b", body.lower()):
                continue                                  # already in the prose
            if variant_of(o, matched) or variant_of(o, name):
                skipped.append((name, o, "respelling"))
                continue
            # If the other name is itself a separate record, these are two entries
            # for one place. Naming each inside the other would have them claim
            # each other's identity; that needs merging, not an alias.
            ok = match_keys(o)
            clash = next((m.get("name") for q, (m, _, k) in records.items()
                          if q != p and ok & k), None)
            if clash:
                conflicts.append((name, o, clash))
                continue
            (old_names if o.lower() != modern.lower() else now_names).append(o)

        clauses = []
        if now_names:
            clauses.append(f"It is now known as {' or '.join(now_names)}.")
        if old_names:
            clauses.append(f"It is known in the older sources as {' or '.join(old_names)}.")
        if not clauses:
            continue
        planned.append((p, meta, body, name, " ".join(clauses)))

    print(f"entries to update : {len(planned)}")
    print(f"respellings skipped: {len(skipped)}")
    print(f"no matching record : {len(nomatch)}")
    if conflicts:
        print(f"\nBOTH NAMES EXIST AS SEPARATE RECORDS — merge these, do not alias:")
        for a, o, b in conflicts:
            print(f"   {a}  <-->  {b}   (via {o})")
    print()
    for _, _, _, name, clause in planned:
        print(f"  {name:<30} {clause}")

    if write:
        for p, meta, body, _, clause in planned:
            meta["aliases_added"] = True
            p.write_text(dump_frontmatter(meta) + "\n\n" + body.rstrip() + " " + clause + "\n",
                         encoding="utf-8")
        print(f"\nwritten: {len(planned)}")
    else:
        print("\n(preview — rerun with --write to apply)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
