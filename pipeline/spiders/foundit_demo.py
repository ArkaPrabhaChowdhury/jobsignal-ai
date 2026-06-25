from __future__ import annotations

import json
import re
from urllib.parse import urlencode

import scrapy

from pipeline.spiders.base import BaseJobSpider
from src.config import get_settings


class FounditDemoSpider(BaseJobSpider):
    name = "foundit_demo"
    source_name = "foundit_demo"
    search_url = "https://www.foundit.in/srp/results"
    middleware_url = "https://www.foundit.in/middleware/jobsearch"
    custom_settings = {
        "ROBOTSTXT_OBEY": False,
    }

    def start_requests_compat(self):
        params = {"query": self.role, "locations": "India"}
        url = f"{self.search_url}?{urlencode(params)}"
        yield scrapy.Request(url=url, callback=self.parse_search_page)

    def parse_search_page(self, response):
        settings = get_settings()
        seo_props = self._extract_window_json(response.text, "_seoHtmlProps_")
        if not seo_props:
            return

        limit = int(seo_props.get("limit", 25))
        for page in range(settings.max_pages):
            start = page * limit
            params = {
                "query": seo_props.get("query", self.role),
                "locations": seo_props.get("locations", "India"),
                "start": start,
                "limit": limit,
            }
            headers = {
                "Accept": "application/json, text/plain, */*",
                "Referer": response.url,
            }
            url = f"{self.middleware_url}?{urlencode(params)}"
            yield scrapy.Request(url=url, callback=self.parse_search_results, headers=headers)

    def parse_search_results(self, response):
        payload = json.loads(response.text)
        jobs = payload.get("jobSearchResponse", {}).get("data", [])
        for job in jobs:
            if job.get("type"):
                continue
            title = job.get("title", "")
            description = job.get("jobDescription", "") or job.get("summary", "")
            skills = job.get("skills", "")
            if not self.matches_role(title, description, skills):
                continue

            self.fetched_count += 1
            seo_url = job.get("seoJdUrl")
            if seo_url:
                job_url = response.urljoin(seo_url)
            else:
                slug = self._slugify_title(title)
                job_url = f"https://www.foundit.in/job/{slug}-{job.get('id')}"

            yield scrapy.Request(
                url=job_url,
                callback=self.parse_job,
                meta={"search_job": job},
            )

    def parse_job(self, response):
        posting = self.extract_job_posting_json_ld(response)
        search_job = response.meta.get("search_job", {})
        title = posting.get("title") or search_job.get("title", "")
        description = self.clean_html_text(posting.get("description", ""))
        if not description:
            description = search_job.get("jobDescription", "") or search_job.get("summary", "")
        company = self.extract_company(posting.get("hiringOrganization")) or search_job.get(
            "companyName", ""
        )
        location = self.extract_location(posting.get("jobLocation")) or search_job.get(
            "locations", ""
        )
        posted_at = posting.get("datePosted") or search_job.get("updatedAt") or search_job.get("postedAt")

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

    def _extract_window_json(self, html: str, variable_name: str) -> dict:
        match = re.search(rf"var\s+{re.escape(variable_name)}\s*=\s*(\{{.*?\}})", html, re.S)
        if not match:
            return {}
        return json.loads(match.group(1))

    def _slugify_title(self, title: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        return slug or "job"
