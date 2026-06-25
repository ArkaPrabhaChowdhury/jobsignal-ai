from __future__ import annotations

import scrapy

from pipeline.spiders.api_base import JsonJobSpider


class GreenhouseSpider(JsonJobSpider):
    name = "greenhouse"
    source_name = "greenhouse"
    endpoint = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
    default_boards = ("airbnb", "stripe")

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
            description = self.clean_html_text(job.get("content", ""))
            if not self.matches_role(title, description):
                continue
            self.fetched_count += 1
            yield self.build_item(
                title=title,
                company=job.get("company_name") or board.replace("-", " ").title(),
                url=job.get("absolute_url", ""),
                description=description,
                location=(job.get("location") or {}).get("name", "Unknown"),
                posted_at=job.get("first_published") or job.get("updated_at"),
            )
