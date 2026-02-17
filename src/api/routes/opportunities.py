"""Opportunity assessment API endpoints."""

from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import String, func, or_
from sqlalchemy.orm import aliased

from ...database import db, Technology, TechnologyAssessment
from ...assessor import Assessor, AssessmentResult, AssessmentError
from ..schemas import (
    CategoryAssessmentResponse,
    OpportunitySummary,
    PaginatedOpportunities,
    OpportunityStats,
)

router = APIRouter(prefix="/api", tags=["opportunities"])


def _build_category_response(assessment, prefix: str) -> Optional[CategoryAssessmentResponse]:
    """Build a CategoryAssessmentResponse from assessment columns with a given prefix."""
    score = getattr(assessment, f"{prefix}_score", None)
    confidence = getattr(assessment, f"{prefix}_confidence", None)
    reasoning = getattr(assessment, f"{prefix}_reasoning", None)
    details = getattr(assessment, f"{prefix}_details", None)

    if score is None and confidence is None and reasoning is None and details is None:
        return None

    return CategoryAssessmentResponse(
        score=score,
        confidence=confidence,
        reasoning=reasoning,
        details=details,
    )


def _row_to_summary(tech: Technology, assessment: TechnologyAssessment) -> OpportunitySummary:
    """Convert a Technology + TechnologyAssessment row pair to an OpportunitySummary."""
    return OpportunitySummary(
        uuid=str(tech.uuid),
        title=tech.title,
        university=tech.university,
        top_field=tech.top_field,
        subfield=tech.subfield,
        patent_status=tech.patent_status,
        composite_score=assessment.composite_score,
        assessment_tier=assessment.assessment_tier,
        trl_gap=_build_category_response(assessment, "trl_gap"),
        false_barrier=_build_category_response(assessment, "false_barrier"),
        alt_application=_build_category_response(assessment, "alt_application"),
        assessed_at=assessment.assessed_at,
    )


# Latest assessment subquery used by list and detail endpoints
def _latest_assessment_subquery(session):
    """Return a subquery that selects the latest assessment ID per technology."""
    return (
        session.query(
            TechnologyAssessment.technology_id,
            func.max(TechnologyAssessment.id).label("max_id"),
        )
        .group_by(TechnologyAssessment.technology_id)
        .subquery("latest")
    )


@router.get("/opportunities/stats", response_model=OpportunityStats)
def get_opportunity_stats():
    """Aggregate stats for assessed technologies."""
    with db.get_session() as session:
        latest = _latest_assessment_subquery(session)

        base = (
            session.query(TechnologyAssessment)
            .join(latest, TechnologyAssessment.id == latest.c.max_id)
            .join(Technology, Technology.id == TechnologyAssessment.technology_id)
            .filter(Technology.assessment_status == "completed")
        )

        total_assessed = base.count()

        total_full = base.filter(TechnologyAssessment.assessment_tier == "full").count()
        total_limited = base.filter(TechnologyAssessment.assessment_tier == "limited").count()

        avg_composite = (
            session.query(func.avg(TechnologyAssessment.composite_score))
            .join(latest, TechnologyAssessment.id == latest.c.max_id)
            .join(Technology, Technology.id == TechnologyAssessment.technology_id)
            .filter(Technology.assessment_status == "completed")
            .scalar()
        )

        high_trl = (
            session.query(func.count())
            .select_from(TechnologyAssessment)
            .join(latest, TechnologyAssessment.id == latest.c.max_id)
            .join(Technology, Technology.id == TechnologyAssessment.technology_id)
            .filter(Technology.assessment_status == "completed")
            .filter(TechnologyAssessment.trl_gap_score > Decimal("0.7"))
            .scalar()
        )

        high_fb = (
            session.query(func.count())
            .select_from(TechnologyAssessment)
            .join(latest, TechnologyAssessment.id == latest.c.max_id)
            .join(Technology, Technology.id == TechnologyAssessment.technology_id)
            .filter(Technology.assessment_status == "completed")
            .filter(TechnologyAssessment.false_barrier_score > Decimal("0.7"))
            .scalar()
        )

        high_aa = (
            session.query(func.count())
            .select_from(TechnologyAssessment)
            .join(latest, TechnologyAssessment.id == latest.c.max_id)
            .join(Technology, Technology.id == TechnologyAssessment.technology_id)
            .filter(Technology.assessment_status == "completed")
            .filter(TechnologyAssessment.alt_application_score > Decimal("0.7"))
            .scalar()
        )

        return OpportunityStats(
            total_assessed=total_assessed,
            total_full=total_full,
            total_limited=total_limited,
            avg_composite_score=round(avg_composite, 2) if avg_composite is not None else None,
            high_trl_gap_count=high_trl or 0,
            high_false_barrier_count=high_fb or 0,
            high_alt_application_count=high_aa or 0,
        )


@router.get("/opportunities", response_model=PaginatedOpportunities)
def list_opportunities(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    q: Optional[str] = Query(None, description="Search in title, description, and assessment reasoning"),
    category: Optional[str] = Query(None, description="Category filter: trl_gap, false_barrier, alt_application"),
    min_score: Optional[float] = Query(None, ge=0, le=1, description="Minimum score filter"),
    min_confidence: Optional[float] = Query(None, ge=0, le=1, description="Minimum confidence filter"),
    top_field: Optional[str] = Query(None, description="Filter by top field"),
    subfield: Optional[str] = Query(None, description="Filter by subfield"),
    university: Optional[list[str]] = Query(None, description="Filter by university (multi-select)"),
    patent_status: Optional[str] = Query(None, description="Filter by patent status"),
    assessment_tier: Optional[str] = Query(None, description="Filter by assessment tier: full, limited"),
    sort: Optional[str] = Query("composite", description="Sort by: composite, trl_gap, false_barrier, alt_application"),
):
    """List assessed technologies (opportunities) with pagination and filters."""
    valid_categories = {"trl_gap", "false_barrier", "alt_application"}
    valid_sorts = {"composite", "trl_gap", "false_barrier", "alt_application"}

    if category and category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}")
    if sort and sort not in valid_sorts:
        raise HTTPException(status_code=400, detail=f"Invalid sort. Must be one of: {', '.join(valid_sorts)}")

    with db.get_session() as session:
        latest = _latest_assessment_subquery(session)

        query = (
            session.query(Technology, TechnologyAssessment)
            .join(TechnologyAssessment, Technology.id == TechnologyAssessment.technology_id)
            .join(latest, TechnologyAssessment.id == latest.c.max_id)
            .filter(Technology.assessment_status == "completed")
        )

        # Text search
        if q:
            search_pattern = f"%{q}%"
            query = query.filter(
                or_(
                    Technology.title.ilike(search_pattern),
                    Technology.description.ilike(search_pattern),
                    TechnologyAssessment.trl_gap_reasoning.ilike(search_pattern),
                    TechnologyAssessment.false_barrier_reasoning.ilike(search_pattern),
                    TechnologyAssessment.alt_application_reasoning.ilike(search_pattern),
                )
            )

        # Technology filters
        if top_field:
            query = query.filter(Technology.top_field == top_field)
        if subfield:
            query = query.filter(Technology.subfield == subfield)
        if university:
            query = query.filter(Technology.university.in_(university))
        if patent_status:
            query = query.filter(Technology.patent_status == patent_status)

        # Assessment filters
        if assessment_tier:
            query = query.filter(TechnologyAssessment.assessment_tier == assessment_tier)

        # Score/confidence filters
        if min_score is not None:
            min_score_dec = Decimal(str(min_score))
            if category:
                score_col = getattr(TechnologyAssessment, f"{category}_score")
                query = query.filter(score_col >= min_score_dec)
            else:
                query = query.filter(TechnologyAssessment.composite_score >= min_score_dec)

        if min_confidence is not None:
            min_conf_dec = Decimal(str(min_confidence))
            if category:
                conf_col = getattr(TechnologyAssessment, f"{category}_confidence")
                query = query.filter(conf_col >= min_conf_dec)
            else:
                # Apply to all categories
                query = query.filter(
                    or_(
                        TechnologyAssessment.trl_gap_confidence >= min_conf_dec,
                        TechnologyAssessment.false_barrier_confidence >= min_conf_dec,
                        TechnologyAssessment.alt_application_confidence >= min_conf_dec,
                    )
                )

        # Get total count before pagination
        total = query.count()

        # Sorting
        if sort == "composite":
            order_col = TechnologyAssessment.composite_score.desc().nullslast()
        else:
            order_col = getattr(TechnologyAssessment, f"{sort}_score").desc().nullslast()

        # Pagination
        pages = (total + limit - 1) // limit if total > 0 else 1
        offset = (page - 1) * limit

        results = (
            query
            .order_by(order_col)
            .offset(offset)
            .limit(limit)
            .all()
        )

        items = [_row_to_summary(tech, assessment) for tech, assessment in results]

        return PaginatedOpportunities(
            items=items,
            total=total,
            page=page,
            pages=pages,
            limit=limit,
        )


@router.get("/opportunities/{uuid}")
def get_opportunity(uuid: UUID):
    """Get full assessment detail for a single technology."""
    with db.get_session() as session:
        tech = session.query(Technology).filter(Technology.uuid == uuid).first()
        if not tech:
            raise HTTPException(status_code=404, detail="Technology not found")

        assessment = (
            session.query(TechnologyAssessment)
            .filter(TechnologyAssessment.technology_id == tech.id)
            .order_by(TechnologyAssessment.assessed_at.desc())
            .first()
        )

        if not assessment:
            raise HTTPException(status_code=404, detail="No assessment found for this technology")

        return _row_to_summary(tech, assessment)


@router.post("/opportunities/{uuid}/assess")
def assess_opportunity(uuid: UUID):
    """Trigger on-demand assessment for a technology."""
    with db.get_session() as session:
        tech = session.query(Technology).filter(Technology.uuid == uuid).first()
        if not tech:
            raise HTTPException(status_code=404, detail="Technology not found")

        tech_id = tech.id
        title = tech.title
        description = tech.description
        raw_data = tech.raw_data

    # Run assessment outside the session
    assessor = Assessor()
    result = assessor.assess(title, description, raw_data)

    if isinstance(result, AssessmentError):
        raise HTTPException(
            status_code=500,
            detail={
                "error_type": result.error_type,
                "message": result.message,
                "retryable": result.retryable,
            },
        )

    # Build assessment_data dict for store_assessment
    assessment_data = {
        "assessment_tier": result.assessment_tier,
        "composite_score": result.composite_score,
        "model": result.model,
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "total_cost": result.total_cost,
        "raw_response": result.raw_response,
    }

    for cat_name in ("trl_gap", "false_barrier", "alt_application"):
        cat = getattr(result, cat_name, None)
        if cat is not None:
            assessment_data[f"{cat_name}_score"] = cat.score
            assessment_data[f"{cat_name}_confidence"] = cat.confidence
            assessment_data[f"{cat_name}_reasoning"] = cat.reasoning
            assessment_data[f"{cat_name}_details"] = cat.details

    stored = db.store_assessment(tech_id, assessment_data)

    if stored is None:
        raise HTTPException(status_code=500, detail="Failed to store assessment")

    # Return the result
    with db.get_session() as session:
        tech = session.query(Technology).filter(Technology.id == tech_id).first()
        return _row_to_summary(tech, stored)
