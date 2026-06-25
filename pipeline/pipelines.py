from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import asdict
from datetime import UTC, datetime

from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem

from src.config import get_settings
from src.database import Database
from src.embedder import get_embedder
from src.enricher import GroqEnricher
from src.logger import get_logger
from src.models import JobListing, RunLog
from src.run_log import RunLogStore


def _normalize_location(value: str) -> str:
    return " ".join((value or "").split())


class PipelineMixin:
    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)

    def _log_stage(self, stage: str, item_id: str, started_at: float, **extra) -> None:
        self.logger.info(
            "pipeline_stage",
            stage=stage,
            item_id=item_id,
            duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
            **extra,
        )


class ValidatePipeline(PipelineMixin):
    def __init__(self, database: Database | None = None) -> None:
        super().__init__()
        self.database = database or Database()

    def process_item(self, item, spider):
        started_at = time.perf_counter()
        adapter = ItemAdapter(item)
        for field in ("title", "company", "description"):
            if not str(adapter.get(field, "")).strip():
                raise DropItem(f"missing required field: {field}")

        adapter["location"] = _normalize_location(adapter.get("location", "Unknown")) or "Unknown"
        digest = hashlib.sha256(f"{adapter.get('source', spider.name)}:{adapter.get('url', '')}".encode("utf-8"))
        adapter["id"] = digest.hexdigest()

        if self.database.exists(adapter["id"]):
            spider.run_log.skipped_dedup += 1
            raise DropItem(f"duplicate listing: {adapter['id']}")

        self._log_stage("validate", adapter["id"], started_at)
        return item


class EnrichPipeline(PipelineMixin):
    def __init__(self, enricher: GroqEnricher | None = None) -> None:
        super().__init__()
        self.settings = get_settings()
        self.enricher = enricher or GroqEnricher()

    def process_item(self, item, spider):
        started_at = time.perf_counter()
        adapter = ItemAdapter(item)
        try:
            skills, confidence = self.enricher.enrich_listing(adapter["description"])
            adapter["skills"] = skills
            adapter["confidence"] = confidence
        except Exception as exc:
            spider.run_log.errors.append(f"enrich:{adapter.get('url', '')}:{exc}")
            adapter["skills"] = []
            adapter["confidence"] = 0.0

        if float(adapter.get("confidence", 0.0)) < self.settings.min_confidence:
            spider.run_log.skipped_low_confidence += 1
            raise DropItem(f"low confidence listing: {adapter.get('id', 'unknown')}")

        self._log_stage("enrich", adapter["id"], started_at, confidence=adapter["confidence"])
        return item


class EmbedPipeline(PipelineMixin):
    def __init__(self, embedder=None) -> None:
        super().__init__()
        self.embedder = embedder or get_embedder()

    def process_item(self, item, spider):
        started_at = time.perf_counter()
        adapter = ItemAdapter(item)
        text = f"{adapter.get('title', '')} {adapter.get('company', '')} {adapter.get('description', '')[:400]}"
        adapter["embedding"] = self.embedder.embed_text(text)
        self._log_stage("embed", adapter["id"], started_at)
        return item


class StorePipeline(PipelineMixin):
    def __init__(
        self,
        database: Database | None = None,
        run_log_store: RunLogStore | None = None,
    ) -> None:
        super().__init__()
        self.database = database or Database()
        self.run_log_store = run_log_store or RunLogStore()

    def open_spider(self, spider) -> None:
        run_id = getattr(spider, "run_id", str(uuid.uuid4()))
        spider.run_id = run_id
        spider.run_log = RunLog(
            run_id=run_id,
            started_at=datetime.now(UTC),
            source=spider.name,
        )

    def close_spider(self, spider) -> None:
        if hasattr(spider, "fetched_count"):
            spider.run_log.fetched = spider.fetched_count
        self.run_log_store.write(spider.run_log)

    def process_item(self, item, spider):
        started_at = time.perf_counter()
        adapter = ItemAdapter(item)
        listing = JobListing(**asdict(item) if hasattr(item, "__dataclass_fields__") else dict(adapter))
        inserted = self.database.upsert_listing(listing)
        if inserted:
            spider.run_log.stored += 1
        else:
            spider.run_log.skipped_dedup += 1
        self._log_stage("store", adapter["id"], started_at, inserted=inserted)
        return item
