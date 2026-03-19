"""QA review API endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...database import db, Technology
from ...scrapers import SCRAPERS

router = APIRouter(prefix="/api/qa", tags=["qa"])


# ── Schemas ──────────────────────────────────────────────────────

class UniversityQAItem(BaseModel):
    university: str
    count: int
    status: str
    conflict_count: int


class SampleResponse(BaseModel):
    university: str
    technology_ids: list[int]


class ConflictItem(BaseModel):
    id: int
    technology_id: int
    field_name: str
    corrected_value: object
    new_scraped_value: object


class ConflictResolution(BaseModel):
    resolution: str  # "keep_correction" or "accept_new"


# ── Universities ─────────────────────────────────────────────────

@router.get("/universities", response_model=list[UniversityQAItem])
def list_qa_universities():
    """List all universities from SCRAPERS registry with QA status and tech counts."""
    # Seed from completed_scrapers.md if table is empty
    statuses = db.get_all_qa_statuses()
    if not statuses:
        db.set_qa_status("buffalo", "approved")
        statuses = db.get_all_qa_statuses()

    conflict_counts = db.count_conflicts_by_university()

    result = []
    for code in SCRAPERS:
        count = db.count_technologies(university=code)
        qa = statuses.get(code)
        result.append(UniversityQAItem(
            university=code,
            count=count,
            status=qa.status if qa else "pending",
            conflict_count=conflict_counts.get(code, 0),
        ))

    return result


@router.put("/universities/{code}/approve")
def approve_university(code: str):
    """Mark a university as approved."""
    if code not in SCRAPERS:
        raise HTTPException(status_code=404, detail=f"Unknown university: {code}")
    db.set_qa_status(code, "approved")
    return {"status": "approved", "university": code}


@router.put("/universities/{code}/unapprove")
def unapprove_university(code: str):
    """Revert a university to pending status."""
    if code not in SCRAPERS:
        raise HTTPException(status_code=404, detail=f"Unknown university: {code}")
    db.set_qa_status(code, "pending")
    return {"status": "pending", "university": code}


# ── Samples ──────────────────────────────────────────────────────

@router.get("/samples/{university}", response_model=SampleResponse)
def get_sample(university: str):
    """Get QA sample for a university. 404 if none exists."""
    if university not in SCRAPERS:
        raise HTTPException(status_code=404, detail=f"Unknown university: {university}")
    ids = db.get_sample(university)
    if not ids:
        raise HTTPException(status_code=404, detail="No sample exists. Create one first.")
    return SampleResponse(university=university, technology_ids=ids)


@router.post("/samples/{university}", response_model=SampleResponse)
def create_sample(university: str):
    """Create a QA sample (first 10 by id) for a university."""
    if university not in SCRAPERS:
        raise HTTPException(status_code=404, detail=f"Unknown university: {university}")
    ids = db.create_sample(university)
    if not ids:
        raise HTTPException(status_code=404, detail="No technologies found for this university.")
    return SampleResponse(university=university, technology_ids=ids)


@router.post("/samples/{university}/refresh")
async def refresh_sample(university: str):
    """Re-scrape detail pages for the sample technologies."""
    from ...scrapers import get_scraper
    from ...scrapers.flintbox_base import FlintboxScraper

    if university not in SCRAPERS:
        raise HTTPException(status_code=404, detail=f"Unknown university: {university}")

    sample_ids = db.get_sample(university)
    if not sample_ids:
        raise HTTPException(status_code=404, detail="No sample exists. Create one first.")

    scraper = get_scraper(university)
    is_flintbox = isinstance(scraper, FlintboxScraper)

    results = []
    for tech_id in sample_ids:
        with db.get_session() as session:
            tech = session.query(Technology).filter(Technology.id == tech_id).first()
            if not tech:
                results.append({"id": tech_id, "status": "not_found"})
                continue

            raw_data = dict(tech.raw_data or {})
            url = tech.url

            try:
                if is_flintbox:
                    tech_uuid = raw_data.get("uuid")
                    if not tech_uuid:
                        results.append({"id": tech_id, "status": "no_uuid"})
                        continue
                    detail = await scraper.scrape_technology_detail(tech_uuid)
                else:
                    if not hasattr(scraper, "scrape_technology_detail"):
                        results.append({"id": tech_id, "status": "no_detail_method"})
                        continue
                    detail = await scraper.scrape_technology_detail(url)

                if not detail:
                    results.append({"id": tech_id, "status": "no_detail"})
                    continue

                # Get existing corrections to protect them
                corrections = db.get_corrections_for_technology(tech_id)

                # Merge detail into raw_data, skipping corrected fields
                for key, value in detail.items():
                    if key not in corrections:
                        raw_data[key] = value

                tech.raw_data = raw_data
                tech.updated_at = datetime.now(timezone.utc)
                results.append({"id": tech_id, "status": "refreshed"})

            except Exception as e:
                results.append({"id": tech_id, "status": "error", "error": str(e)})

    return {"university": university, "results": results}


# ── Conflicts ────────────────────────────────────────────────────

@router.get("/conflicts/{university}", response_model=list[ConflictItem])
def list_conflicts(university: str):
    """List unresolved QA conflicts for a university."""
    if university not in SCRAPERS:
        raise HTTPException(status_code=404, detail=f"Unknown university: {university}")
    conflicts = db.get_conflicts(university)
    return [
        ConflictItem(
            id=c.id,
            technology_id=c.technology_id,
            field_name=c.field_name,
            corrected_value=c.corrected_value,
            new_scraped_value=c.new_scraped_value,
        )
        for c in conflicts
    ]


@router.post("/conflicts/{conflict_id}/resolve")
def resolve_conflict(conflict_id: int, body: ConflictResolution):
    """Resolve a QA conflict."""
    if body.resolution not in ("keep_correction", "accept_new"):
        raise HTTPException(status_code=400, detail="resolution must be 'keep_correction' or 'accept_new'")
    ok = db.resolve_conflict(conflict_id, body.resolution)
    if not ok:
        raise HTTPException(status_code=404, detail="Conflict not found")
    return {"resolved": True, "resolution": body.resolution}
