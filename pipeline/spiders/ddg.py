from __future__ import annotations

from urllib.parse import quote_plus

import scrapy

from pipeline.spiders.base import BaseJobSpider


class DDGSpider(BaseJobSpider):
    name = "ddg"
    source_name = "ddg"

    def start_requests_compat(self):
        query = quote_plus(f"site:linkedin.com/jobs OR site:cutshort.io {self.role}")
        url = f"https://duckduckgo.com/html/?q={query}"
        yield scrapy.Request(url=url, callback=self.parse_search)

    def parse_search(self, response):
        results = response.css("a.result__a")
        self.fetched_count += len(results)
        for result in results:
            url = result.css("::attr(href)").get()
            title = result.css("::text").get(default="").strip()
            if not url:
                continue
            yield scrapy.Request(
                url=url,
                callback=self.parse_job,
                meta={"search_title": title},
                dont_filter=True,
            )

    def parse_job(self, response):
        description = self.extract_all_text(response, "body *::text")[:4000]
        yield self.build_item(
            title=response.meta.get("search_title", "") or response.css("title::text").get(default="").strip(),
            company=response.url.split("/")[2],
            url=response.url,
            description=description,
            location="Unknown",
        )
