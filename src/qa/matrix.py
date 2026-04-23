"""Migration QA gap matrix generator.

Merges three input JSON artifacts into a single per-university × per-section
pass/fail matrix, plus a drift-friendly markdown table.

Inputs:
  docs/qa/samples-latest.json            (AU-1)
  docs/qa/db-coverage-latest.json        (AU-2)
  docs/qa/playwright-drawer-latest.worker-*.json  (AU-4 workers)
  docs/qa/playwright-detail-latest.worker-*.json  (AU-5 workers)

Outputs:
  docs/qa/migration-matrix-<ISO-date>.json
  docs/qa/migration-matrix-<ISO-date>.md
  docs/qa/migration-matrix-latest.{json,md}  (mirrors the dated file)

Per-cell statuses: pass / fail / no-data / crash / missing-test. Aggregated
across sampled records per (university, section, surface=drawer|detail).

Read-only: never writes to the database.
"""

from __future__ import annotations

import glob
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Literal, Optional

from .section_catalog import CATALOG


QA_DIR = Path(__file__).resolve().parents[2] / "docs" / "qa"

Surface = Literal["drawer", "detail"]


@dataclass
class MergedRecord:
    university: str
    uuid: str
    tech_id: str
    # {section_id: "pass" | "missing" | ...}
    sections: dict[str, str]
    status: str  # record-level: pass | fail | crash | unreachable


def _load_workers(pattern: str) -> list[dict]:
    paths = sorted(glob.glob(str(QA_DIR / pattern)))
    records: list[dict] = []
    for p in paths:
        try:
            payload = json.loads(Path(p).read_text())
        except json.JSONDecodeError:
            continue
        records.extend(payload.get("records", []))
    return records


def _merge_surface(surface: Surface) -> list[MergedRecord]:
    pattern = f"playwright-{surface}-latest.worker-*.json"
    raw_records = _load_workers(pattern)
    merged: list[MergedRecord] = []
    for r in raw_records:
        section_map = {s["sectionId"]: s["status"] for s in r.get("sections", [])}
        merged.append(
            MergedRecord(
                university=r["university"],
                uuid=r["uuid"],
                tech_id=r["tech_id"],
                sections=section_map,
                status=r.get("status", "unknown"),
            )
        )
    return merged


def _cell_status(
    coverage_status: Optional[str], surface_status: Optional[str]
) -> str:
    """Derive the matrix cell status for a single (section, record, surface).

    coverage_status: has_data | empty | malformed | None
    surface_status: pass | missing | None
    """
    if coverage_status in (None, "empty", "malformed"):
        return "no-data"
    # has_data
    if surface_status is None:
        return "missing-test"
    if surface_status == "pass":
        return "pass"
    return "fail"


def build_matrix() -> dict:
    coverage_path = QA_DIR / "db-coverage-latest.json"
    samples_path = QA_DIR / "samples-latest.json"
    coverage = json.loads(coverage_path.read_text())
    samples = json.loads(samples_path.read_text())

    drawer_records = _merge_surface("drawer")
    detail_records = _merge_surface("detail")

    drawer_by_uuid = {r.uuid: r for r in drawer_records}
    detail_by_uuid = {r.uuid: r for r in detail_records}

    sections = [s.id for s in CATALOG]
    section_labels = {s.id: s.label for s in CATALOG}

    per_uni: dict[str, dict] = {}
    for uni in samples["universities"]:
        code = uni["code"]
        name = uni["name"]
        uni_cov = coverage["universities"].get(code, {}).get("per_record", {})
        # Stats per (section, surface)
        drawer_stats: dict[str, Counter] = {sid: Counter() for sid in sections}
        detail_stats: dict[str, Counter] = {sid: Counter() for sid in sections}
        record_outcomes: dict[str, dict] = {}

        for sample in uni["sampled"]:
            uuid = sample["uuid"]
            cov_row = uni_cov.get(uuid, {})
            drawer_r = drawer_by_uuid.get(uuid)
            detail_r = detail_by_uuid.get(uuid)
            per_record_cells = {}
            for sid in sections:
                cov_status = cov_row.get(sid)
                drawer_cell = _cell_status(
                    cov_status,
                    (drawer_r.sections.get(sid) if drawer_r else None),
                )
                detail_cell = _cell_status(
                    cov_status,
                    (detail_r.sections.get(sid) if detail_r else None),
                )
                drawer_stats[sid][drawer_cell] += 1
                detail_stats[sid][detail_cell] += 1
                per_record_cells[sid] = {"drawer": drawer_cell, "detail": detail_cell}
            record_outcomes[uuid] = {
                "tech_id": sample.get("tech_id"),
                "drawer_status": drawer_r.status if drawer_r else "missing-test",
                "detail_status": detail_r.status if detail_r else "missing-test",
                "cells": per_record_cells,
            }

        per_uni[code] = {
            "name": name,
            "sampled": len(uni["sampled"]),
            "drawer_stats": {sid: dict(c) for sid, c in drawer_stats.items()},
            "detail_stats": {sid: dict(c) for sid, c in detail_stats.items()},
            "records": record_outcomes,
        }

    now = datetime.now(timezone.utc)
    return {
        "generated_at": now.isoformat(),
        "samples_generated_at": samples.get("generated_at"),
        "coverage_generated_at": coverage.get("generated_at"),
        "sections": sections,
        "section_labels": section_labels,
        "universities": per_uni,
    }


def _pass_rate(stats: dict, sid: str) -> tuple[int, int, int, int, int]:
    """(pass, fail, no-data, crash, missing-test)."""
    counter = stats.get(sid, {})
    return (
        counter.get("pass", 0),
        counter.get("fail", 0),
        counter.get("no-data", 0),
        counter.get("crash", 0),
        counter.get("missing-test", 0),
    )


def render_markdown(matrix: dict) -> str:
    out: list[str] = []
    out.append("# Migration-QA Gap Matrix")
    out.append("")
    out.append(
        f"Generated: `{matrix['generated_at']}` · "
        f"Samples: `{matrix['samples_generated_at']}` · "
        f"Coverage: `{matrix['coverage_generated_at']}`"
    )
    out.append("")
    out.append(
        "Per-cell format: `pass / fail / no-data`. `crash` and `missing-test` "
        "are folded into `fail` for the summary totals below and called out "
        "explicitly in the per-university detail."
    )
    out.append("")

    # Overall roll-up
    total_drawer = Counter()
    total_detail = Counter()
    for uni in matrix["universities"].values():
        for sid in matrix["sections"]:
            for k, v in uni["drawer_stats"].get(sid, {}).items():
                total_drawer[k] += v
            for k, v in uni["detail_stats"].get(sid, {}).items():
                total_detail[k] += v

    def _rate(counter: Counter) -> str:
        relevant = counter["pass"] + counter["fail"] + counter["crash"] + counter["missing-test"]
        if not relevant:
            return "n/a"
        return f"{counter['pass']}/{relevant} ({100 * counter['pass'] / relevant:.1f}%)"

    out.append("## Summary")
    out.append("")
    out.append("| Surface | pass | fail | no-data | crash | missing-test | pass rate |")
    out.append("|---|---:|---:|---:|---:|---:|---:|")
    out.append(
        f"| Drawer | {total_drawer['pass']} | {total_drawer['fail']} | "
        f"{total_drawer['no-data']} | {total_drawer['crash']} | "
        f"{total_drawer['missing-test']} | {_rate(total_drawer)} |"
    )
    out.append(
        f"| Detail | {total_detail['pass']} | {total_detail['fail']} | "
        f"{total_detail['no-data']} | {total_detail['crash']} | "
        f"{total_detail['missing-test']} | {_rate(total_detail)} |"
    )
    out.append("")

    # Per-section roll-up
    out.append("## By section (aggregated across universities)")
    out.append("")
    out.append("| Section | Drawer pass/total | Detail pass/total |")
    out.append("|---|---:|---:|")
    for sid in matrix["sections"]:
        label = matrix["section_labels"][sid]
        draw_c = Counter()
        det_c = Counter()
        for uni in matrix["universities"].values():
            for k, v in uni["drawer_stats"].get(sid, {}).items():
                draw_c[k] += v
            for k, v in uni["detail_stats"].get(sid, {}).items():
                det_c[k] += v
        out.append(f"| {label} | {_rate(draw_c)} | {_rate(det_c)} |")
    out.append("")

    # Per-university detail
    out.append("## Per-university detail")
    out.append("")
    for code, uni in matrix["universities"].items():
        out.append(f"### {uni['name']} (`{code}`) — {uni['sampled']} sampled")
        out.append("")
        out.append("| Section | Drawer (pass/fail/no-data) | Detail (pass/fail/no-data) |")
        out.append("|---|---:|---:|")
        for sid in matrix["sections"]:
            label = matrix["section_labels"][sid]
            p, f, n, c, m = _pass_rate(uni["drawer_stats"], sid)
            dp, df, dn, dc, dm = _pass_rate(uni["detail_stats"], sid)
            drawer_cell = f"{p}/{f}/{n}"
            if c or m:
                drawer_cell += f" ({c} crash, {m} missing-test)"
            detail_cell = f"{dp}/{df}/{dn}"
            if dc or dm:
                detail_cell += f" ({dc} crash, {dm} missing-test)"
            out.append(f"| {label} | {drawer_cell} | {detail_cell} |")
        out.append("")
    return "\n".join(out)


def write_matrix(matrix: dict, output_dir: Optional[Path] = None) -> tuple[Path, Path]:
    if output_dir is None:
        output_dir = QA_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    iso_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    json_path = output_dir / f"migration-matrix-{iso_date}.json"
    md_path = output_dir / f"migration-matrix-{iso_date}.md"
    latest_json = output_dir / "migration-matrix-latest.json"
    latest_md = output_dir / "migration-matrix-latest.md"
    body = json.dumps(matrix, indent=2)
    md = render_markdown(matrix)
    json_path.write_text(body)
    latest_json.write_text(body)
    md_path.write_text(md)
    latest_md.write_text(md)
    return md_path, json_path


def run_matrix(output_dir: Optional[Path] = None) -> dict:
    matrix = build_matrix()
    write_matrix(matrix, output_dir)
    return matrix
