from __future__ import annotations

import json
import re
from html import unescape
from urllib.parse import urljoin

import scrapy
from scrapy import Selector

from pipeline.items import JobItem


class BaseJobSpider(scrapy.Spider):
    role: str = "software engineer"
    source_name: str = "base"

    def __init__(self, role: str | None = None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if role:
            self.role = role
        self.fetched_count = 0

    async def start(self):
        for request in self.start_requests_compat():
            yield request

    def start_requests_compat(self):
        raise NotImplementedError

    def extract_text(self, response, selectors: list[str]) -> str:
        for selector in selectors:
            value = response.css(selector).get()
            if value:
                return " ".join(value.split())
        return ""

    def extract_all_text(self, response, selector: str) -> str:
        values = response.css(selector).getall()
        return " ".join(" ".join(value.split()) for value in values if value).strip()

    def clean_url(self, response, href: str) -> str:
        return urljoin(response.url, href)

    def normalize_text(self, value: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()

    def matches_role(self, *parts: str) -> bool:
        primary = self.normalize_text(parts[0]) if parts else ""
        if not primary:
            return False

        role = self.normalize_text(self.role)
        if role and role in primary:
            return True

        tokens = [token for token in role.split() if len(token) >= 2]
        return bool(tokens) and all(token in primary for token in tokens)

    def clean_html_text(self, value: str) -> str:
        text = re.sub(r"<[^>]+>", " ", unescape(value or ""))
        return re.sub(r"\s+", " ", text).strip()

    def iter_sitemap_urls(self, response) -> list[str]:
        selector = Selector(text=response.text, type="xml")
        return selector.xpath("//*[local-name()='loc']/text()").getall()

    def extract_json_ld_blocks(self, response) -> list[dict]:
        blocks: list[dict] = []
        for raw in response.css('script[type="application/ld+json"]::text').getall():
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(data, list):
                blocks.extend(item for item in data if isinstance(item, dict))
            elif isinstance(data, dict):
                blocks.append(data)
        return blocks

    def extract_job_posting_json_ld(self, response) -> dict:
        for block in self.extract_json_ld_blocks(response):
            if block.get("@type") == "JobPosting":
                return block
        return {}

    def extract_location(self, location_value) -> str:
        if isinstance(location_value, list):
            parts = [self.extract_location(item) for item in location_value]
            return ", ".join(part for part in parts if part)
        if isinstance(location_value, dict):
            address = location_value.get("address", {})
            if isinstance(address, list):
                parts = [self.extract_location(item) for item in address]
                return ", ".join(part for part in parts if part)
            if isinstance(address, dict):
                return (
                    address.get("addressLocality")
                    or address.get("streetAddress")
                    or address.get("addressRegion")
                    or ""
                )
        return ""

    def extract_company(self, organization_value) -> str:
        if isinstance(organization_value, list):
            for item in organization_value:
                company = self.extract_company(item)
                if company:
                    return company
            return ""
        if isinstance(organization_value, dict):
            return organization_value.get("name", "")
        return str(organization_value or "")

    def build_item(
        self,
        *,
        title: str,
        company: str,
        url: str,
        description: str,
        location: str,
        posted_at: str | None = None,
    ) -> JobItem:
        return JobItem(
            title=title,
            company=company,
            url=url,
            description=description,
            location=location,
            posted_at=posted_at,
            source=self.source_name,
        )
