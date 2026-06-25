from __future__ import annotations

from urllib.parse import urlencode

import scrapy

from pipeline.spiders.api_base import JsonJobSpider
from src.config import get_settings


class HimalayasSpider(JsonJobSpider):
    name = "himalayas"
    source_name = "himalayas"
    endpoint = "https://himalayas.app/jobs/api"
    page_size = 20

    def start_requests_compat(self):
        params = {"limit": self.page_size, "offset": 0}
        yield scrapy.Request(
            f"{self.endpoint}?{urlencode(params)}",
            callback=self.parse_page,
            cb_kwargs={"page": 0},
        )

    def parse_page(self, response, page: int):
        payload = self.decode_json(response) or {}
        for job in payload.get("jobs", []):
            title = job.get("title", "")
            description = self.clean_html_text(job.get("description", ""))
            if not self.matches_role(title, description, " ".join(job.get("categories", []))):
                continue
            self.fetched_count += 1
            location = ", ".join(job.get("locationRestrictions", [])) or "Remote"
            yield self.build_item(
                title=title,
                company=job.get("companyName", ""),
                url=job.get("applicationLink") or job.get("guid", ""),
                description=description,
                location=location,
                posted_at=self.unix_timestamp(job.get("pubDate")),
            )

        next_page = page + 1
        if next_page >= get_settings().max_pages:
            return
        offset = next_page * self.page_size
        if offset >= int(payload.get("totalCount", 0)):
            return
        params = {"limit": self.page_size, "offset": offset}
        yield scrapy.Request(
            f"{self.endpoint}?{urlencode(params)}",
            callback=self.parse_page,
            cb_kwargs={"page": next_page},
        )
