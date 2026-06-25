# Competitive Intelligence Pipeline

Production-oriented India job-market intelligence pipeline built with Scrapy, Groq, pgvector, and FastAPI.

This project does more than scrape feeds. It collects live job listings, extracts skills, stores vectorized records, and answers natural-language questions over the scraped dataset.

## Why This Is Resume-Worthy

- Shows real crawling and parsing work, not just CSV cleanup or API consumption.
- Includes enrichment, embeddings, retrieval, and an API layer instead of stopping at raw scrape output.
- Demonstrates both safe crawling and a portfolio-style results-page scraper.
- Ships with a live dashboard at the API root so the project is demoable.

## What It Does

```text
Scrapy spiders
    -> ValidatePipeline
    -> EnrichPipeline
    -> EmbedPipeline
    -> PostgreSQL + pgvector
    -> FastAPI + CLI
    -> recruiter-facing dashboard + RAG query flow
```

## Source Modes

- `cutshort`
  Safe mode. Uses sitemap discovery, then scrapes full Cutshort job pages.
- `foundit`
  Safe mode. Uses Foundit sitemaps, then scrapes full job detail pages.
- `foundit_demo`
  Portfolio-demo mode. Starts from the real Foundit results page, extracts page state, calls the site's search endpoint, then visits job detail pages.
- `greenhouse`
  Public ATS API. Normalizes jobs from configurable Greenhouse boards.
- `lever`
  Public ATS API. Extracts structured Lever postings.
- `ashby`
  Public ATS API. Extracts Ashby job-board records.
- `himalayas`
  Public job API. Crawls a paginated remote-jobs feed.
- `arbeitnow`
  Public job API. Crawls role-filtered European listings.
- `forage_ai`
  Direct scraping. Uses Forage AI's XML sitemap and parses its WordPress job-detail pages.

`foundit_demo` is the proof point for actual website scraping beyond RSS or sitemap-only ingestion.

## Tech Stack

- Crawling: `Scrapy`
- Enrichment: `Groq`
- Embeddings: lightweight deterministic hashing vectors for free-tier deployment
- Storage: `PostgreSQL` + `pgvector`
- API: `FastAPI`
- Tests: `pytest`

## Quick Start

1. Copy `.env.example` to `.env` and set `GROQ_API_KEY`.
2. Start Postgres only:

```bash
docker compose up -d db
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run a crawl.

Safe crawl:

```bash
python main.py ingest --role "software engineer" --sources cutshort foundit
```

Real website-scraping demo:

```bash
python main.py ingest --role "software engineer" --sources foundit_demo

# Production-oriented mix: ATS APIs, public feeds, and direct HTML extraction
python main.py ingest --role "software engineer" --sources greenhouse lever ashby himalayas arbeitnow forage_ai

# ATS spiders accept comma-separated board/company slugs when run directly
scrapy crawl greenhouse -a role="software engineer" -a boards="airbnb,stripe"
scrapy crawl lever -a role="software engineer" -a companies="palantir"
scrapy crawl ashby -a role="software engineer" -a boards="ashby"
```

5. Inspect stats:

```bash
python main.py stats
```

6. Ask a query:

```bash
python main.py query --q "What skills are trending in software engineer roles in India?"
```

7. Start the API and dashboard:

```bash
uvicorn api:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Deployment

The repo now includes a full Docker deployment path for the API, dashboard, and pgvector database.

Files added for deployment:

- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`
- `.env.deploy.example`
- `render.yaml`

### One-time setup

1. Copy `.env.deploy.example` to `.env`
2. Set `GROQ_API_KEY`
3. Change `POSTGRES_PASSWORD`
4. Optionally change `APP_PORT` and `DB_PORT`

### Start the full stack

```bash
docker compose up -d --build
```

This starts:

- `app`: FastAPI + Scrapy runtime
- `db`: PostgreSQL 16 with `pgvector`

### Health check

After startup:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok","database":"reachable"}
```

### Deploy-time behavior

- The app now retries database bootstrap on startup.
- In deploy mode, `STRICT_STARTUP=true` makes the app fail fast if the database never becomes ready.
- Run logs are persisted in the app volume at `/app/data/run_logs.db`.
- The database is persisted in the `pgdata` Docker volume.

### Useful deploy commands

Rebuild:

```bash
docker compose up -d --build
```

View logs:

```bash
docker compose logs -f app
```

Stop:

```bash
docker compose down
```

Stop and remove volumes:

```bash
docker compose down -v
```

## Free Deployment

This repo is prepared for a free Render web service using `render.yaml` and a
separate free Neon PostgreSQL database.

### Recommended Render shape

- Web Service: Docker-based FastAPI app
- Managed Postgres: Neon Free with `pgvector`
- Public link: Render web URL

### Render defaults in this repo

- `render.yaml` provisions one free Docker web service.
- Set `DATABASE_URL` to the Neon pooled connection string.
- Run logs use ephemeral `/tmp` storage; job listings remain persistent in Neon.
- `PUBLIC_INGEST_ENABLED=false` by default on Render so the public resume link is safer
- `/health` is used as the Render health check path

### Deploy on Render

1. Push this repo to GitHub.
2. Create a free Neon project and run `CREATE EXTENSION IF NOT EXISTS vector;`.
3. In Render, create a new Blueprint deployment from the repo.
4. Render will detect `render.yaml`.
5. Set `DATABASE_URL` and the optional `GROQ_API_KEY`.
6. Deploy the stack.

### After first deploy

Use one of these options:

- safest public demo:
  keep public ingest disabled, seed data manually once, and share the dashboard/query surface
- owner-controlled ingest:
  temporarily set `PUBLIC_INGEST_ENABLED=true`, run an ingest, then switch it back to `false`

### Suggested public-demo posture

For a recruiter-facing live link:

- keep `/query`, `/stats`, `/listings/recent`, `/sources`, and `/docs` public
- keep public ingest disabled
- pre-seed the database with recent listings

That gives you a stable public demo without letting strangers trigger crawls.

## Demo Surface

The FastAPI root route now acts as a recruiter-facing dashboard.

It shows:

- total listings
- source coverage
- top extracted skills
- recent crawl runs
- recent scraped listings
- a live RAG query form
- a live ingest trigger form

Useful routes:

- `GET /`
- `GET /health`
- `GET /sources`
- `GET /stats`
- `GET /listings/recent`
- `GET /query?q=<question>`
- `POST /ingest`
- `GET /docs`

## Example Recruiter Demo

Use this exact flow in a call or Loom:

1. Open the dashboard home page.
2. Explain the difference between `foundit` and `foundit_demo`.
3. Trigger `foundit_demo` ingest for `software engineer`.
4. Open recent listings and show scraped titles, companies, skills, and source labels.
5. Ask a query like `What backend skills are trending in India right now?`
6. Open one of the cited URLs to prove the answer is grounded in scraped pages.

That sequence is much stronger than showing code alone.

## How To Present It On Your Resume

Use bullets like:

- Built a Scrapy-based competitive intelligence pipeline that scraped live India job listings and transformed them into a searchable skill-intelligence dataset.
- Added Groq-powered enrichment, sentence-transformer embeddings, and pgvector retrieval to answer natural-language hiring-market questions over scraped data.
- Implemented both safe crawlers and a results-page scraper demo, then exposed the pipeline through FastAPI, a live dashboard, and automated tests.

If you want one tight project line:

> Built a production-style job-market intelligence pipeline with Scrapy, Groq, FastAPI, and pgvector to scrape live listings, extract skills, and answer recruiter-facing market queries.

## How To Showcase It Live

Best option:

- Deploy the FastAPI app and Postgres database.
- Seed it with a recent crawl.
- Put the dashboard URL on your resume and LinkedIn project section.

Practical deployment choices:

- `Render` or `Railway` for the API
- managed `Postgres` with `pgvector`
- optional scheduled ingest later

What recruiters should see:

- a homepage that explains the system
- real recent listings
- source labels
- query answers backed by source URLs
- live API docs at `/docs`

If live crawling is too risky for a public demo, keep production crawling off and pre-seed the database. That still shows the full system without depending on third-party site stability during interviews.

## Suggested Resume/Portfolio Setup

- Resume project title: `Competitive Intelligence Pipeline for India Job Market`
- Resume link: deployed dashboard URL
- GitHub repo: this project with cleaned README
- Optional: 60-second Loom showing ingest -> stats -> query -> cited listings

This combination is usually better than linking GitHub alone.

## Testing

```bash
pytest -q
```

## Ethical Note

The default project settings keep `ROBOTSTXT_OBEY`, retries, and throttle behavior on.

`foundit_demo` is intentionally a portfolio scraper and overrides `ROBOTSTXT_OBEY` so you can demonstrate a real results-page extraction path. Treat it as a demo source, not the production-safe default.
