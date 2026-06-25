from __future__ import annotations

import scrapy

from pipeline.spiders.base import BaseJobSpider
from src.config import get_settings


class ForageAISpider(BaseJobSpider):
    """Direct HTML scraper demonstrating discovery and resilient detail parsing."""

    name = "forage_ai"
    source_name = "forage_ai"
    sitemap_url = "https://forage.ai/job-opportunities-sitemap.xml"
    allowed_domains = ["forage.ai"]

    def start_requests_compat(self):
        yield scrapy.Request(self.sitemap_url, callback=self.parse_sitemap)

    def parse_sitemap(self, response):
        limit = max(get_settings().max_pages * 10, 10)
        scheduled = 0
        for url in reversed(self.iter_sitemap_urls(response)):
            if "/job-opportunities/" not in url:
                continue
            yield scrapy.Request(url, callback=self.parse_job)
            scheduled += 1
            if scheduled >= limit:
                break

    def parse_job(self, response):
        posting = self.extract_job_posting_json_ld(response)
        title = posting.get("title") or self.extract_text(
            response,
            ["main h1::text", "article h1::text", "h1::text"],
        )
        description = self.clean_html_text(posting.get("description", ""))
        if not description:
            content = response.css(".content-wrapper")
            values = content.xpath(
                ".//text()[not(ancestor::style) and not(ancestor::script)]"
            ).getall()
            description = " ".join(" ".join(value.split()) for value in values if value).strip()
        if not description:
            description = self.extract_all_text(
                response, "main p::text, main li::text, article p::text, article li::text"
            )
        company = self.extract_company(posting.get("hiringOrganization")) or "Forage AI"
        location = self.extract_location(posting.get("jobLocation"))
        if not location:
            location = self.extract_text(
                response,
                ["[class*='location']::text", "[class*='remote']::text"],
            )
        if len(description) < 100 or not self.matches_role(title, description):
            return
        self.fetched_count += 1
        published_at = posting.get("datePosted")
        if not published_at:
            for block in self.extract_json_ld_blocks(response):
                graph = block.get("@graph", [])
                if not isinstance(graph, list):
                    continue
                page = next(
                    (
                        entity
                        for entity in graph
                        if isinstance(entity, dict) and entity.get("@type") == "WebPage"
                    ),
                    {},
                )
                published_at = page.get("datePublished")
                if published_at:
                    break
        yield self.build_item(
            title=title,
            company=company,
            url=response.url,
            description=description,
            location=location or "Remote",
            posted_at=published_at,
        )
