from __future__ import annotations

import scrapy

from pipeline.spiders.base import BaseJobSpider
from src.config import get_settings


class FounditSpider(BaseJobSpider):
    name = "foundit"
    source_name = "foundit"
    sitemap_url = "https://www.foundit.in/xmlsitemap/todays-jobs-sitemap.xml"

    def start_requests_compat(self):
        yield scrapy.Request(url=self.sitemap_url, callback=self.parse_sitemap)

    def parse_sitemap(self, response):
        settings = get_settings()
        limit = max(settings.max_pages * 10, 10)
        scheduled = 0
        for url in self.iter_sitemap_urls(response):
            if not self.matches_role(url):
                continue
            scheduled += 1
            yield scrapy.Request(url=url, callback=self.parse_job)
            if scheduled >= limit:
                break

    def parse_job(self, response):
        posting = self.extract_job_posting_json_ld(response)
        title = posting.get("title") or response.css("h1::text").get(default="").strip()
        description = self.clean_html_text(posting.get("description", ""))
        company = self.extract_company(posting.get("hiringOrganization")) or self.extract_text(
            response, ["[data-testid='company-name']::text", "h2::text"]
        )
        location = self.extract_location(posting.get("jobLocation")) or self.extract_text(
            response, ["[data-testid='job-location']::text"]
        )
        posted_at = posting.get("datePosted")

        if not self.matches_role(title, description, response.url):
            return

        self.fetched_count += 1
        yield self.build_item(
            title=title,
            company=company,
            url=response.url,
            description=description,
            location=location or "India",
            posted_at=posted_at,
        )
