from __future__ import annotations

from urllib.parse import quote_plus

import scrapy

from pipeline.spiders.base import BaseJobSpider
from src.config import get_settings


class IndeedSpider(BaseJobSpider):
    name = "indeed"
    source_name = "indeed"

    def start_requests_compat(self):
        settings = get_settings()
        role = quote_plus(self.role)
        for page in range(settings.max_pages):
            start = page * 10
            url = f"https://in.indeed.com/jobs?q={role}&l=India&fromage=7&start={start}"
            yield scrapy.Request(url=url, callback=self.parse_search)

    def parse_search(self, response):
        if "Security Check - Indeed.com" in response.text:
            self.logger.warning("Indeed blocked crawl with security page", extra={"url": response.url})
            return
        cards = response.css("div.job_seen_beacon")
        self.fetched_count += len(cards)
        for card in cards:
            href = card.css("h2 a::attr(href)").get()
            if not href:
                continue
            url = self.clean_url(response, href)
            meta = {
                "title": card.css("h2 a span::text").get(default="").strip(),
                "company": card.css("span.companyName::text").get(default="").strip(),
                "location": card.css("div.companyLocation::text").get(default="").strip(),
                "posted_at": card.css("span.date::text").get(default="").strip() or None,
            }
            yield response.follow(url, callback=self.parse_job, meta=meta)

    def parse_job(self, response):
        description = self.extract_all_text(response, "#jobDescriptionText *::text")
        yield self.build_item(
            title=response.meta.get("title", ""),
            company=response.meta.get("company", ""),
            url=response.url,
            description=description,
            location=response.meta.get("location", ""),
            posted_at=response.meta.get("posted_at"),
        )
