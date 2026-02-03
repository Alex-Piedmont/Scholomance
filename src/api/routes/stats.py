"""Statistics API endpoints."""

from fastapi import APIRouter
from sqlalchemy import cast, func, extract, Date

from ...database import db, Technology, ScrapeLog
from ..schemas import (
    StatsOverview,
    FieldCount,
    SubfieldCount,
    UniversityCount,
    TimelinePoint,
    KeywordCount,
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

        granted_patents = session.query(func.count(Technology.id)).filter(
            Technology.patent_status == "granted"
        ).scalar() or 0

        last_scrape = session.query(func.max(ScrapeLog.completed_at)).scalar()

        return StatsOverview(
            total_technologies=total,
            total_universities=universities,
            total_fields=fields,
            granted_patents=granted_patents,
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


@router.get("/keywords", response_model=list[KeywordCount])
def get_keywords():
    """Get keyword counts across all technologies."""
    with db.get_session() as session:
        keyword = func.unnest(Technology.keywords).label("keyword")
        EXCLUDED = {"available technologies"}
        counts = (
            session.query(keyword, func.count().label("count"))
            .filter(Technology.keywords.isnot(None))
            .group_by("keyword")
            .order_by(func.count().desc())
            .limit(120)
            .all()
        )
        return [
            KeywordCount(keyword=kw, count=c)
            for kw, c in counts
            if kw.lower() not in EXCLUDED
        ][:100]


@router.get("/timeline", response_model=list[TimelinePoint])
def get_timeline():
    """Get technology counts by month (based on published date)."""
    with db.get_session() as session:
        # Use published_on or web_published from raw_data; exclude records without a published date
        pub_date = func.coalesce(
            cast(Technology.raw_data['published_on'].astext, Date),
            cast(Technology.raw_data['web_published'].astext, Date),
        )
        timeline = (
            session.query(
                extract("year", pub_date).label("year"),
                extract("month", pub_date).label("month"),
                func.count(Technology.id).label("count")
            )
            .filter(pub_date.isnot(None))
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
