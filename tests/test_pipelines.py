from __future__ import annotations

from dataclasses import dataclass

import pytest
from scrapy.exceptions import DropItem

from pipeline.items import JobItem
from pipeline.pipelines import EmbedPipeline, EnrichPipeline, StorePipeline, ValidatePipeline
from src.run_log import RunLogStore


@dataclass
class StubRunLog:
    skipped_dedup: int = 0
    skipped_low_confidence: int = 0
    stored: int = 0
    fetched: int = 0
    errors: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class StubSpider:
    name = "indeed"
    fetched_count = 0

    def __init__(self):
        self.run_log = StubRunLog()


class StubDatabase:
    def __init__(self, exists_result: bool = False, insert_result: bool = True) -> None:
        self.exists_result = exists_result
        self.insert_result = insert_result
        self.saved = []

    def exists(self, listing_id: str) -> bool:
        del listing_id
        return self.exists_result

    def upsert_listing(self, listing):
        self.saved.append(listing)
        return self.insert_result


class StubEnricher:
    def __init__(self, skills=None, confidence=0.9, error: Exception | None = None) -> None:
        self.skills = skills or ["Python", "FastAPI"]
        self.confidence = confidence
        self.error = error

    def enrich_listing(self, description: str):
        del description
        if self.error:
            raise self.error
        return self.skills, self.confidence


class StubEmbedder:
    def embed_text(self, text: str):
        del text
        return [0.1, 0.2, 0.3]


def test_validate_pipeline_generates_id_and_normalizes_location():
    spider = StubSpider()
    pipeline = ValidatePipeline(database=StubDatabase(exists_result=False))
    item = JobItem(
        title="Backend Engineer",
        company="Acme",
        url="https://example.com/jobs/1",
        description="Python services",
        location="  Bengaluru   India ",
        source="indeed",
    )

    result = pipeline.process_item(item, spider)

    assert result.id
    assert result.location == "Bengaluru India"


def test_validate_pipeline_drops_duplicates():
    spider = StubSpider()
    pipeline = ValidatePipeline(database=StubDatabase(exists_result=True))
    item = JobItem(
        title="Backend Engineer",
        company="Acme",
        url="https://example.com/jobs/1",
        description="Python services",
        location="Remote",
        source="indeed",
    )

    with pytest.raises(DropItem):
        pipeline.process_item(item, spider)

    assert spider.run_log.skipped_dedup == 1


def test_enrich_pipeline_drops_low_confidence():
    spider = StubSpider()
    item = JobItem(id="abc", description="marketing role")
    pipeline = EnrichPipeline(enricher=StubEnricher(confidence=0.2))

    with pytest.raises(DropItem):
        pipeline.process_item(item, spider)

    assert spider.run_log.skipped_low_confidence == 1


def test_embed_and_store_pipelines_persist_listing(tmp_path):
    spider = StubSpider()
    store_pipeline = StorePipeline(
        database=StubDatabase(insert_result=True),
        run_log_store=RunLogStore(db_path=str(tmp_path / "run_logs.db")),
    )
    item = JobItem(
        id="abc",
        title="AI Engineer",
        company="Acme",
        url="https://example.com/jobs/1",
        description="Python LLM systems",
        location="Remote",
        source="ddg",
        skills=["Python"],
        confidence=0.9,
    )

    store_pipeline.open_spider(spider)
    embedded = EmbedPipeline(embedder=StubEmbedder()).process_item(item, spider)
    stored = store_pipeline.process_item(embedded, spider)
    store_pipeline.close_spider(spider)

    assert stored.embedding == [0.1, 0.2, 0.3]
    assert spider.run_log.stored == 1
