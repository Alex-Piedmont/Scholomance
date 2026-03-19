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
    from sqlalchemy import func as sqlfunc

    with db.get_session() as session:
        # Seed from completed_scrapers.md if table is empty
        from ...database import UniversityQAStatus, Technology, QAConflict
        status_count = session.query(sqlfunc.count(UniversityQAStatus.id)).scalar()
        if not status_count:
            session.add(UniversityQAStatus(university="buffalo", status="approved", approved_at=datetime.now(timezone.utc)))
            session.flush()

        # All three queries in one session
        statuses = {
            row.university: row.status
            for row in session.query(UniversityQAStatus).all()
        }

        tech_counts = dict(
            session.query(Technology.university, sqlfunc.count(Technology.id))
            .group_by(Technology.university)
            .all()
        )

        conflict_counts = dict(
            session.query(Technology.university, sqlfunc.count(QAConflict.id))
            .join(Technology, QAConflict.technology_id == Technology.id)
            .group_by(Technology.university)
            .all()
        )

    result = []
    for code in SCRAPERS:
        result.append(UniversityQAItem(
            university=code,
            count=tech_counts.get(code, 0),
            status=statuses.get(code, "pending"),
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
    """Re-scrape detail pages for the sample technologies.

    For Flintbox scrapers, runs the full parsing pipeline (_parse_api_item_with_detail)
    to produce properly cleaned/normalized raw_data. For others, merges detail fields.
    Corrected fields are always preserved.
    """
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

    if is_flintbox:
        results = await _refresh_flintbox_sample(scraper, sample_ids)
    elif hasattr(scraper, '_parse_algolia_hit'):
        # Algolia-based scrapers (JHU etc.) need full pipeline re-parse
        results = await _refresh_algolia_sample(scraper, sample_ids)
    else:
        results = await _refresh_generic_sample(scraper, sample_ids)

    return {"university": university, "results": results}


async def _refresh_flintbox_sample(scraper, sample_ids: list[int]) -> list[dict]:
    """Refresh Flintbox sample techs through the full parsing pipeline."""
    import aiohttp

    # Build a map of tech_id (string) -> db info for the sample
    tech_map: dict[str, dict] = {}
    for tid in sample_ids:
        with db.get_session() as session:
            tech = session.query(Technology).filter(Technology.id == tid).first()
            if tech:
                tech_map[str(tech.tech_id)] = {
                    "db_id": tid,
                    "raw_data": dict(tech.raw_data or {}),
                }

    if not tech_map:
        return [{"id": tid, "status": "not_found"} for tid in sample_ids]

    # Fetch API list items for these techs
    api_items = {}
    params = {
        "organizationId": scraper.ORGANIZATION_ID,
        "organizationAccessKey": scraper.ACCESS_KEY,
        "query": "",
    }
    try:
        await scraper._init_session()
        # Fetch pages until we find all sample techs (they're the first N by id)
        for page_num in range(1, 20):
            async with scraper._session.get(
                scraper.api_url, params={**params, "page": page_num}
            ) as resp:
                if resp.status != 200:
                    break
                data = await resp.json()
                items = data.get("data", [])
                if not items:
                    break
                for item in items:
                    item_id = str(item.get("id", ""))
                    if item_id in tech_map:
                        api_items[item_id] = item
                # Stop once we've found all sample items
                if len(api_items) >= len(tech_map):
                    break
    finally:
        await scraper._close_session()

    # Run each through the full pipeline
    results = []
    for tech_id_str, info in tech_map.items():
        tid = info["db_id"]
        api_item = api_items.get(tech_id_str)
        if not api_item:
            results.append({"id": tid, "status": "not_in_api"})
            continue

        try:
            parsed_tech = await scraper._parse_api_item_with_detail(api_item)
            if not parsed_tech:
                results.append({"id": tid, "status": "parse_failed"})
                continue

            new_raw = dict(parsed_tech.raw_data or {})

            # Protect corrected fields
            corrections = db.get_corrections_for_technology(tid)
            for field_name in corrections:
                if field_name in info["raw_data"]:
                    new_raw[field_name] = info["raw_data"][field_name]

            with db.get_session() as session:
                tech = session.query(Technology).filter(Technology.id == tid).first()
                if tech:
                    tech.raw_data = new_raw
                    tech.updated_at = datetime.now(timezone.utc)

            results.append({"id": tid, "status": "refreshed"})
        except Exception as e:
            results.append({"id": tid, "status": "error", "error": str(e)})

    # Include not-found entries for any IDs not in tech_map
    found_ids = {info["db_id"] for info in tech_map.values()}
    for tid in sample_ids:
        if tid not in found_ids:
            results.append({"id": tid, "status": "not_found"})

    return results


async def _refresh_algolia_sample(scraper, sample_ids: list[int]) -> list[dict]:
    """Refresh Algolia-based sample techs (JHU) through the full parsing pipeline."""
    import aiohttp

    # Build tech_id -> db info map
    tech_map: dict[str, dict] = {}
    for tid in sample_ids:
        with db.get_session() as session:
            tech = session.query(Technology).filter(Technology.id == tid).first()
            if tech:
                tech_map[str(tech.tech_id)] = {
                    "db_id": tid,
                    "raw_data": dict(tech.raw_data or {}),
                }

    if not tech_map:
        return [{"id": tid, "status": "not_found"} for tid in sample_ids]

    # Query Algolia for the sample techs
    algolia_hits: dict[str, dict] = {}
    headers = {
        "X-Algolia-Application-Id": scraper.ALGOLIA_APP_ID,
        "X-Algolia-API-Key": scraper.ALGOLIA_API_KEY,
        "Content-Type": "application/json",
    }
    try:
        async with aiohttp.ClientSession() as session:
            for tech_id_str in tech_map:
                payload = {
                    "query": tech_id_str,
                    "hitsPerPage": 5,
                    "attributesToRetrieve": ["*"],
                }
                async with session.post(scraper.ALGOLIA_URL, headers=headers, json=payload) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json()
                    for hit in data.get("hits", []):
                        hit_id = hit.get("techID", "") or str(hit.get("objectID", ""))
                        if hit_id == tech_id_str:
                            algolia_hits[hit_id] = hit
                            break
    except Exception as e:
        return [{"id": tid, "status": "error", "error": str(e)} for tid in sample_ids]

    # Parse each through the full Algolia pipeline + detail enrichment
    results = []
    for tech_id_str, info in tech_map.items():
        tid = info["db_id"]
        hit = algolia_hits.get(tech_id_str)
        if not hit:
            results.append({"id": tid, "status": "not_in_algolia"})
            continue

        try:
            parsed_tech = scraper._parse_algolia_hit(hit)
            if not parsed_tech:
                results.append({"id": tid, "status": "parse_failed"})
                continue

            new_raw = dict(parsed_tech.raw_data or {})

            # Also fetch detail page for enrichment
            try:
                detail = await scraper.scrape_technology_detail(parsed_tech.url)
                if detail:
                    for key, value in detail.items():
                        if key not in new_raw or not new_raw[key]:
                            new_raw[key] = value
                    # Update description from detail abstract if available
                    if detail.get("abstract") and (not new_raw.get("description") or "&" in new_raw.get("description", "")):
                        new_raw["description"] = detail["abstract"]
            except Exception:
                pass  # Detail enrichment is best-effort

            # Protect corrected fields
            corrections = db.get_corrections_for_technology(tid)
            for field_name in corrections:
                if field_name in info["raw_data"]:
                    new_raw[field_name] = info["raw_data"][field_name]

            with db.get_session() as session:
                tech = session.query(Technology).filter(Technology.id == tid).first()
                if tech:
                    tech.raw_data = new_raw
                    tech.updated_at = datetime.now(timezone.utc)

            results.append({"id": tid, "status": "refreshed"})
        except Exception as e:
            results.append({"id": tid, "status": "error", "error": str(e)})

    found_ids = {info["db_id"] for info in tech_map.values()}
    for tid in sample_ids:
        if tid not in found_ids:
            results.append({"id": tid, "status": "not_found"})

    return results


async def _refresh_generic_sample(scraper, sample_ids: list[int]) -> list[dict]:
    """Refresh non-Flintbox sample techs by merging detail page data."""
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
                if not hasattr(scraper, "scrape_technology_detail"):
                    results.append({"id": tech_id, "status": "no_detail_method"})
                    continue
                detail = await scraper.scrape_technology_detail(url)

                if not detail:
                    results.append({"id": tech_id, "status": "no_detail"})
                    continue

                corrections = db.get_corrections_for_technology(tech_id)
                for key, value in detail.items():
                    if key not in corrections:
                        raw_data[key] = value

                tech.raw_data = raw_data
                tech.updated_at = datetime.now(timezone.utc)
                results.append({"id": tech_id, "status": "refreshed"})

            except Exception as e:
                results.append({"id": tech_id, "status": "error", "error": str(e)})

    return results


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
