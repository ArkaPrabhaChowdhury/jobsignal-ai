from __future__ import annotations

import json
from datetime import UTC, datetime

from pipeline.spiders.base import BaseJobSpider


class JsonJobSpider(BaseJobSpider):
    """Shared parsing helpers for public job feeds and ATS APIs."""

    def decode_json(self, response):
        try:
            return json.loads(response.text)
        except json.JSONDecodeError as exc:
            self.logger.error("invalid_json", url=response.url, error=str(exc))
            return None

    def unix_timestamp(self, value) -> str | None:
        if value in (None, ""):
            return None
        try:
            timestamp = float(value)
            if timestamp > 10_000_000_000:
                timestamp /= 1000
            return datetime.fromtimestamp(timestamp, tz=UTC).isoformat()
        except (TypeError, ValueError, OSError):
            return str(value)

    def comma_values(self, value: str | None, defaults: tuple[str, ...]) -> list[str]:
        if not value:
            return list(defaults)
        return [part.strip() for part in value.split(",") if part.strip()]
