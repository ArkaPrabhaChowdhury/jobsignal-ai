from __future__ import annotations

import scrapy

from pipeline.spiders.base import BaseJobSpider
from src.config import get_settings


class CutshortSpider(BaseJobSpider):
    name = "cutshort"
    source_name = "cutshort"
    sitemap_url = "https://cutshort.io/sitemap_jobs.xml"

    def start_requests_compat(self):
        yield scrapy.Request(url=self.sitemap_url, callback=self.parse_sitemap)

    def parse_sitemap(self, response):
        settings = get_settings()
        limit = max(settings.max_pages * 10, 10)
        seen = set()
        scheduled = 0
        for url in self.iter_sitemap_urls(response):
            if url in seen or not self.matches_role(url):
                continue
            seen.add(url)
            scheduled += 1
            yield scrapy.Request(url=url, callback=self.parse_job)
            if scheduled >= limit:
                break

    def parse_job(self, response):
        self.fetched_count += 1
        posting = self.extract_job_posting_json_ld(response)
        title = posting.get("title") or response.css("h1::text").get(default="").strip().rstrip(",")
        company = self.extract_company(posting.get("hiringOrganization")) or response.css(
            "h2::text"
        ).get(default="").replace("at ", "").strip()
        location = self.extract_location(posting.get("jobLocation"))
        description = self.clean_html_text(posting.get("description", ""))
        posted_at = posting.get("datePosted")

        if not self.matches_role(title, description, response.url):
            return

        yield self.build_item(
            title=title,
            company=company,
            url=response.url,
            description=description,
            location=location or "India",
            posted_at=posted_at,
        )
