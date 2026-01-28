"""Statistics API endpoints."""

from fastapi import APIRouter
from sqlalchemy import func, extract

from ...database import db, Technology, ScrapeLog
from ..schemas import (
    StatsOverview,
    FieldCount,
    SubfieldCount,
    UniversityCount,
    TimelinePoint,
)

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/overview", response_model=StatsOverview)
def get_overview():
    """Get overall statistics."""
    with db.get_session() as session:
        total = session.query(func.count(Technology.id)).scalar() or 0

        universities = session.query(
            func.count(func.distinct(Technology.university))
        ).scalar() or 0

        fields = session.query(
            func.count(func.distinct(Technology.top_field))
        ).filter(Technology.top_field.isnot(None)).scalar() or 0

        classified = session.query(func.count(Technology.id)).filter(
            Technology.classification_status == "completed"
        ).scalar() or 0

        pending = session.query(func.count(Technology.id)).filter(
            Technology.classification_status == "pending"
        ).scalar() or 0

        last_scrape = session.query(func.max(ScrapeLog.completed_at)).scalar()

        return StatsOverview(
            total_technologies=total,
            total_universities=universities,
            total_fields=fields,
            classified_count=classified,
            pending_count=pending,
            last_scrape=last_scrape,
        )


@router.get("/by-field", response_model=list[FieldCount])
def get_by_field():
    """Get technology counts by field and subfield."""
    with db.get_session() as session:
        # Get top-level field counts
        field_counts = (
            session.query(
                Technology.top_field,
                func.count(Technology.id).label("count")
            )
            .filter(Technology.top_field.isnot(None))
            .group_by(Technology.top_field)
            .order_by(func.count(Technology.id).desc())
            .all()
        )

        results = []
        for top_field, count in field_counts:
            # Get subfield breakdown for this field
            subfield_counts = (
                session.query(
                    Technology.subfield,
                    func.count(Technology.id).label("count")
                )
                .filter(
                    Technology.top_field == top_field,
                    Technology.subfield.isnot(None)
                )
                .group_by(Technology.subfield)
                .order_by(func.count(Technology.id).desc())
                .all()
            )

            subfields = [
                SubfieldCount(subfield=sf, count=c)
                for sf, c in subfield_counts
            ]

            results.append(FieldCount(
                top_field=top_field,
                count=count,
                subfields=subfields,
            ))

        return results


@router.get("/by-university", response_model=list[UniversityCount])
def get_by_university():
    """Get technology counts by university."""
    with db.get_session() as session:
        # Get counts per university
        counts = (
            session.query(
                Technology.university,
                func.count(Technology.id).label("count")
            )
            .group_by(Technology.university)
            .order_by(func.count(Technology.id).desc())
            .all()
        )

        # Get last scrape times per university
        last_scrapes = dict(
            session.query(
                ScrapeLog.university,
                func.max(ScrapeLog.completed_at)
            )
            .filter(ScrapeLog.status == "completed")
            .group_by(ScrapeLog.university)
            .all()
        )

        return [
            UniversityCount(
                university=uni,
                count=count,
                last_scraped=last_scrapes.get(uni),
            )
            for uni, count in counts
        ]


@router.get("/timeline", response_model=list[TimelinePoint])
def get_timeline():
    """Get technology counts by month (based on first_seen)."""
    with db.get_session() as session:
        # Group by year-month of first_seen
        timeline = (
            session.query(
                extract("year", Technology.first_seen).label("year"),
                extract("month", Technology.first_seen).label("month"),
                func.count(Technology.id).label("count")
            )
            .filter(Technology.first_seen.isnot(None))
            .group_by("year", "month")
            .order_by("year", "month")
            .all()
        )

        return [
            TimelinePoint(
                month=f"{int(year)}-{int(month):02d}",
                count=count,
            )
            for year, month, count in timeline
            if year and month
        ]
