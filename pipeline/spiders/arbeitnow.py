from __future__ import annotations

from urllib.parse import urlencode

import scrapy

from pipeline.spiders.api_base import JsonJobSpider
from src.config import get_settings


class ArbeitnowSpider(JsonJobSpider):
    name = "arbeitnow"
    source_name = "arbeitnow"
    endpoint = "https://www.arbeitnow.com/api/job-board-api"

    def start_requests_compat(self):
        params = {"search": self.role, "page": 1}
        yield scrapy.Request(
            f"{self.endpoint}?{urlencode(params)}",
            callback=self.parse_page,
            cb_kwargs={"page": 1},
        )

    def parse_page(self, response, page: int):
        payload = self.decode_json(response) or {}
        for job in payload.get("data", []):
            title = job.get("title", "")
            description = self.clean_html_text(job.get("description", ""))
            if not self.matches_role(title, description, " ".join(job.get("tags", []))):
                continue
            self.fetched_count += 1
            yield self.build_item(
                title=title,
                company=job.get("company_name", ""),
                url=job.get("url", ""),
                description=description,
                location=job.get("location") or ("Remote" if job.get("remote") else "Unknown"),
                posted_at=self.unix_timestamp(job.get("created_at")),
            )

        next_url = (payload.get("links") or {}).get("next")
        if next_url and page < get_settings().max_pages:
            yield scrapy.Request(
                next_url,
                callback=self.parse_page,
                cb_kwargs={"page": page + 1},
            )
