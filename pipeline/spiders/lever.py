from __future__ import annotations

import scrapy

from pipeline.spiders.api_base import JsonJobSpider


class LeverSpider(JsonJobSpider):
    name = "lever"
    source_name = "lever"
    endpoint = "https://api.lever.co/v0/postings/{company}?mode=json"
    default_companies = ("palantir",)

    def __init__(self, companies: str | None = None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.companies = self.comma_values(companies, self.default_companies)

    def start_requests_compat(self):
        for company in self.companies:
            yield scrapy.Request(
                self.endpoint.format(company=company),
                callback=self.parse_company,
                cb_kwargs={"company": company},
            )

    def parse_company(self, response, company: str):
        for job in self.decode_json(response) or []:
            description = " ".join(
                part
                for part in (
                    job.get("openingPlain"),
                    job.get("descriptionPlain"),
                    " ".join(item.get("content", "") for item in job.get("lists", [])),
                    job.get("additionalPlain"),
                )
                if part
            )
            title = job.get("text", "")
            if not self.matches_role(title, description):
                continue
            self.fetched_count += 1
            categories = job.get("categories") or {}
            yield self.build_item(
                title=title,
                company=company.replace("-", " ").title(),
                url=job.get("hostedUrl", ""),
                description=self.clean_html_text(description),
                location=categories.get("location", "Unknown"),
                posted_at=self.unix_timestamp(job.get("createdAt")),
            )
