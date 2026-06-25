from __future__ import annotations


class CrawlerIdentityMiddleware:
    """Use an explicit crawler identity instead of impersonating browsers."""

    USER_AGENT = "JobIntelligenceResearchBot/1.0 (+https://github.com/arkaprabha)"

    def process_request(self, request, spider):
        del spider
        request.headers.setdefault("User-Agent", self.USER_AGENT)
        request.headers.setdefault("Accept", "application/json,text/html;q=0.9,*/*;q=0.8")
