"""Technology API endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, or_

from ...database import db, Technology
from ...taxonomy import TAXONOMY
from ..schemas import (
    TechnologySummary,
    TechnologyDetail,
    PaginatedTechnologies,
    TaxonomyField,
    TaxonomySubfield,
)

router = APIRouter(prefix="/api", tags=["technologies"])


@router.get("/technologies", response_model=PaginatedTechnologies)
def list_technologies(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    q: Optional[str] = Query(None, description="Search in title and description"),
    top_field: Optional[str] = Query(None, description="Filter by top field"),
    subfield: Optional[str] = Query(None, description="Filter by subfield"),
    university: Optional[str] = Query(None, description="Filter by university"),
    from_date: Optional[datetime] = Query(None, description="Filter by first_seen >= date"),
    to_date: Optional[datetime] = Query(None, description="Filter by first_seen <= date"),
):
    """List technologies with pagination and filters."""
    with db.get_session() as session:
        query = session.query(Technology)

        # Apply filters
        if q:
            search_pattern = f"%{q}%"
            query = query.filter(
                or_(
                    Technology.title.ilike(search_pattern),
                    Technology.description.ilike(search_pattern),
                )
            )

        if top_field:
            query = query.filter(Technology.top_field == top_field)

        if subfield:
            query = query.filter(Technology.subfield == subfield)

        if university:
            query = query.filter(Technology.university == university)

        if from_date:
            query = query.filter(Technology.first_seen >= from_date)

        if to_date:
            query = query.filter(Technology.first_seen <= to_date)

        # Get total count
        total = query.count()

        # Calculate pagination
        pages = (total + limit - 1) // limit if total > 0 else 1
        offset = (page - 1) * limit

        # Get paginated results
        technologies = (
            query
            .order_by(Technology.first_seen.desc().nullslast())
            .offset(offset)
            .limit(limit)
            .all()
        )

        items = [
            TechnologySummary(
                uuid=str(t.uuid),
                university=t.university,
                tech_id=t.tech_id,
                title=t.title,
                url=t.url,
                top_field=t.top_field,
                subfield=t.subfield,
                first_seen=t.first_seen,
            )
            for t in technologies
        ]

        return PaginatedTechnologies(
            items=items,
            total=total,
            page=page,
            pages=pages,
            limit=limit,
        )


@router.get("/technologies/{uuid}", response_model=TechnologyDetail)
def get_technology(uuid: UUID):
    """Get a single technology by UUID."""
    with db.get_session() as session:
        tech = session.query(Technology).filter(Technology.uuid == uuid).first()

        if not tech:
            raise HTTPException(status_code=404, detail="Technology not found")

        return TechnologyDetail(
            uuid=str(tech.uuid),
            university=tech.university,
            tech_id=tech.tech_id,
            title=tech.title,
            description=tech.description,
            url=tech.url,
            top_field=tech.top_field,
            subfield=tech.subfield,
            patent_geography=tech.patent_geography,
            keywords=tech.keywords,
            classification_status=tech.classification_status,
            classification_confidence=tech.classification_confidence,
            scraped_at=tech.scraped_at,
            updated_at=tech.updated_at,
            first_seen=tech.first_seen,
            raw_data=tech.raw_data,
        )


@router.get("/taxonomy", response_model=list[TaxonomyField])
def get_taxonomy():
    """Get the field/subfield taxonomy for filter dropdowns."""
    return [
        TaxonomyField(
            name=field_name,
            subfields=[
                TaxonomySubfield(name=sf)
                for sf in definition.subfields
            ],
        )
        for field_name, definition in TAXONOMY.items()
    ]
