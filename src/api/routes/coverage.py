"""Coverage items and pipeline-decision API endpoints.

Coverage records are independent of scraped TTO listings. Saving a find
never requires a ``technologies`` row. Pipeline status lives on
``pipeline_decisions``, not on ``technologies``.
"""

from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, or_

from ...coverage import (
    DECISION_STATUSES,
    SOURCE_CLASSES,
    apply_coverage_fields,
    apply_decision_fields,
    blank_to_none,
    create_pipeline_decision,
    monday_of,
    resolve_technology_match,
    upsert_coverage_item,
)
from ...database import CoverageItem, PipelineDecision, db
from ..schemas import (
    CoverageItemCreate,
    CoverageItemResponse,
    CoverageItemUpdate,
    CoverageUpsertRequest,
    CoverageUpsertItemResult,
    CoverageUpsertResponse,
    CoverageWeekCount,
    PaginatedCoverage,
    PaginatedDecisions,
    PipelineDecisionCreate,
    PipelineDecisionResponse,
    PipelineDecisionUpdate,
)

router = APIRouter(prefix="/api", tags=["coverage"])


def _decision_to_response(decision: PipelineDecision) -> PipelineDecisionResponse:
    return PipelineDecisionResponse(
        id=str(decision.id),
        coverage_item_id=str(decision.coverage_item_id),
        technology_uuid=str(decision.technology_uuid) if decision.technology_uuid else None,
        user_story=decision.user_story,
        status=decision.status,
        blocker=decision.blocker,
        signed_off_at=decision.signed_off_at,
        created_at=decision.created_at,
        updated_at=decision.updated_at,
    )


def _item_to_response(
    item: CoverageItem,
    *,
    include_decisions: bool = False,
    latest_decision: Optional[PipelineDecision] = None,
) -> CoverageItemResponse:
    decisions = None
    latest = latest_decision
    if include_decisions:
        ordered = sorted(
            item.decisions or [],
            key=lambda d: d.created_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        decisions = [_decision_to_response(d) for d in ordered]
        if latest is None and ordered:
            latest = ordered[0]
    return CoverageItemResponse(
        id=str(item.id),
        technology_uuid=str(item.technology_uuid) if item.technology_uuid else None,
        university=item.university,
        headline=item.headline,
        summary=item.summary,
        capability=item.capability,
        sources=item.sources or [],
        source_class=item.source_class,
        independence_note=item.independence_note,
        coverage_date=item.coverage_date,
        packet_week=item.packet_week,
        match_status=item.match_status,
        created_at=item.created_at,
        updated_at=item.updated_at,
        latest_decision=_decision_to_response(latest) if latest else None,
        decisions=decisions,
    )


def _create_payload(body: CoverageItemCreate) -> dict:
    return body.model_dump()


@router.get("/coverage/weeks", response_model=list[CoverageWeekCount])
def list_coverage_weeks():
    """Distinct packet weeks with item counts, newest first."""
    with db.get_session() as session:
        rows = (
            session.query(CoverageItem.packet_week, func.count(CoverageItem.id))
            .filter(CoverageItem.packet_week.isnot(None))
            .group_by(CoverageItem.packet_week)
            .order_by(CoverageItem.packet_week.desc())
            .all()
        )
        return [CoverageWeekCount(packet_week=week, count=count) for week, count in rows]


@router.post("/coverage/upsert", response_model=CoverageUpsertResponse)
def upsert_coverage(body: CoverageUpsertRequest):
    """Weekly upsert keyed by packet_week (Monday) + headline + university.

    Accepts a single item (top-level fields) or a batch under ``items``.
    ``technology_uuid`` is optional; unmatched finds are saved with NULL.
    """
    if body.items:
        payloads = []
        for item in body.items:
            payload = item.model_dump()
            if payload.get("packet_week") is None and body.packet_week is not None:
                payload["packet_week"] = body.packet_week
            payloads.append(payload)
        auto_match = body.auto_match
    else:
        if not body.headline or not body.source_class:
            raise HTTPException(
                status_code=422,
                detail="Provide items[] or headline + source_class for a single upsert",
            )
        payloads = [
            body.model_dump(exclude={"items", "auto_match"}, exclude_none=False)
        ]
        auto_match = body.auto_match

    results: list[CoverageUpsertItemResult] = []
    created = 0
    updated = 0
    try:
        with db.get_session() as session:
            for payload in payloads:
                payload.pop("items", None)
                payload.pop("auto_match", None)
                item, was_created = upsert_coverage_item(
                    session, payload, auto_match=auto_match
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
                results.append(
                    CoverageUpsertItemResult(
                        item=_item_to_response(item),
                        created=was_created,
                    )
                )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return CoverageUpsertResponse(items=results, created=created, updated=updated)


@router.get("/coverage", response_model=PaginatedCoverage)
def list_coverage(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None, description="Search headline, summary, university"),
    packet_week: Optional[date] = Query(None, description="Monday of the briefing week"),
    university: Optional[str] = Query(None),
    match_status: Optional[str] = Query(None, description="matched, unmatched, candidate"),
    source_class: Optional[str] = Query(None, description="newspaper_tv or specialist"),
    decision_status: Optional[str] = Query(
        None, description="Filter by latest decision status"
    ),
    unmatched_only: bool = Query(False, description="Only items with no technology_uuid"),
):
    """List coverage finds. Independent of TTO listing rows."""
    with db.get_session() as session:
        latest = (
            session.query(
                PipelineDecision.coverage_item_id,
                func.max(PipelineDecision.created_at).label("max_created"),
            )
            .group_by(PipelineDecision.coverage_item_id)
            .subquery("latest_decision")
        )
        latest_row = (
            session.query(PipelineDecision)
            .join(
                latest,
                (PipelineDecision.coverage_item_id == latest.c.coverage_item_id)
                & (PipelineDecision.created_at == latest.c.max_created),
            )
            .subquery("latest_row")
        )

        query = session.query(CoverageItem).outerjoin(
            latest_row, CoverageItem.id == latest_row.c.coverage_item_id
        )

        if q:
            pattern = f"%{q}%"
            query = query.filter(
                or_(
                    CoverageItem.headline.ilike(pattern),
                    CoverageItem.summary.ilike(pattern),
                    CoverageItem.university.ilike(pattern),
                    CoverageItem.capability.ilike(pattern),
                )
            )
        if packet_week is not None:
            query = query.filter(CoverageItem.packet_week == monday_of(packet_week))
        if university:
            query = query.filter(CoverageItem.university == university)
        if match_status:
            query = query.filter(CoverageItem.match_status == match_status)
        if source_class:
            query = query.filter(CoverageItem.source_class == source_class)
        if unmatched_only:
            query = query.filter(CoverageItem.technology_uuid.is_(None))
        if decision_status:
            if decision_status not in DECISION_STATUSES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid decision_status. Must be one of: {', '.join(DECISION_STATUSES)}",
                )
            query = query.filter(latest_row.c.status == decision_status)

        total = query.count()
        pages = (total + limit - 1) // limit if total > 0 else 1
        offset = (page - 1) * limit

        rows = (
            query.order_by(CoverageItem.packet_week.desc().nullslast(), CoverageItem.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        # Attach latest decision per item in one query
        ids = [row.id for row in rows]
        latest_by_item: dict = {}
        if ids:
            decisions = (
                session.query(PipelineDecision)
                .filter(PipelineDecision.coverage_item_id.in_(ids))
                .order_by(PipelineDecision.created_at.desc())
                .all()
            )
            for decision in decisions:
                latest_by_item.setdefault(decision.coverage_item_id, decision)

        items = [
            _item_to_response(row, latest_decision=latest_by_item.get(row.id))
            for row in rows
        ]
        return PaginatedCoverage(items=items, total=total, page=page, pages=pages, limit=limit)


@router.post("/coverage", response_model=CoverageItemResponse, status_code=201)
def create_coverage(body: CoverageItemCreate):
    """Create a coverage find. ``technology_uuid`` may be null."""
    try:
        with db.get_session() as session:
            item, _created = upsert_coverage_item(session, _create_payload(body), auto_match=True)
            return _item_to_response(item)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/coverage/{item_id}", response_model=CoverageItemResponse)
def get_coverage(item_id: UUID):
    """Get one coverage find, including its pipeline decisions."""
    with db.get_session() as session:
        item = session.query(CoverageItem).filter(CoverageItem.id == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Coverage item not found")
        return _item_to_response(item, include_decisions=True)


@router.patch("/coverage/{item_id}", response_model=CoverageItemResponse)
def update_coverage(item_id: UUID, body: CoverageItemUpdate):
    """Partial update of a coverage find. Does not require a TTO match."""
    updates = body.model_dump(exclude_unset=True)
    with db.get_session() as session:
        item = session.query(CoverageItem).filter(CoverageItem.id == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Coverage item not found")

        if "headline" in updates:
            headline = (updates["headline"] or "").strip()
            if not headline:
                raise HTTPException(status_code=422, detail="headline is required")
            updates["headline"] = headline
        if "university" in updates:
            updates["university"] = blank_to_none(updates["university"])
        if "packet_week" in updates and updates["packet_week"] is not None:
            updates["packet_week"] = monday_of(updates["packet_week"])
        if "source_class" in updates and updates["source_class"] not in SOURCE_CLASSES:
            raise HTTPException(
                status_code=422,
                detail=f"source_class must be one of {SOURCE_CLASSES}",
            )
        if "sources" in updates and updates["sources"] is not None and not isinstance(updates["sources"], list):
            raise HTTPException(status_code=422, detail="sources must be a JSON array")

        match_keys = {"technology_uuid", "headline", "university", "match_status"}
        match_inputs_changed = any(key in updates for key in match_keys)
        apply_coverage_fields(item, {k: v for k, v in updates.items() if k != "match_status"})
        if match_inputs_changed:
            tech_uuid, status = resolve_technology_match(
                session,
                item.technology_uuid,
                item.university,
                item.headline,
                requested_status=updates.get("match_status"),
            )
            item.technology_uuid = tech_uuid
            item.match_status = status
        return _item_to_response(item, include_decisions=True)


@router.get("/coverage/{item_id}/decisions", response_model=list[PipelineDecisionResponse])
def list_item_decisions(item_id: UUID):
    """List pipeline decisions for a coverage item, newest first."""
    with db.get_session() as session:
        item = session.query(CoverageItem).filter(CoverageItem.id == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Coverage item not found")
        decisions = (
            session.query(PipelineDecision)
            .filter(PipelineDecision.coverage_item_id == item_id)
            .order_by(PipelineDecision.created_at.desc())
            .all()
        )
        return [_decision_to_response(d) for d in decisions]


@router.post(
    "/coverage/{item_id}/decisions",
    response_model=PipelineDecisionResponse,
    status_code=201,
)
def create_item_decision(item_id: UUID, body: PipelineDecisionCreate):
    """Record a hold / proceed / archive (etc.) decision for a coverage item."""
    with db.get_session() as session:
        item = session.query(CoverageItem).filter(CoverageItem.id == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Coverage item not found")
        try:
            decision = create_pipeline_decision(session, item, body.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return _decision_to_response(decision)


@router.get("/pipeline-decisions", response_model=PaginatedDecisions)
def list_decisions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    coverage_item_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    technology_uuid: Optional[UUID] = Query(None),
):
    """List pipeline decisions across coverage items."""
    with db.get_session() as session:
        query = session.query(PipelineDecision)
        if coverage_item_id:
            query = query.filter(PipelineDecision.coverage_item_id == coverage_item_id)
        if status:
            if status not in DECISION_STATUSES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status. Must be one of: {', '.join(DECISION_STATUSES)}",
                )
            query = query.filter(PipelineDecision.status == status)
        if technology_uuid:
            query = query.filter(PipelineDecision.technology_uuid == technology_uuid)

        total = query.count()
        pages = (total + limit - 1) // limit if total > 0 else 1
        offset = (page - 1) * limit
        rows = (
            query.order_by(PipelineDecision.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return PaginatedDecisions(
            items=[_decision_to_response(d) for d in rows],
            total=total,
            page=page,
            pages=pages,
            limit=limit,
        )


@router.get("/pipeline-decisions/{decision_id}", response_model=PipelineDecisionResponse)
def get_decision(decision_id: UUID):
    with db.get_session() as session:
        decision = session.query(PipelineDecision).filter(PipelineDecision.id == decision_id).first()
        if not decision:
            raise HTTPException(status_code=404, detail="Pipeline decision not found")
        return _decision_to_response(decision)


@router.patch("/pipeline-decisions/{decision_id}", response_model=PipelineDecisionResponse)
def update_decision(decision_id: UUID, body: PipelineDecisionUpdate):
    updates = body.model_dump(exclude_unset=True)
    with db.get_session() as session:
        decision = session.query(PipelineDecision).filter(PipelineDecision.id == decision_id).first()
        if not decision:
            raise HTTPException(status_code=404, detail="Pipeline decision not found")
        if "status" in updates and updates["status"] not in DECISION_STATUSES:
            raise HTTPException(
                status_code=422,
                detail=f"status must be one of {DECISION_STATUSES}",
            )
        if "user_story" in updates:
            story = (updates["user_story"] or "").strip()
            if not story:
                raise HTTPException(status_code=422, detail="user_story is required")
            updates["user_story"] = story
        apply_decision_fields(decision, updates)
        return _decision_to_response(decision)
