from __future__ import annotations

import scrapy

from pipeline.spiders.api_base import JsonJobSpider


class AshbySpider(JsonJobSpider):
    name = "ashby"
    source_name = "ashby"
    endpoint = (
        "https://api.ashbyhq.com/posting-api/job-board/"
        "{board}?includeCompensation=true"
    )
    default_boards = ("ashby",)

    def __init__(self, boards: str | None = None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.boards = self.comma_values(boards, self.default_boards)

    def start_requests_compat(self):
        for board in self.boards:
            yield scrapy.Request(
                self.endpoint.format(board=board),
                callback=self.parse_board,
                cb_kwargs={"board": board},
            )

    def parse_board(self, response, board: str):
        payload = self.decode_json(response) or {}
        for job in payload.get("jobs", []):
            title = job.get("title", "")
            description = self.clean_html_text(
                job.get("descriptionHtml") or job.get("descriptionPlain", "")
            )
            if not self.matches_role(title, description):
                continue
            self.fetched_count += 1
            location = job.get("location", "")
            if job.get("isRemote") and "remote" not in location.lower():
                location = f"{location}, Remote".strip(", ")
            yield self.build_item(
                title=title,
                company=board.replace("-", " ").title(),
                url=job.get("jobUrl") or job.get("applyUrl", ""),
                description=description,
                location=location or "Unknown",
                posted_at=job.get("publishedAt"),
            )
