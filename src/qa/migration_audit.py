"""Migration QA DB-side section coverage auditor.

Reads `docs/qa/samples-latest.json` and evaluates each record against the
UI section catalog to produce a three-state coverage report per record:

    has_data  - at least one source matches an accepted shape for the section
    empty     - every source is None, empty, or absent
    malformed - at least one source has data, but none match an accepted shape

Emits:
    docs/qa/db-coverage-<ISO-date>.json
    docs/qa/db-coverage-latest.json
    docs/qa/db-coverage-<ISO-date>.md

Read-only: no writes to `technologies`. Catalog drives the audit, not the
raw_data keys directly.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from ..database import Technology, db
from .section_catalog import CATALOG, Section, ShapeToken


Status = str  # "has_data" | "empty" | "malformed"


HTML_TAG_RE = re.compile(r"<[a-zA-Z][^>]*>")


def classify_shape(value: Any) -> set[ShapeToken]:
    """Return the set of shape tokens a value matches.

    A value may match multiple tokens (e.g. a string with '\\n' and ',' matches
    both newline_string and comma_string). An empty value matches nothing.
    """
    tokens: set[ShapeToken] = set()
    if value is None:
        return tokens
    if isinstance(value, list):
        if not value:
            return tokens
        if all(isinstance(x, str) and x.strip() for x in value):
            tokens.add("array_of_strings")
        if all(isinstance(x, dict) for x in value):
            tokens.add("array_of_objects")
        return tokens
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return tokens
        if HTML_TAG_RE.search(stripped):
            tokens.add("html_string")
        if "\n" in stripped:
            tokens.add("newline_string")
        if "," in stripped:
            tokens.add("comma_string")
        tokens.add("plain_string")
        return tokens
    if isinstance(value, dict):
        if value:
            tokens.add("object")
        return tokens
    return tokens


def _get_value(tech: Technology, source_type: str, key: str) -> Any:
    if source_type == "raw_data":
        rd = tech.raw_data or {}
        if not isinstance(rd, dict):
            return None
        return rd.get(key)
    # column
    return getattr(tech, key, None)


def evaluate_section(tech: Technology, section: Section) -> Status:
    """Evaluate a single section for a single tech record."""
    any_source_populated = False
    for source in section.sources:
        value = _get_value(tech, source.type, source.key)
        shapes = classify_shape(value)
        if shapes:
            any_source_populated = True
            if set(source.accepted_shapes) & shapes:
                return "has_data"
    return "malformed" if any_source_populated else "empty"


@dataclass
class UniCoverage:
    code: str
    name: str
    sampled_count: int
    # {section_id: {"has_data": n, "empty": n, "malformed": n}}
    section_counts: dict[str, Counter]
    # {uuid: {section_id: status}}
    per_record: dict[str, dict[str, Status]]


def audit_from_samples(session: Session, samples_payload: dict) -> list[UniCoverage]:
    coverages: list[UniCoverage] = []
    for uni in samples_payload["universities"]:
        code = uni["code"]
        name = uni["name"]
        section_counts: dict[str, Counter] = {s.id: Counter() for s in CATALOG}
        per_record: dict[str, dict[str, Status]] = {}
        uuids = [s["uuid"] for s in uni["sampled"]]
        if not uuids:
            coverages.append(UniCoverage(code, name, 0, section_counts, per_record))
            continue
        techs = (
            session.query(Technology)
            .filter(Technology.uuid.in_(uuids))
            .all()
        )
        tech_by_uuid = {str(t.uuid): t for t in techs}
        for uuid in uuids:
            tech = tech_by_uuid.get(uuid)
            if not tech:
                continue
            row: dict[str, Status] = {}
            for section in CATALOG:
                status = evaluate_section(tech, section)
                row[section.id] = status
                section_counts[section.id][status] += 1
            per_record[uuid] = row
        coverages.append(
            UniCoverage(code, name, len(uuids), section_counts, per_record)
        )
    return coverages


def coverages_to_json(
    coverages: list[UniCoverage], samples_payload: dict
) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "generated_at": now.isoformat(),
        "samples_generated_at": samples_payload.get("generated_at"),
        "sections": [s.id for s in CATALOG],
        "universities": {
            c.code: {
                "name": c.name,
                "sampled": c.sampled_count,
                "section_counts": {
                    sid: dict(counter) for sid, counter in c.section_counts.items()
                },
                "per_record": c.per_record,
            }
            for c in coverages
        },
    }


def _render_markdown(coverages: list[UniCoverage]) -> str:
    out: list[str] = []
    out.append("# Migration-QA DB Coverage Report\n")
    out.append(
        "Per-university section coverage across sampled records. "
        "`has_data` means at least one source matches an accepted shape "
        "per `section_catalog.py`. `malformed` means data is present but no "
        "shape matched — this is the AU-6 parser-fix candidate signal.\n"
    )
    section_ids = [s.id for s in CATALOG]
    labels = {s.id: s.label for s in CATALOG}

    # Per-university detail tables
    for c in coverages:
        out.append(f"## {c.name} (`{c.code}`) — {c.sampled_count} sampled\n")
        if not c.sampled_count:
            out.append("_No sampled records._\n")
            continue
        out.append("| Section | has_data | empty | malformed |")
        out.append("|---|---:|---:|---:|")
        for sid in section_ids:
            cnt = c.section_counts[sid]
            h = cnt.get("has_data", 0)
            e = cnt.get("empty", 0)
            m = cnt.get("malformed", 0)
            # Flag malformed cells for visibility
            m_cell = f"**{m}**" if m else str(m)
            out.append(f"| {labels[sid]} | {h} | {e} | {m_cell} |")
        out.append("")

    # Top-level summary: any section with malformed records
    out.append("## Summary — parser-fix candidates\n")
    flagged: list[tuple[str, str, int]] = []
    for c in coverages:
        for sid in section_ids:
            m = c.section_counts[sid].get("malformed", 0)
            if m:
                flagged.append((c.code, sid, m))
    if flagged:
        out.append("| University | Section | Malformed count |")
        out.append("|---|---|---:|")
        for code, sid, m in sorted(flagged, key=lambda x: (-x[2], x[0], x[1])):
            out.append(f"| `{code}` | {labels[sid]} | {m} |")
    else:
        out.append("_No malformed sources detected. Every populated source matches an accepted shape._")
    out.append("")
    return "\n".join(out)


def run_audit(
    samples_path: Optional[Path] = None, output_dir: Optional[Path] = None
) -> list[UniCoverage]:
    if samples_path is None:
        samples_path = (
            Path(__file__).resolve().parents[2] / "docs" / "qa" / "samples-latest.json"
        )
    if output_dir is None:
        output_dir = samples_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = json.loads(samples_path.read_text())
    with db.get_session() as session:
        coverages = audit_from_samples(session, payload)

    json_doc = coverages_to_json(coverages, payload)
    md_doc = _render_markdown(coverages)
    iso_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (output_dir / f"db-coverage-{iso_date}.json").write_text(
        json.dumps(json_doc, indent=2)
    )
    (output_dir / "db-coverage-latest.json").write_text(
        json.dumps(json_doc, indent=2)
    )
    (output_dir / f"db-coverage-{iso_date}.md").write_text(md_doc)
    return coverages
