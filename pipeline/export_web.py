"""Export the canonical site corpus for the Sarvam map-practice application.

The Markdown files under ``sites/`` are the source of truth.  ``data/sites.json``
is an extraction index and deliberately lacks several fields needed by the web
application, so this exporter reads the canonical records directly and joins in
aliases, bibliography metadata, chapter labels and the currently available PYQ
frequency data.

Usage::

    python pipeline/export_web.py             # preview readiness counts
    python pipeline/export_web.py --write     # write data/web-sites.json and report
    python pipeline/export_web.py --check     # fail when generated files are stale

The export is deterministic: it contains no build timestamp.  That makes it safe
to compare in CI and prevents a no-op build from changing a committed artifact.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import canonical_key, load_frontmatter, match_keys  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITES = ROOT / "sites"
REPORTS = ROOT / "reports"
OUTPUT = DATA / "web-sites.json"
REPORT = REPORTS / "web-readiness.md"

# `coords_confidence` is the miner's word for how cleanly it read a dot off the
# scanned exam sheet. It says nothing about whether the result is near the site:
# Burzahom is labelled `high` and sits 139 km from Burzahom. Gating on it flagged
# 52 exact coordinates as suspect and passed the 170 worst ones, so the gate is
# provenance instead — was this coordinate ever checked against a gazetteer?
READ_CONFIDENCE_VOCABULARY = {"high", "medium", "inherited", "gazetteer", "none", ""}
GAZETTEER_CONFIDENCE = {"gazetteer"}

# Checked coordinates, measured against the unambiguous entries in
# data/.wikidata_cache.json that fall inside the sheet's own frame: n=123,
# median 0.0 km, p90 2.2 km. 25 km leaves room for the genuine ambiguity — a
# mound a few miles outside the modern town it is named after — without
# accepting the next district.
#
# Unchecked coordinates get no radius, because the honest answer is that they
# cannot be scored at all. They are digitised dot positions; hand-checking
# Burzahom, Bhimbetka and Mohenjodaro put them 139, 28 and 18 km out. A trainer
# that marks a correct click wrong teaches the error instead of the site.
VERIFIED_RADIUS_KM = 25
POTENTIAL_NON_POINT = re.compile(
    r"\b(valley|basin|hills|range|culture|route|group|sites|hoards|and)\b|\sor\s",
    re.IGNORECASE,
)
UNCERTAIN_LOCATION = re.compile(
    r"\b(generally placed|tentatively (?:placed|located)|"
    r"(?:exact )?(?:site|location) (?:is|remains) (?:unknown|uncertain|disputed)|"
    r"most-cited candidate)\b",
    re.IGNORECASE,
)


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def parse_body(body: str) -> dict:
    """Return the three canonical answer anchors plus the written source line."""
    anchors: dict[str, dict] = {}
    current: dict | None = None
    sources_line = ""

    text = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
    for line in text.splitlines():
        if not line.strip():
            continue
        bullet = re.match(r"^(\s*)[-*+]\s+(.*)$", line)
        if not bullet:
            if current is not None:
                current["summary"] = (current["summary"] + " " + line.strip()).strip()
            continue

        depth, value = len(bullet.group(1)), bullet.group(2).strip()
        source = re.match(r"^\*Sources?\*\s*:?\s*(.*)$", value, flags=re.IGNORECASE)
        if source:
            sources_line = source.group(1).strip().rstrip(".")
            continue

        if depth == 0:
            labelled = re.match(r"^\*\*(.+?)\*\*\s*:?\s*(.*)$", value)
            if labelled:
                label = labelled.group(1).strip()
                current = {"summary": labelled.group(2).strip(), "points": []}
                anchors[label] = current
            else:
                current = None
        elif current is not None:
            current["points"].append(value)

    return {
        "location": anchors.get("Location", {"summary": "", "points": []}),
        "periodLevel": anchors.get("Period/Level", {"summary": "", "points": []}),
        "keyFindsAndSignificance": anchors.get(
            "Key Finds & Significance", {"summary": "", "points": []}
        ),
        "sourcesLine": sources_line,
    }


def bibliography_reference(raw: str, bibliography: dict) -> dict:
    key, marker, locator = raw.partition("#")
    work = bibliography.get(key, {})
    return {
        "ref": raw,
        "key": key,
        "locator": locator if marker else "",
        "author": work.get("author", ""),
        "title": work.get("title", ""),
        "year": work.get("year"),
    }


def alias_assignments(records: list[tuple[Path, dict, str]], aliases_data: dict) -> dict:
    """Map slugs to search aliases while keeping answer aliases unambiguous."""
    configured = aliases_data.get("aliases", {})
    site_keys = {
        path.stem: match_keys(str(meta.get("name", ""))) | {canonical_key(str(meta.get("name", "")))}
        for path, meta, _ in records
    }
    primary_keys: dict[str, set[str]] = defaultdict(set)
    for slug, keys in site_keys.items():
        for key in keys:
            primary_keys[key].add(slug)

    result = {path.stem: {"search": set(), "answer": set(), "ambiguous": set()}
              for path, _, _ in records}
    for canonical, variants in configured.items():
        canonical_keys = match_keys(canonical) | {canonical_key(canonical)}
        targets = sorted(
            slug for slug, keys in site_keys.items()
            if canonical_keys & keys
        )
        if not targets:
            continue

        for slug in targets:
            result[slug]["search"].update([canonical, *variants])

        for variant in variants:
            variant_keys = match_keys(variant) | {canonical_key(variant)}
            primary_conflicts = set().union(
                *(primary_keys.get(key, set()) for key in variant_keys)
            )
            safe = len(targets) == 1 and not (primary_conflicts - set(targets))
            for slug in targets:
                if safe:
                    result[slug]["answer"].add(variant)
                else:
                    result[slug]["ambiguous"].add(variant)

    return result


def resolve_unmatched_pyq(
    records: list[tuple[Path, dict, str]], aliases: dict, unmatched: dict
) -> tuple[dict, dict]:
    """Resolve a PYQ label only when it names exactly one canonical record.

    The source PYQ file intentionally leaves historical names such as Tanjore
    and Cambay unmatched.  They are safe to count after the reviewed alias map
    identifies a unique answer target.  Search-only/ambiguous aliases are not
    considered, so Muziris cannot silently become an answer for Kodungallur.
    """
    targets_by_key: dict[str, set[str]] = defaultdict(set)
    for path, meta, _ in records:
        slug = path.stem
        labels = [str(meta.get("name", slug)), *aliases[slug]["answer"]]
        for label in labels:
            key = canonical_key(label)
            if key:
                targets_by_key[key].add(slug)

    resolved: dict[str, list[dict]] = defaultdict(list)
    remaining = {}
    for label, raw_count in unmatched.items():
        count = int(raw_count)
        targets = targets_by_key.get(canonical_key(str(label)), set())
        if len(targets) == 1:
            slug = next(iter(targets))
            resolved[slug].append({"label": str(label), "count": count})
        else:
            remaining[str(label)] = count

    for labels in resolved.values():
        labels.sort(key=lambda item: item["label"].casefold())
    return dict(resolved), remaining


def pyq_by_record(pyq: dict, resolved: dict) -> dict:
    """Group every mined occurrence under the record it belongs to.

    The frequency is the number of occurrences, and each one names the paper and
    page it was read off, so a claim like "asked four times" can be checked. The
    years travel with it but stay flagged: the 1779-2012 compendium prints many
    papers per page and the miner takes the first year on the page, so a year is
    indicative of the paper, not of the question.
    """
    slug_for_label = dict(pyq.get("matched_labels", {}))
    for slug, labels in resolved.items():
        for item in labels:
            slug_for_label.setdefault(item["label"], slug)

    grouped: dict[str, list[dict]] = defaultdict(list)
    for occurrence in pyq.get("occurrences", []):
        slug = slug_for_label.get(occurrence.get("label"))
        if slug:
            grouped[slug].append({
                "label": occurrence.get("label", ""),
                "year": str(occurrence.get("year", "")),
                "paper": occurrence.get("paper", ""),
                "page": occurrence.get("page"),
            })

    for items in grouped.values():
        items.sort(key=lambda item: (item["year"], item["paper"], item["page"] or 0))
    return dict(grouped)


def chapter_for(path: Path, chapters: dict) -> tuple[str, str]:
    folder = path.parent.name
    moved = chapters.get("move_sites", {}).get(path.stem)
    target = moved or chapters.get("merge_into", {}).get(folder, folder)
    return target, chapters.get("titles", {}).get(target, target)


def collect_records() -> list[tuple[Path, dict, str]]:
    records = []
    for path in sorted(SITES.rglob("*.md")):
        meta, body = load_frontmatter(path.read_text(encoding="utf-8"))
        records.append((path, meta, body))
    return records


def build_export() -> tuple[dict, dict]:
    records = collect_records()
    bibliography = read_json(DATA / "bibliography.json", {})
    aliases_data = read_json(DATA / "aliases.json", {})
    chapters = read_json(DATA / "chapters.json", {})
    pyq = read_json(DATA / "pyq.json", {})
    legacy_sites = read_json(DATA / "sites.json", [])
    gazetteer = read_json(DATA / "gazetteer.json", {}).get("gazetteer", {})

    aliases = alias_assignments(records, aliases_data)
    legacy_by_slug = {record.get("slug"): record for record in legacy_sites}
    resolved_pyq, unmatched_pyq = resolve_unmatched_pyq(
        records, aliases, pyq.get("unmatched", {})
    )
    pyq_occurrences = pyq_by_record(pyq, resolved_pyq)

    coordinate_groups: dict[tuple, list[str]] = defaultdict(list)
    for path, meta, _ in records:
        coords = meta.get("coords")
        if isinstance(coords, list) and len(coords) == 2:
            coordinate_groups[tuple(coords)].append(path.stem)
    collisions = {coords: slugs for coords, slugs in coordinate_groups.items() if len(slugs) > 1}
    collision_slugs = {slug for slugs in collisions.values() for slug in slugs}

    sites = []
    name_mismatches = []
    for path, meta, body in records:
        slug = path.stem
        canonical_name = str(meta.get("name", slug))
        legacy_name = legacy_by_slug.get(slug, {}).get("name")
        if legacy_name is not None and legacy_name != canonical_name:
            name_mismatches.append((slug, str(legacy_name), canonical_name))

        coords = meta.get("coords") if isinstance(meta.get("coords"), list) else []
        verified = meta.get("coords_provisional") is False
        confidence = str(meta.get("coords_confidence", ""))
        provenance = ("gazetteer" if verified and confidence in GAZETTEER_CONFIDENCE
                      else "checked" if verified else "scan-dot")
        sources = meta.get("sources") if isinstance(meta.get("sources"), list) else []
        content = parse_body(body)
        chapter_id, chapter_title = chapter_for(path, chapters)
        explicit_review = str(meta.get("review_status", "")).lower() == "reviewed"
        model_answer = str(meta.get("model_answer_30", "")).strip()
        location_type = str(meta.get("location_type", "point"))

        issues = []
        if len(coords) != 2:
            issues.append("coordinate_missing")
        if not verified:
            issues.append("coordinate_unverified")
        if confidence not in READ_CONFIDENCE_VOCABULARY:
            issues.append("coordinate_confidence_unknown_value")
        if not meta.get("state"):
            issues.append("region_missing")
        if slug in collision_slugs:
            issues.append("coordinate_collision_review")
        location_is_uncertain = UNCERTAIN_LOCATION.search(content["location"]["summary"])
        if (
            POTENTIAL_NON_POINT.search(canonical_name) or location_is_uncertain
        ) and "location_type" not in meta:
            issues.append("location_type_review_required")
        if not sources:
            issues.append("source_metadata_missing")
        if not content["sourcesLine"]:
            issues.append("written_source_line_missing")
        if not explicit_review:
            issues.append("content_review_required")
        if not model_answer:
            issues.append("model_answer_30_missing")

        alias_info = aliases[slug]
        site = {
            "slug": slug,
            "name": canonical_name,
            # Sort on (casefold, exact): folding alone makes two spellings that
            # differ only in case compare equal, and the tie then falls back to
            # set iteration order, which varies per process. The export has to
            # be byte-identical between runs for --check to mean anything.
            "searchAliases": sorted(alias_info["search"], key=lambda s: (s.casefold(), s)),
            "answerAliases": sorted(alias_info["answer"], key=lambda s: (s.casefold(), s)),
            "ambiguousAliases": sorted(alias_info["ambiguous"], key=lambda s: (s.casefold(), s)),
            "categories": meta.get("categories", []),
            "chapter": {"id": chapter_id, "title": chapter_title},
            "stateOrRegion": meta.get("state", ""),
            "location": {
                "type": location_type,
                "coordinates": {"lat": coords[0], "lon": coords[1]} if len(coords) == 2 else None,
                "provenance": provenance,
                "verified": verified,
                # The one field the trainer should branch on. An unverified
                # coordinate is fine to show on a reference map and unfit to
                # mark a student's click against.
                "scorable": verified and len(coords) == 2,
                "acceptedRadiusKm": VERIFIED_RADIUS_KM if verified else None,
                "readConfidence": confidence,
                "source": meta.get("coords_from", ""),
            },
            "content": content,
            "exam": {
                "modelAnswer30": model_answer or None,
                "recallPoints": meta.get("recall_points", [])
                if isinstance(meta.get("recall_points"), list) else [],
            },
            "sources": [bibliography_reference(str(source), bibliography) for source in sources],
            "pyq": {
                "frequency": len(pyq_occurrences.get(slug, [])),
                "years": sorted({item["year"] for item in pyq_occurrences.get(slug, [])}),
                "yearAttributionStatus": "unverified",
                "occurrences": pyq_occurrences.get(slug, []),
                "resolvedLabels": resolved_pyq.get(slug, []),
            },
            "editorial": {
                "status": meta.get("status", ""),
                "reviewStatus": meta.get("review_status", "unreviewed"),
                "referenceReady": bool(body.strip() and len(coords) == 2),
                "practiceReady": not issues,
                "issues": issues,
            },
        }
        sites.append(site)

    sites.sort(key=lambda site: (site["chapter"]["id"], site["name"].casefold()))
    issue_counts = Counter(issue for site in sites for issue in site["editorial"]["issues"])
    orphan_gazetteer = sorted(set(gazetteer) - {path.stem for path, _, _ in records})
    resolved_pyq_labels = [
        (item["label"], item["count"], slug)
        for slug, labels in resolved_pyq.items()
        for item in labels
    ]

    stats = {
        "sites": len(sites),
        "referenceReady": sum(site["editorial"]["referenceReady"] for site in sites),
        "practiceReady": sum(site["editorial"]["practiceReady"] for site in sites),
        "scorableCoordinates": sum(site["location"]["scorable"] for site in sites),
        "unverifiedCoordinates": issue_counts["coordinate_unverified"],
        "missingRegions": issue_counts["region_missing"],
        "unknownCoordinateConfidenceValues": issue_counts["coordinate_confidence_unknown_value"],
        "coordinateCollisionGroups": len(collisions),
        "locationTypeReviews": issue_counts["location_type_review_required"],
        "missingSourceMetadata": issue_counts["source_metadata_missing"],
        "missingWrittenSourceLines": issue_counts["written_source_line_missing"],
        "contentReviewsRequired": issue_counts["content_review_required"],
        "missingModelAnswers30": issue_counts["model_answer_30_missing"],
        "legacyNameMismatches": len(name_mismatches),
        "orphanGazetteerEntries": len(orphan_gazetteer),
        "unmatchedPyqLabels": len(unmatched_pyq),
        "unmatchedPyqOccurrences": sum(unmatched_pyq.values()),
        "resolvedPyqAliasLabels": len(resolved_pyq_labels),
        "resolvedPyqAliasOccurrences": sum(item[1] for item in resolved_pyq_labels),
    }
    payload = {
        "schemaVersion": 1,
        "sourceOfTruth": "sites/**/*.md",
        "stats": stats,
        "sites": sites,
    }
    audit = {
        "stats": stats,
        "issueCounts": dict(sorted(issue_counts.items())),
        "coordinateCollisions": collisions,
        "legacyNameMismatches": name_mismatches,
        "orphanGazetteer": orphan_gazetteer,
        "unmatchedPyq": unmatched_pyq,
        "resolvedPyqAliases": sorted(
            resolved_pyq_labels, key=lambda item: (-item[1], item[0].casefold())
        ),
        "potentialNonPoint": [
            (site["slug"], site["name"])
            for site in sites
            if "location_type_review_required" in site["editorial"]["issues"]
        ],
        "missingRegions": [
            (site["slug"], site["name"])
            for site in sites
            if "region_missing" in site["editorial"]["issues"]
        ],
        "missingSources": [
            (site["slug"], site["name"])
            for site in sites
            if "source_metadata_missing" in site["editorial"]["issues"]
        ],
    }
    return payload, audit


def render_report(audit: dict) -> str:
    stats = audit["stats"]
    lines = [
        "# Web map readiness",
        "",
        "Generated from the canonical Markdown records by `pipeline/export_web.py`.",
        "A reference-ready record has text and a coordinate. A practice-ready record",
        "also requires reviewed content, a verified coordinate, source metadata and a",
        "concise model answer. No readiness flag is inferred from `status: sourced`.",
        "",
        "A coordinate counts as verified when `coords_provisional` is `false`, meaning",
        "someone checked it against a gazetteer. `coords_confidence` is not used as a",
        "quality signal: it records how cleanly the dot was read off the scanned sheet,",
        "not how close the reading is. Burzahom is labelled `high` and lies 139 km from",
        "Burzahom. Measured against the unambiguous Wikidata entries inside the sheet's",
        "frame, verified coordinates run to a median of 0.0 km and a p90 of 2.2 km",
        "(n=123), which is what the 25 km accepted radius is built on; unverified ones",
        "are exported with `scorable: false` and no radius at all.",
        "",
        "## Summary",
        "",
        f"- Sites: **{stats['sites']}**",
        f"- Reference ready: **{stats['referenceReady']}**",
        f"- Practice ready: **{stats['practiceReady']}**",
        f"- Scorable coordinates: **{stats['scorableCoordinates']}**",
        f"- Unverified coordinates: **{stats['unverifiedCoordinates']}**",
        f"- Missing state/region: **{stats['missingRegions']}**",
        f"- Unknown coordinate-confidence values: "
        f"**{stats['unknownCoordinateConfidenceValues']}**",
        f"- Shared-coordinate groups needing review: **{stats['coordinateCollisionGroups']}**",
        f"- Location types needing review: **{stats['locationTypeReviews']}**",
        f"- Missing source metadata: **{stats['missingSourceMetadata']}**",
        f"- Missing written source line: **{stats['missingWrittenSourceLines']}**",
        f"- Content reviews required: **{stats['contentReviewsRequired']}**",
        f"- Missing 30-word model answers: **{stats['missingModelAnswers30']}**",
        f"- Legacy `data/sites.json` name mismatches: **{stats['legacyNameMismatches']}**",
        f"- Orphan gazetteer entries: **{stats['orphanGazetteerEntries']}**",
        f"- Unmatched PYQ labels: **{stats['unmatchedPyqLabels']}** "
        f"({stats['unmatchedPyqOccurrences']} occurrences)",
        f"- PYQ labels resolved through unique answer aliases: "
        f"**{stats['resolvedPyqAliasLabels']}** "
        f"({stats['resolvedPyqAliasOccurrences']} occurrences)",
        "",
        "## Exact coordinate collisions",
        "",
        "These are review items, not automatic duplicates. Some may legitimately refer",
        "to the same historical place.",
        "",
        "| Coordinates | Records |",
        "|---|---|",
    ]
    for coords, slugs in sorted(audit["coordinateCollisions"].items()):
        lines.append(f"| `{coords[0]}, {coords[1]}` | {', '.join(f'`{slug}`' for slug in slugs)} |")

    lines += ["", "## Canonical-name mismatches", "", "| Slug | Legacy index | Canonical Markdown |", "|---|---|---|"]
    for slug, legacy, canonical in audit["legacyNameMismatches"]:
        lines.append(f"| `{slug}` | {legacy} | {canonical} |")

    lines += ["", "## Missing state or region", ""]
    lines += [f"- `{slug}` — {name}" for slug, name in audit["missingRegions"]] or ["- None"]

    lines += [
        "",
        "## No source metadata",
        "",
        "No work in `corpus/` was confirmed to discuss these. `pipeline/cite.py",
        "search \"<name>\"` finds passages; attach a key only after reading one.",
        "A high score is not a confirmation — the top hit for Ajmer (Hakra Basin)",
        "scored 40 and was about the conquest of Ajmer in 1195.",
        "",
    ]
    lines += [f"- `{slug}` — {name}" for slug, name in audit["missingSources"]] or ["- None"]

    lines += ["", "## Location type review", ""]
    lines += [f"- `{slug}` — {name}" for slug, name in audit["potentialNonPoint"]] or ["- None"]

    lines += ["", "## Orphan gazetteer entries", ""]
    lines += [f"- `{slug}`" for slug in audit["orphanGazetteer"]] or ["- None"]

    lines += [
        "",
        "## PYQ labels resolved through unique answer aliases",
        "",
        "Search-only and ambiguous aliases are deliberately excluded.",
        "",
        "| PYQ label | Occurrences | Canonical record |",
        "|---|---:|---|",
    ]
    lines += [
        f"| {label} | {count} | `{slug}` |"
        for label, count, slug in audit["resolvedPyqAliases"]
    ] or ["| None | 0 | - |"]

    lines += ["", "## Highest-frequency unmatched PYQ labels", ""]
    unmatched = sorted(audit["unmatchedPyq"].items(), key=lambda item: (-item[1], item[0].casefold()))
    lines += [f"- {name}: {count}" for name, count in unmatched[:40]] or ["- None"]
    return "\n".join(lines) + "\n"


def serialise(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    payload, audit = build_export()
    json_text = serialise(payload)
    report_text = render_report(audit)
    stats = payload["stats"]
    print(
        f"sites={stats['sites']} reference_ready={stats['referenceReady']} "
        f"practice_ready={stats['practiceReady']} scorable={stats['scorableCoordinates']} "
        f"unverified={stats['unverifiedCoordinates']} "
        f"missing_model_answers={stats['missingModelAnswers30']}"
    )

    if "--check" in sys.argv:
        stale = []
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != json_text:
            stale.append(str(OUTPUT.relative_to(ROOT)))
        if not REPORT.exists() or REPORT.read_text(encoding="utf-8") != report_text:
            stale.append(str(REPORT.relative_to(ROOT)))
        if stale:
            print("stale generated files: " + ", ".join(stale), file=sys.stderr)
            return 1
        print("web export is current")
        return 0

    if "--write" in sys.argv or "--apply" in sys.argv:
        DATA.mkdir(exist_ok=True)
        REPORTS.mkdir(exist_ok=True)
        # newline="\n" explicitly: the default translates to CRLF on Windows, so
        # a generated file rewritten on Linux would show every line as changed.
        OUTPUT.write_text(json_text, encoding="utf-8", newline="\n")
        REPORT.write_text(report_text, encoding="utf-8", newline="\n")
        print(f"wrote {OUTPUT.relative_to(ROOT)}")
        print(f"wrote {REPORT.relative_to(ROOT)}")
    else:
        print("preview only — rerun with --write to create the web export")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
