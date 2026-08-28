"""Tests for coverage items, weekly upsert, and pipeline decisions."""

from contextlib import contextmanager
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.coverage import (
    DECISION_STATUSES,
    MATCH_STATUSES,
    SOURCE_CLASSES,
    apply_coverage_fields,
    blank_to_none,
    coverage_upsert_identity,
    create_pipeline_decision,
    identities_equal,
    monday_of,
    resolve_technology_match,
    upsert_coverage_item,
)
from src.database import CoverageItem, PipelineDecision, Technology


def test_monday_of_normalizes_midweek():
    assert monday_of(date(2026, 8, 28)) == date(2026, 8, 24)  # Friday -> Monday
    assert monday_of(date(2026, 8, 24)) == date(2026, 8, 24)  # already Monday
    assert monday_of(date(2026, 8, 30)) == date(2026, 8, 24)  # Sunday -> Monday


def test_upsert_identity_strips_and_nulls_blank_university():
    ident = coverage_upsert_identity(date(2026, 8, 28), "  A headline  ", "  ")
    assert ident == (date(2026, 8, 24), "A headline", None)
    assert identities_equal(ident, coverage_upsert_identity(date(2026, 8, 24), "A headline", None))


def test_blank_to_none():
    assert blank_to_none("") is None
    assert blank_to_none("  ") is None
    assert blank_to_none(None) is None
    assert blank_to_none("stanford") == "stanford"


def test_coverage_item_is_not_a_technology():
    assert CoverageItem.__tablename__ == "coverage_items"
    assert PipelineDecision.__tablename__ == "pipeline_decisions"
    assert "status" not in {c.name for c in Technology.__table__.columns}
    assert "user_story" not in {c.name for c in Technology.__table__.columns}
    tech_uuid_col = CoverageItem.__table__.c.technology_uuid
    assert tech_uuid_col.nullable
    assert len(tech_uuid_col.foreign_keys) == 0


def test_pipeline_decision_fk_points_at_coverage_not_listings():
    fk = next(iter(PipelineDecision.__table__.c.coverage_item_id.foreign_keys))
    assert fk.column.table.name == "coverage_items"
    assert PipelineDecision.__table__.c.technology_uuid.nullable
    assert len(PipelineDecision.__table__.c.technology_uuid.foreign_keys) == 0


def _filter_chain(first_value=None):
    query = MagicMock()
    query.filter.return_value = query
    query.limit.return_value = query
    query.first.return_value = first_value
    query.all.return_value = []
    return query


def test_resolve_match_unmatched_when_no_listing():
    session = MagicMock()
    tech_query = _filter_chain(first_value=None)
    tech_query.limit.return_value.all.return_value = []
    session.query.return_value = tech_query

    uuid_out, status = resolve_technology_match(session, None, "stanford", "No such listing")
    assert uuid_out is None
    assert status == "unmatched"


def test_resolve_match_explicit_uuid_that_exists():
    session = MagicMock()
    known = uuid4()
    session.query.return_value.filter.return_value.first.return_value = (known,)

    uuid_out, status = resolve_technology_match(session, known, None, "Headline")
    assert uuid_out == known
    assert status == "matched"


def test_resolve_match_explicit_uuid_missing_is_candidate_not_rejected():
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    dangling = uuid4()

    uuid_out, status = resolve_technology_match(session, dangling, None, "Headline")
    assert uuid_out == dangling
    assert status == "candidate"


def test_resolve_match_title_hit_is_candidate():
    session = MagicMock()
    hit = MagicMock()
    hit.uuid = uuid4()
    query = _filter_chain()
    query.limit.return_value.all.return_value = [hit]
    session.query.return_value = query

    uuid_out, status = resolve_technology_match(session, None, "stanford", "Exact Title")
    assert uuid_out == hit.uuid
    assert status == "candidate"


def test_resolve_match_requested_unmatched_drops_auto_uuid():
    session = MagicMock()
    hit = MagicMock()
    hit.uuid = uuid4()
    query = _filter_chain()
    query.limit.return_value.all.return_value = [hit]
    session.query.return_value = query

    uuid_out, status = resolve_technology_match(
        session, None, "stanford", "Exact Title", requested_status="unmatched"
    )
    assert uuid_out is None
    assert status == "unmatched"


def test_upsert_creates_unmatched_item():
    session = MagicMock()
    lookup = _filter_chain(first_value=None)
    match_query = _filter_chain()
    match_query.limit.return_value.all.return_value = []

    def query_side_effect(model):
        if model is CoverageItem:
            return lookup
        return match_query

    session.query.side_effect = query_side_effect

    item, created = upsert_coverage_item(
        session,
        {
            "headline": "Campus lab ships new sensor",
            "source_class": "newspaper_tv",
            "university": None,
            "packet_week": date(2026, 8, 26),
            "sources": [{"url": "https://example.com/story", "title": "Local TV"}],
        },
    )
    assert created is True
    session.add.assert_called_once()
    assert item.technology_uuid is None
    assert item.match_status == "unmatched"
    assert item.packet_week == date(2026, 8, 24)
    assert item.university is None


def test_upsert_updates_existing_by_week_headline_university():
    existing = CoverageItem(
        id=uuid4(),
        headline="Campus lab ships new sensor",
        university="stanford",
        source_class="newspaper_tv",
        match_status="unmatched",
        packet_week=date(2026, 8, 24),
        sources=[],
    )
    session = MagicMock()
    lookup = _filter_chain(first_value=existing)
    match_query = _filter_chain()
    match_query.limit.return_value.all.return_value = []

    def query_side_effect(model):
        if model is CoverageItem:
            return lookup
        return match_query

    session.query.side_effect = query_side_effect

    item, created = upsert_coverage_item(
        session,
        {
            "headline": "Campus lab ships new sensor",
            "source_class": "specialist",
            "university": "stanford",
            "packet_week": date(2026, 8, 24),
            "summary": "Updated blurb",
        },
    )
    assert created is False
    assert item is existing
    assert item.summary == "Updated blurb"
    assert item.source_class == "specialist"
    session.add.assert_not_called()


def test_upsert_rejects_bad_source_class():
    session = MagicMock()
    with pytest.raises(ValueError, match="source_class"):
        upsert_coverage_item(session, {"headline": "X", "source_class": "blog"})


def test_create_decision_defaults_technology_uuid_from_coverage():
    session = MagicMock()
    tech = uuid4()
    coverage = CoverageItem(
        id=uuid4(),
        headline="H",
        source_class="specialist",
        match_status="matched",
        technology_uuid=tech,
        packet_week=date(2026, 8, 24),
        sources=[],
    )
    decision = create_pipeline_decision(
        session,
        coverage,
        {"user_story": "As a buyer I can detect PFAS in the field.", "status": "hold"},
    )
    session.add.assert_called_once()
    assert decision.coverage_item_id == coverage.id
    assert decision.technology_uuid == tech
    assert decision.status == "hold"


def test_create_decision_rejects_unknown_status():
    session = MagicMock()
    coverage = CoverageItem(id=uuid4(), headline="H", source_class="specialist")
    with pytest.raises(ValueError, match="status"):
        create_pipeline_decision(session, coverage, {"user_story": "story", "status": "maybe"})


def test_apply_coverage_fields_ignores_unknown_keys():
    item = CoverageItem(headline="old", source_class="specialist", match_status="unmatched")
    apply_coverage_fields(item, {"headline": "new", "not_a_column": 1})
    assert item.headline == "new"


# ── API endpoint tests ──────────────────────────────────────────


def _session_cm(session):
    @contextmanager
    def _cm():
        yield session

    return _cm()


@pytest.fixture
def api_client():
    from fastapi.testclient import TestClient
    from src.api.main import app

    return TestClient(app)


def test_create_coverage_allows_null_technology_uuid(api_client):
    item = CoverageItem(
        id=uuid4(),
        headline="Unmatched find",
        source_class="newspaper_tv",
        match_status="unmatched",
        technology_uuid=None,
        packet_week=date(2026, 8, 24),
        sources=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    with patch("src.api.routes.coverage.upsert_coverage_item", return_value=(item, True)):
        with patch("src.api.routes.coverage.db.get_session", return_value=_session_cm(MagicMock())):
            response = api_client.post(
                "/api/coverage",
                json={
                    "headline": "Unmatched find",
                    "source_class": "newspaper_tv",
                    "packet_week": "2026-08-24",
                },
            )
    assert response.status_code == 201
    body = response.json()
    assert body["headline"] == "Unmatched find"
    assert body["technology_uuid"] is None
    assert body["match_status"] == "unmatched"


def test_upsert_batch_reports_created_and_updated(api_client):
    first = CoverageItem(
        id=uuid4(),
        headline="One",
        source_class="newspaper_tv",
        match_status="unmatched",
        packet_week=date(2026, 8, 24),
        sources=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    second = CoverageItem(
        id=uuid4(),
        headline="Two",
        source_class="specialist",
        match_status="unmatched",
        packet_week=date(2026, 8, 24),
        sources=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    calls = iter([(first, True), (second, False)])
    captured: list[dict] = []

    def fake_upsert(session, payload, auto_match=True):
        captured.append(payload)
        return next(calls)

    with patch("src.api.routes.coverage.upsert_coverage_item", side_effect=fake_upsert):
        with patch("src.api.routes.coverage.db.get_session", return_value=_session_cm(MagicMock())):
            response = api_client.post(
                "/api/coverage/upsert",
                json={
                    "packet_week": "2026-08-24",
                    "items": [
                        {"headline": "One", "source_class": "newspaper_tv"},
                        {"headline": "Two", "source_class": "specialist", "university": "stanford"},
                    ],
                },
            )
    assert response.status_code == 200
    body = response.json()
    assert body["created"] == 1
    assert body["updated"] == 1
    assert len(body["items"]) == 2
    assert body["items"][0]["created"] is True
    assert body["items"][1]["created"] is False
    assert captured[0]["packet_week"] == date(2026, 8, 24)
    assert captured[1]["packet_week"] == date(2026, 8, 24)


def test_upsert_rejects_missing_headline(api_client):
    response = api_client.post("/api/coverage/upsert", json={"source_class": "newspaper_tv"})
    assert response.status_code == 422


def test_create_and_patch_decision(api_client):
    coverage_id = uuid4()
    decision_id = uuid4()
    coverage = CoverageItem(
        id=coverage_id,
        headline="Find",
        source_class="specialist",
        match_status="unmatched",
        sources=[],
    )
    decision = PipelineDecision(
        id=decision_id,
        coverage_item_id=coverage_id,
        user_story="As a lab I can screen samples in minutes.",
        status="hold",
        blocker="Need independent replication",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = coverage

    with patch("src.api.routes.coverage.create_pipeline_decision", return_value=decision):
        with patch("src.api.routes.coverage.db.get_session", return_value=_session_cm(session)):
            created = api_client.post(
                f"/api/coverage/{coverage_id}/decisions",
                json={
                    "user_story": "As a lab I can screen samples in minutes.",
                    "status": "hold",
                    "blocker": "Need independent replication",
                },
            )
    assert created.status_code == 201
    assert created.json()["status"] == "hold"
    assert created.json()["coverage_item_id"] == str(coverage_id)

    session2 = MagicMock()
    session2.query.return_value.filter.return_value.first.return_value = decision
    with patch("src.api.routes.coverage.db.get_session", return_value=_session_cm(session2)):
        patched = api_client.patch(
            f"/api/pipeline-decisions/{decision_id}",
            json={"status": "proceed", "blocker": None},
        )
    assert patched.status_code == 200
    assert patched.json()["status"] == "proceed"


def test_list_coverage_returns_paginated_payload(api_client):
    item = CoverageItem(
        id=uuid4(),
        headline="Listed find",
        source_class="newspaper_tv",
        match_status="unmatched",
        packet_week=date(2026, 8, 24),
        sources=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    def query_side_effect(*args, **kwargs):
        q = MagicMock()
        q.filter.return_value = q
        q.outerjoin.return_value = q
        q.join.return_value = q
        q.group_by.return_value = q
        q.order_by.return_value = q
        q.offset.return_value = q
        q.limit.return_value = q
        q.subquery.return_value = MagicMock()
        model = args[0] if args else None
        if model is CoverageItem:
            q.count.return_value = 1
            q.all.return_value = [item]
        else:
            q.count.return_value = 0
            q.all.return_value = []
        return q

    session = MagicMock()
    session.query.side_effect = query_side_effect

    with patch("src.api.routes.coverage.db.get_session", return_value=_session_cm(session)):
        response = api_client.get("/api/coverage?packet_week=2026-08-24")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["headline"] == "Listed find"
    assert body["items"][0]["technology_uuid"] is None


def test_get_coverage_includes_decisions(api_client):
    coverage_id = uuid4()
    decision = PipelineDecision(
        id=uuid4(),
        coverage_item_id=coverage_id,
        user_story="As a buyer I can detect PFAS.",
        status="proceed",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    item = CoverageItem(
        id=coverage_id,
        headline="Find with decision",
        source_class="specialist",
        match_status="unmatched",
        sources=[],
        decisions=[decision],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = item
    with patch("src.api.routes.coverage.db.get_session", return_value=_session_cm(session)):
        response = api_client.get(f"/api/coverage/{coverage_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["headline"] == "Find with decision"
    assert body["decisions"][0]["status"] == "proceed"
    assert body["latest_decision"]["status"] == "proceed"


def test_patch_coverage_updates_summary(api_client):
    item = CoverageItem(
        id=uuid4(),
        headline="Original",
        source_class="newspaper_tv",
        match_status="unmatched",
        sources=[],
        summary="old",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = item
    with patch("src.api.routes.coverage.db.get_session", return_value=_session_cm(session)):
        response = api_client.patch(f"/api/coverage/{item.id}", json={"summary": "new blurb"})
    assert response.status_code == 200
    assert response.json()["summary"] == "new blurb"


def test_create_rejects_invalid_source_class(api_client):
    response = api_client.post(
        "/api/coverage",
        json={"headline": "X", "source_class": "blog"},
    )
    assert response.status_code == 422


def test_get_coverage_404(api_client):
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    with patch("src.api.routes.coverage.db.get_session", return_value=_session_cm(session)):
        response = api_client.get(f"/api/coverage/{uuid4()}")
    assert response.status_code == 404


def test_constants_match_live_check_constraints():
    assert SOURCE_CLASSES == ("newspaper_tv", "specialist")
    assert MATCH_STATUSES == ("matched", "unmatched", "candidate")
    assert DECISION_STATUSES == ("greenlit", "hold", "proceed", "archive", "dropped")
