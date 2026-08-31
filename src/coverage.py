"""Coverage items and pipeline decisions.

These records are produced by the weekly commercialization packet. They are
not TTO listings: a coverage row may exist with no matching ``technologies``
row, and a listing must never be treated as a coverage/pipeline object.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .database import CoverageItem, PipelineDecision, Technology

SOURCE_CLASSES = ("newspaper_tv", "specialist")
MATCH_STATUSES = ("matched", "unmatched", "candidate")
DECISION_STATUSES = ("greenlit", "hold", "proceed", "archive", "dropped")


def monday_of(value: date) -> date:
    """Return the Monday of the ISO week containing ``value``."""
    return value - timedelta(days=value.weekday())


def blank_to_none(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def coverage_upsert_identity(
    packet_week: date,
    headline: str,
    university: Optional[str],
) -> tuple[date, str, Optional[str]]:
    """Natural key for a weekly packet row: Monday + headline + university."""
    return (monday_of(packet_week), headline.strip(), blank_to_none(university))


def identities_equal(
    left: tuple[date, str, Optional[str]],
    right: tuple[date, str, Optional[str]],
) -> bool:
    return left == right


def find_coverage_for_upsert(
    session: Session,
    packet_week: date,
    headline: str,
    university: Optional[str],
) -> Optional[CoverageItem]:
    """Look up an existing row by the weekly upsert key."""
    week, title, uni = coverage_upsert_identity(packet_week, headline, university)
    query = session.query(CoverageItem).filter(
        CoverageItem.packet_week == week,
        CoverageItem.headline == title,
    )
    if uni is None:
        query = query.filter(CoverageItem.university.is_(None))
    else:
        query = query.filter(CoverageItem.university == uni)
    return query.first()


def resolve_technology_match(
    session: Session,
    technology_uuid: Optional[UUID],
    university: Optional[str],
    headline: str,
    requested_status: Optional[str] = None,
) -> tuple[Optional[UUID], str]:
    """Best-effort TTO match. Never requires a listing to exist.

    - Explicit uuid that exists on ``technologies`` -> matched.
    - Explicit uuid that does not exist -> keep uuid, candidate.
    - No uuid: unique case-insensitive title match (optionally scoped by
      university) -> candidate.
    - Otherwise unmatched with uuid None.

    ``requested_status`` overrides the computed status when it is valid.
    """
    uuid_out: Optional[UUID] = None
    status = "unmatched"

    if technology_uuid is not None:
        exists = (
            session.query(Technology.uuid)
            .filter(Technology.uuid == technology_uuid)
            .first()
        )
        uuid_out = technology_uuid
        status = "matched" if exists else "candidate"
    else:
        uni = blank_to_none(university)
        query = session.query(Technology).filter(Technology.title.ilike(headline.strip()))
        if uni is not None:
            query = query.filter(Technology.university == uni)
        hits = query.limit(2).all()
        if len(hits) == 1:
            uuid_out = hits[0].uuid
            status = "candidate"

    if requested_status in MATCH_STATUSES:
        status = requested_status
        if status == "unmatched":
            # Honour an explicit unmatched: drop a speculative auto-match, but
            # keep a caller-supplied uuid (they may match later).
            if technology_uuid is None:
                uuid_out = None

    return uuid_out, status


def apply_coverage_fields(
    item: CoverageItem,
    fields: dict[str, Any],
    *,
    touch_updated: bool = True,
) -> CoverageItem:
    """Copy known coverage fields onto ``item``. Ignores missing keys."""
    for key in (
        "technology_uuid",
        "university",
        "headline",
        "summary",
        "capability",
        "sources",
        "source_class",
        "independence_note",
        "coverage_date",
        "packet_week",
        "match_status",
    ):
        if key in fields:
            setattr(item, key, fields[key])
    if touch_updated:
        item.updated_at = datetime.now(timezone.utc)
    return item


def upsert_coverage_item(
    session: Session,
    data: dict[str, Any],
    *,
    auto_match: bool = True,
) -> tuple[CoverageItem, bool]:
    """Insert or update by (packet_week, headline, university).

    ``technology_uuid`` is optional. Saving never requires a TTO listing.
    Returns ``(item, created)``.
    """
    headline = (data.get("headline") or "").strip()
    if not headline:
        raise ValueError("headline is required")

    source_class = data.get("source_class")
    if source_class not in SOURCE_CLASSES:
        raise ValueError(f"source_class must be one of {SOURCE_CLASSES}")

    university = blank_to_none(data.get("university"))
    packet_week_raw = data.get("packet_week") or date.today()
    if isinstance(packet_week_raw, datetime):
        packet_week_raw = packet_week_raw.date()
    packet_week = monday_of(packet_week_raw)

    coverage_date = data.get("coverage_date")
    if isinstance(coverage_date, datetime):
        coverage_date = coverage_date.date()

    tech_uuid = data.get("technology_uuid")
    requested_status = data.get("match_status")

    if auto_match:
        tech_uuid, match_status = resolve_technology_match(
            session,
            tech_uuid,
            university,
            headline,
            requested_status=requested_status,
        )
    else:
        match_status = requested_status if requested_status in MATCH_STATUSES else "unmatched"

    sources = data.get("sources")
    if sources is None:
        sources = []
    if not isinstance(sources, list):
        raise ValueError("sources must be a JSON array")

    fields = {
        "technology_uuid": tech_uuid,
        "university": university,
        "headline": headline,
        "summary": data.get("summary"),
        "capability": data.get("capability"),
        "sources": sources,
        "source_class": source_class,
        "independence_note": data.get("independence_note"),
        "coverage_date": coverage_date,
        "packet_week": packet_week,
        "match_status": match_status,
    }

    existing = find_coverage_for_upsert(session, packet_week, headline, university)
    if existing:
        apply_coverage_fields(existing, fields)
        return existing, False

    item = CoverageItem()
    apply_coverage_fields(item, fields, touch_updated=False)
    session.add(item)
    session.flush()
    return item, True


def apply_decision_fields(decision: PipelineDecision, fields: dict[str, Any]) -> PipelineDecision:
    for key in ("technology_uuid", "user_story", "status", "blocker", "signed_off_at"):
        if key in fields:
            setattr(decision, key, fields[key])
    decision.updated_at = datetime.now(timezone.utc)
    return decision


def create_pipeline_decision(
    session: Session,
    coverage_item: CoverageItem,
    data: dict[str, Any],
) -> PipelineDecision:
    status = data.get("status")
    if status not in DECISION_STATUSES:
        raise ValueError(f"status must be one of {DECISION_STATUSES}")
    user_story = data.get("user_story")
    if not user_story or not str(user_story).strip():
        raise ValueError("user_story is required")

    tech_uuid = data.get("technology_uuid")
    if tech_uuid is None:
        tech_uuid = coverage_item.technology_uuid

    decision = PipelineDecision(
        coverage_item_id=coverage_item.id,
        technology_uuid=tech_uuid,
        user_story=str(user_story).strip(),
        status=status,
        blocker=data.get("blocker"),
        signed_off_at=data.get("signed_off_at"),
    )
    session.add(decision)
    session.flush()
    return decision
