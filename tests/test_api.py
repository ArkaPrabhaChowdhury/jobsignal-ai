from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from api import app
from src.models import ListingPreview, RunLog


class StubDatabase:
    def ensure_schema(self) -> None:
        return None

    def ping(self) -> bool:
        return True

    def stats(self) -> dict:
        return {
            "total_listings": 24,
            "by_source": {"foundit_demo": 24},
            "top_skills": [{"skill": "Python", "count": 5}],
        }

    def recent_listings(self, limit: int = 12) -> list[ListingPreview]:
        del limit
        return [
            ListingPreview(
                id="job-1",
                title="Software Engineer",
                company="Acme",
                url="https://example.com/job-1",
                location="Hyderabad",
                source="foundit_demo",
                posted_at="2026-06-23",
                skills=["Python", "Docker"],
                confidence=0.81,
                ingested_at=datetime.now(UTC),
            )
        ]


class StubRunLogStore:
    def last_runs(self, limit: int = 5) -> list[RunLog]:
        del limit
        return [
            RunLog(
                run_id="run-1",
                started_at=datetime.now(UTC),
                source="foundit_demo",
                fetched=25,
                stored=24,
                skipped_dedup=0,
                skipped_low_confidence=1,
                errors=[],
            )
        ]


class StubRagService:
    def query(self, question: str):
        return f"Answer for: {question}", ["https://example.com/job-1"]


class FailingHealthDatabase(StubDatabase):
    def ping(self) -> bool:
        raise RuntimeError("db down")


def test_landing_page_renders_dashboard():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "JobSignal AI" in response.text
    assert "foundit_demo" in response.text


def test_static_favicon_is_served():
    client = TestClient(app)

    response = client.get("/static/favicon.svg")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")


def test_stats_endpoint_returns_summary(monkeypatch):
    monkeypatch.setattr("api.Database", lambda: StubDatabase())
    monkeypatch.setattr("api.RunLogStore", lambda: StubRunLogStore())
    client = TestClient(app)

    response = client.get("/stats")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_listings"] == 24
    assert payload["by_source"]["foundit_demo"] == 24
    assert payload["last_5_runs"][0]["stored"] == 24


def test_recent_listings_endpoint_returns_preview(monkeypatch):
    monkeypatch.setattr("api.Database", lambda: StubDatabase())
    client = TestClient(app)

    response = client.get("/listings/recent?limit=4")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["title"] == "Software Engineer"
    assert payload[0]["source"] == "foundit_demo"


def test_query_endpoint_uses_rag_service(monkeypatch):
    monkeypatch.setattr("api.Database", lambda: StubDatabase())
    monkeypatch.setattr("api.RagService", lambda: StubRagService())
    client = TestClient(app)

    response = client.get("/query", params={"q": "What skills matter?"})

    assert response.status_code == 200
    payload = response.json()
    assert "What skills matter?" in payload["answer"]
    assert payload["sources"] == ["https://example.com/job-1"]


def test_health_endpoint_reports_ok(monkeypatch):
    monkeypatch.setattr("api.Database", lambda: StubDatabase())
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["database"] == "reachable"


def test_health_endpoint_reports_degraded(monkeypatch):
    monkeypatch.setattr("api.Database", lambda: FailingHealthDatabase())
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"


def test_ingest_endpoint_starts_when_enabled(monkeypatch):
    monkeypatch.setattr("api.get_settings", lambda: type("S", (), {"public_ingest_enabled": True})())
    client = TestClient(app)

    response = client.post("/ingest", json={"role": "software engineer", "sources": ["foundit_demo"]})

    assert response.status_code == 200
    assert response.json()["status"] == "started"


def test_ingest_endpoint_blocks_when_disabled(monkeypatch):
    monkeypatch.setattr("api.get_settings", lambda: type("S", (), {"public_ingest_enabled": False})())
    client = TestClient(app)

    response = client.post("/ingest", json={"role": "software engineer", "sources": ["foundit_demo"]})

    assert response.status_code == 403
    assert response.json()["status"] == "disabled"
