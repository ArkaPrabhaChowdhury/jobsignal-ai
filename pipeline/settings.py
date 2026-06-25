from __future__ import annotations

from src.config import get_settings

settings = get_settings()

BOT_NAME = "jobsignal_ai"

SPIDER_MODULES = ["pipeline.spiders"]
NEWSPIDER_MODULE = "pipeline.spiders"

ROBOTSTXT_OBEY = True
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.5
AUTOTHROTTLE_MAX_DELAY = 10
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [408, 425, 429, 500, 502, 503, 504]
DOWNLOAD_DELAY = settings.crawl_delay_ms / 1000
CONCURRENT_REQUESTS_PER_DOMAIN = 4
DOWNLOAD_TIMEOUT = 30
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 900
HTTPCACHE_IGNORE_HTTP_CODES = [401, 403, 407, 429, 500, 502, 503, 504]
LOG_LEVEL = settings.log_level

ITEM_PIPELINES = {
    "pipeline.pipelines.ValidatePipeline": 100,
    "pipeline.pipelines.EnrichPipeline": 200,
    "pipeline.pipelines.EmbedPipeline": 300,
    "pipeline.pipelines.StorePipeline": 400,
}

DOWNLOADER_MIDDLEWARES = {
    "pipeline.middlewares.CrawlerIdentityMiddleware": 400,
}
