from __future__ import annotations

import scrapy
from scrapy_playwright.page import PageMethod

from pipeline.spiders.base import BaseJobSpider


class GreenhousePlaywrightSpider(BaseJobSpider):
    """Portfolio spider demonstrating browser-rendered extraction with Playwright."""

    name = "greenhouse_playwright"
    source_name = "greenhouse_playwright"
    board_url = "https://job-boards.greenhouse.io/stablekernel"
    custom_settings = {
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "PLAYWRIGHT_MAX_PAGES_PER_CONTEXT": 2,
    }

    def __init__(self, board_url: str | None = None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if board_url:
            self.board_url = board_url

    def start_requests_compat(self):
        yield scrapy.Request(
            url=self.board_url,
            callback=self.parse_rendered_board,
            meta={
                "playwright": True,
                "playwright_page_methods": [
                    PageMethod("wait_for_load_state", "domcontentloaded"),
                    PageMethod(
                        "evaluate",
                        """
                        role => {
                          const input = document.querySelector(
                            'input[type="search"], input[placeholder*="Search"]'
                          );
                          if (!input) return;
                          input.value = role;
                          input.dispatchEvent(new Event("input", {bubbles: true}));
                        }
                        """,
                        self.role,
                    ),
                    PageMethod("wait_for_timeout", 500),
                ],
            },
        )

    def parse_rendered_board(self, response):
        seen: set[str] = set()
        for link in response.css('a[href*="/jobs/"]'):
            title = " ".join(link.css("::text").getall()).strip()
            href = link.attrib.get("href")
            if not href or not self.matches_role(title):
                continue
            job_url = response.urljoin(href)
            if job_url in seen:
                continue
            seen.add(job_url)
            yield scrapy.Request(
                url=job_url,
                callback=self.parse_rendered_job,
                meta={"playwright": True},
            )

    def parse_rendered_job(self, response):
        posting = self.extract_job_posting_json_ld(response)
        title = posting.get("title") or self.extract_text(
            response,
            ["h1::text", ".job__title::text"],
        )
        description = self.clean_html_text(posting.get("description", ""))
        if not description:
            description = self.extract_all_text(
                response,
                "#content *::text, .job__description *::text",
            )
        company = self.extract_company(posting.get("hiringOrganization"))
        location = self.extract_location(posting.get("jobLocation")) or self.extract_text(
            response,
            [".location::text", ".job__location::text"],
        )

        if not self.matches_role(title, description):
            return

        self.fetched_count += 1
        yield self.build_item(
            title=title,
            company=company,
            url=response.url,
            description=description,
            location=location or "Remote",
            posted_at=posting.get("datePosted"),
        )
