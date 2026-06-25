from __future__ import annotations

from scrapy.http import TextResponse

from pipeline.spiders.base import BaseJobSpider
from pipeline.spiders.greenhouse import GreenhouseSpider
from pipeline.spiders.lever import LeverSpider


class StubSpider(BaseJobSpider):
    name = "stub"

    def start_requests_compat(self):
        return []


def test_matches_role_uses_phrase_or_tokens():
    spider = StubSpider(role="software engineer")

    assert spider.matches_role("Senior Software Engineer")
    assert spider.matches_role("platform software role for engineer")
    assert not spider.matches_role("data analyst")
    assert not spider.matches_role(
        "Product Manager",
        "Work with software teams and engineering stakeholders",
    )


def test_clean_html_text_strips_tags():
    spider = StubSpider()

    assert spider.clean_html_text("<p>Hello <strong>World</strong></p>") == "Hello World"


def test_extract_job_posting_json_ld():
    spider = StubSpider()
    html = """
    <html>
      <body>
        <script type="application/ld+json">
          {"@context":"https://schema.org","@type":"JobPosting","title":"Backend Engineer","description":"<p>Python</p>"}
        </script>
      </body>
    </html>
    """
    response = TextResponse(url="https://example.com/job", body=html, encoding="utf-8")

    posting = spider.extract_job_posting_json_ld(response)

    assert posting["title"] == "Backend Engineer"


def test_greenhouse_parses_matching_jobs():
    spider = GreenhouseSpider(role="software engineer", boards="example")
    response = TextResponse(
        url="https://boards-api.greenhouse.io/v1/boards/example/jobs?content=true",
        body=b"""{"jobs":[{"title":"Software Engineer","company_name":"Example",
        "absolute_url":"https://example.com/job","content":"<p>Python services</p>",
        "location":{"name":"Remote"},"updated_at":"2026-01-01"}]}""",
        encoding="utf-8",
    )

    items = list(spider.parse_board(response, "example"))

    assert len(items) == 1
    assert items[0].company == "Example"
    assert items[0].description == "Python services"


def test_lever_combines_description_sections():
    spider = LeverSpider(role="software engineer", companies="example")
    response = TextResponse(
        url="https://api.lever.co/v0/postings/example?mode=json",
        body=b"""[{"text":"Software Engineer","descriptionPlain":"Build Python systems",
        "lists":[{"content":"APIs and distributed services"}],
        "categories":{"location":"Remote"},"hostedUrl":"https://example.com/job",
        "createdAt":1767225600000}]""",
        encoding="utf-8",
    )

    items = list(spider.parse_company(response, "example"))

    assert len(items) == 1
    assert "distributed services" in items[0].description
