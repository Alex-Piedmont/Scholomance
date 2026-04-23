"""Migration QA sample generator.

Emits a deterministic stratified sample of 15 technologies per university
covering every university present in the `technologies` table (union of
registry codes and DB-distinct codes).

Output artifact shape (docs/qa/samples-<ISO-date>.json and samples-latest.json):

    {
      "generated_at": "2026-04-23T12:34:56",
      "seed_scheme": "per-university stable seed from code",
      "universities": [
        {
          "code": "jhu",
          "name": "Johns Hopkins University",
          "total_records": 187,
          "null_raw_data": 2,
          "full_coverage": false,
          "sampled": [
            {
              "uuid": "be9a2b26-...",
              "tech_id": "C18050",
              "first_seen": "2026-03-23T00:00:00+00:00",
              "stratum": "oldest",
              "raw_data_keys": ["advantages", "background", ...]
            },
            ...
          ]
        },
        ...
      ]
    }

Strata: "oldest", "newest", "stage:<value>", "random".

Read-only: this module NEVER writes to `technologies`. It only reads.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import Technology, db
from ..scrapers.registry import UNIVERSITY_CONFIGS


SAMPLE_SIZE = 15


@dataclass
class SampledRecord:
    uuid: str
    tech_id: str
    first_seen: Optional[str]
    stratum: str
    raw_data_keys: list[str]

    def to_dict(self) -> dict:
        return {
            "uuid": self.uuid,
            "tech_id": self.tech_id,
            "first_seen": self.first_seen,
            "stratum": self.stratum,
            "raw_data_keys": self.raw_data_keys,
        }


@dataclass
class UniversitySample:
    code: str
    name: str
    total_records: int
    null_raw_data: int
    sampled: list[SampledRecord] = field(default_factory=list)

    @property
    def full_coverage(self) -> bool:
        # All populated records (total_records minus null_raw_data) are in the sample.
        return len(self.sampled) >= (self.total_records - self.null_raw_data) > 0

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "total_records": self.total_records,
            "null_raw_data": self.null_raw_data,
            "full_coverage": self.full_coverage,
            "sampled": [s.to_dict() for s in self.sampled],
        }


def _universe_of_universities(session: Session) -> dict[str, str]:
    """Return {code: display_name} for every university we care about.

    Union of registry codes (with enabled-flag ignored so recently-disabled
    scrapers still audit) and DB-distinct universities.
    """
    registry = {cfg.code: cfg.name for cfg in UNIVERSITY_CONFIGS}
    db_codes = {
        code
        for (code,) in session.query(Technology.university).distinct().all()
        if code
    }
    all_codes = set(registry.keys()) | db_codes
    return {code: registry.get(code, code) for code in sorted(all_codes)}


def _stratified_sample(
    session: Session, code: str, total: int
) -> list[SampledRecord]:
    """Pick up to SAMPLE_SIZE records for this university, stratified.

    Strata (in order of preference):
      1. Oldest by first_seen (1)
      2. Newest by first_seen (1)
      3. One record per distinct raw_data->>'development_stage' value (capped)
      4. Random fill using a per-university seed (deterministic across runs)
    """
    populated_q = (
        session.query(Technology)
        .filter(Technology.university == code)
        .filter(Technology.raw_data.isnot(None))
    )
    populated_count = populated_q.count()
    if populated_count == 0:
        return []

    cap = min(SAMPLE_SIZE, populated_count)
    picked_uuids: set[str] = set()
    result: list[SampledRecord] = []

    def _record(tech: Technology, stratum: str) -> SampledRecord:
        raw_keys = sorted(list(tech.raw_data.keys())) if isinstance(tech.raw_data, dict) else []
        return SampledRecord(
            uuid=str(tech.uuid),
            tech_id=tech.tech_id,
            first_seen=tech.first_seen.isoformat() if tech.first_seen else None,
            stratum=stratum,
            raw_data_keys=raw_keys,
        )

    oldest = populated_q.order_by(Technology.first_seen.asc().nullslast()).limit(1).first()
    if oldest and str(oldest.uuid) not in picked_uuids and len(result) < cap:
        result.append(_record(oldest, "oldest"))
        picked_uuids.add(str(oldest.uuid))

    newest = populated_q.order_by(Technology.first_seen.desc().nullslast()).limit(1).first()
    if newest and str(newest.uuid) not in picked_uuids and len(result) < cap:
        result.append(_record(newest, "newest"))
        picked_uuids.add(str(newest.uuid))

    if len(result) < cap:
        stage_rows = (
            session.query(
                Technology.raw_data["development_stage"].astext.label("stage"),
                func.min(Technology.id).label("sample_id"),
            )
            .filter(Technology.university == code)
            .filter(Technology.raw_data.isnot(None))
            .filter(Technology.raw_data["development_stage"].astext.isnot(None))
            .group_by("stage")
            .all()
        )
        for stage_value, sample_id in stage_rows:
            if len(result) >= cap:
                break
            if not stage_value:
                continue
            tech = session.query(Technology).get(sample_id)
            if tech and str(tech.uuid) not in picked_uuids:
                result.append(_record(tech, f"stage:{stage_value}"))
                picked_uuids.add(str(tech.uuid))

    if len(result) < cap:
        remaining_ids = [
            tid
            for (tid,) in session.query(Technology.id)
            .filter(Technology.university == code)
            .filter(Technology.raw_data.isnot(None))
            .all()
            if tid
        ]
        already_ids = {
            tid
            for tid in session.query(Technology.id)
            .filter(Technology.uuid.in_([r.uuid for r in result]))
            .all()
            for tid in tid
        }
        eligible = [tid for tid in remaining_ids if tid not in already_ids]
        rng = random.Random(f"migration-qa::{code}")
        rng.shuffle(eligible)
        for tid in eligible:
            if len(result) >= cap:
                break
            tech = session.query(Technology).get(tid)
            if tech and str(tech.uuid) not in picked_uuids:
                result.append(_record(tech, "random"))
                picked_uuids.add(str(tech.uuid))

    return result


def build_sample(session: Session) -> list[UniversitySample]:
    """Build stratified samples for every university in the universe."""
    universe = _universe_of_universities(session)
    samples: list[UniversitySample] = []
    for code, name in universe.items():
        total = (
            session.query(Technology).filter(Technology.university == code).count()
        )
        null_count = (
            session.query(Technology)
            .filter(Technology.university == code)
            .filter(Technology.raw_data.is_(None))
            .count()
        )
        sampled = _stratified_sample(session, code, total)
        samples.append(
            UniversitySample(
                code=code,
                name=name,
                total_records=total,
                null_raw_data=null_count,
                sampled=sampled,
            )
        )
    return samples


def write_samples(samples: list[UniversitySample], output_dir: Path) -> tuple[Path, Path]:
    """Write the dated JSON and update samples-latest.json. Returns both paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    payload = {
        "generated_at": now.isoformat(),
        "seed_scheme": "per-university stable seed from code",
        "sample_size": SAMPLE_SIZE,
        "universities": [s.to_dict() for s in samples],
    }
    iso_date = now.strftime("%Y-%m-%d")
    dated = output_dir / f"samples-{iso_date}.json"
    latest = output_dir / "samples-latest.json"
    body = json.dumps(payload, indent=2)
    dated.write_text(body)
    latest.write_text(body)
    return dated, latest


def run_sampler(output_dir: Optional[Path] = None) -> list[UniversitySample]:
    """Run the sampler end-to-end. Returns the in-memory samples.

    Side effect: writes two JSON files (dated + latest) into output_dir.
    Default output_dir is <repo_root>/docs/qa.
    """
    if output_dir is None:
        output_dir = Path(__file__).resolve().parents[2] / "docs" / "qa"
    with db.get_session() as session:
        samples = build_sample(session)
    write_samples(samples, output_dir)
    return samples
