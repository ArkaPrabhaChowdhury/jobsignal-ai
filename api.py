from __future__ import annotations

import time
from contextlib import asynccontextmanager
import json
import subprocess
import sys
import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.config import get_settings
from src.database import Database
from src.models import IngestRequest, ListingPreview, QueryResponse, StatsResponse
from src.rag import RagService
from src.run_log import RunLogStore


def bootstrap_database() -> None:
    settings = get_settings()
    if not settings.strict_startup:
        return
    attempts = max(1, settings.db_startup_retries)
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            Database().ensure_schema()
            return
        except Exception as exc:  # pragma: no cover - exercised in integration
            last_error = exc
            if attempt == attempts:
                break
            time.sleep(settings.db_startup_delay_seconds)
    if settings.strict_startup and last_error is not None:
        raise RuntimeError("database bootstrap failed") from last_error


@asynccontextmanager
async def lifespan(_: FastAPI):
    bootstrap_database()
    yield


app = FastAPI(title="JobSignal AI", lifespan=lifespan)
FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

SOURCE_CATALOG = [
    {
        "name": "cutshort",
        "mode": "safe",
        "description": "Uses sitemap discovery, then scrapes full Cutshort job pages.",
    },
    {
        "name": "foundit",
        "mode": "safe",
        "description": "Uses Foundit sitemaps, then scrapes full job detail pages.",
    },
    {
        "name": "foundit_demo",
        "mode": "portfolio-demo",
        "description": "Starts from real Foundit search results, extracts page state, calls the site's search endpoint, then scrapes job pages.",
    },
    {
        "name": "greenhouse_playwright",
        "mode": "browser-automation-demo",
        "description": "Renders a public Greenhouse board in headless Chromium, filters it through a browser interaction, then extracts job pages.",
    },
    {
        "name": "forage_ai",
        "mode": "html-sitemap",
        "description": "Discovers Forage AI roles through its XML sitemap and extracts resilient full-page job records.",
    },
    {
        "name": "greenhouse",
        "mode": "public-ats-api",
        "description": "Normalizes published jobs from configurable Greenhouse company boards.",
    },
    {
        "name": "lever",
        "mode": "public-ats-api",
        "description": "Extracts structured postings, sections, locations, and timestamps from Lever boards.",
    },
    {
        "name": "ashby",
        "mode": "public-ats-api",
        "description": "Consumes Ashby's public posting API with HTML cleanup and remote-location normalization.",
    },
    {
        "name": "himalayas",
        "mode": "public-job-api",
        "description": "Crawls the paginated Himalayas remote-jobs feed with local relevance filtering.",
    },
    {
        "name": "arbeitnow",
        "mode": "public-job-api",
        "description": "Crawls Arbeitnow's paginated public feed with role search and normalized timestamps.",
    },
]

LANDING_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>JobSignal AI</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Manrope:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #f4efe6;
      --bg-soft: #ece5d8;
      --surface: rgba(255, 252, 246, 0.84);
      --surface-strong: #fffdf8;
      --card: #f8f2e8;
      --ink: #182426;
      --muted: #59696b;
      --line: rgba(24, 36, 38, 0.12);
      --line-strong: rgba(24, 36, 38, 0.2);
      --accent: #1f6f67;
      --accent-soft: rgba(31, 111, 103, 0.12);
      --accent-2: #b77145;
      --ok: #2d8a76;
      --shadow: 0 28px 70px rgba(45, 39, 31, 0.12);
      --radius-xl: 34px;
      --radius-lg: 24px;
      --radius-md: 18px;
      --max: 1200px;
      --ease: cubic-bezier(.2,.8,.2,1);
    }

    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      color: var(--ink);
      font-family: "Manrope", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(31, 111, 103, 0.08), transparent 32%),
        radial-gradient(circle at 88% 12%, rgba(183, 113, 69, 0.08), transparent 28%),
        linear-gradient(180deg, #f8f4ec 0%, #f4efe6 48%, #eee7da 100%);
      min-height: 100vh;
    }

    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background:
        radial-gradient(circle at 20% 20%, rgba(255, 255, 255, 0.4), transparent 34%),
        repeating-linear-gradient(90deg, rgba(24, 36, 38, 0.015), rgba(24, 36, 38, 0.015) 1px, transparent 1px, transparent 5px);
      opacity: 0.45;
      mix-blend-mode: multiply;
    }

    a { color: inherit; }
    img { max-width: 100%; display: block; }
    h1, h2, h3, p { margin: 0; }

    .skip-link {
      position: absolute;
      left: 16px;
      top: -48px;
      background: var(--ink);
      color: #fff;
      padding: 10px 14px;
      border-radius: 12px;
      z-index: 10;
    }
    .skip-link:focus { top: 16px; }

    .page {
      width: min(var(--max), calc(100% - 40px));
      margin: 0 auto;
      padding: 24px 0 56px;
      position: relative;
      z-index: 1;
    }

    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      padding: 14px 18px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(255, 253, 248, 0.68);
      box-shadow: 0 14px 32px rgba(45, 39, 31, 0.06);
      backdrop-filter: blur(14px);
    }

    .brand-title {
      font-weight: 700;
      letter-spacing: -0.02em;
    }

    .brand-kicker,
    .code,
    .eyebrow,
    .badge,
    .meta,
    .section-kicker {
      font-family: "IBM Plex Mono", monospace;
      letter-spacing: 0.04em;
    }

    .brand-kicker,
    .section-kicker,
    .eyebrow {
      text-transform: uppercase;
      font-size: 0.76rem;
      color: var(--accent);
    }

    .hero {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(380px, 520px);
      gap: 54px;
      align-items: center;
      padding: 34px 0 14px;
    }

    .hero-copy {
      display: flex;
      align-items: center;
      min-height: 650px;
    }

    .hero-copy-inner {
      max-width: 610px;
    }

    .trust-badge {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 10px 14px;
      border-radius: 999px;
      background: rgba(255, 253, 248, 0.86);
      border: 1px solid var(--line);
      color: var(--muted);
      box-shadow: 0 12px 28px rgba(45, 39, 31, 0.06);
    }

    .trust-badge svg {
      width: 16px;
      height: 16px;
      fill: var(--accent-2);
      flex: 0 0 auto;
    }

    .trust-score {
      color: var(--ink);
      font-weight: 700;
    }

    .headline {
      margin-top: 24px;
      max-width: 11ch;
      font-family: "Fraunces", serif;
      font-size: clamp(3.2rem, 7vw, 6rem);
      line-height: 0.94;
      letter-spacing: -0.05em;
    }

    .headline-emphasis {
      color: var(--accent);
      font-family: "IBM Plex Mono", monospace;
      font-size: 0.8em;
      letter-spacing: -0.06em;
      text-transform: uppercase;
      white-space: nowrap;
    }

    .headline-avatars {
      display: inline-flex;
      vertical-align: middle;
      margin: 0 0.14em;
      transform: translateY(-0.06em);
    }

    .headline-avatars span {
      width: 0.96em;
      height: 0.96em;
      border-radius: 50%;
      margin-left: -0.2em;
      border: 2px solid rgba(248, 244, 236, 0.95);
      box-shadow: 0 8px 18px rgba(45, 39, 31, 0.16);
      display: block;
    }
    .headline-avatars span:first-child { margin-left: 0; }
    .avatar-one { background: linear-gradient(135deg, #f1c39a, #97623d); }
    .avatar-two { background: linear-gradient(135deg, #c7ded5, #42766d); }
    .avatar-three { background: linear-gradient(135deg, #ddd6f3, #6a628f); }

    .hero-summary {
      max-width: 54ch;
      margin-top: 24px;
      color: var(--muted);
      font-size: 1.06rem;
      line-height: 1.8;
    }

    .hero-cta {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      margin-top: 26px;
      padding: 16px 24px;
      border-radius: 999px;
      background: var(--accent);
      color: #f8f4ec;
      font-weight: 700;
      text-decoration: none;
      box-shadow: 0 16px 34px rgba(31, 111, 103, 0.22);
      transition: transform 220ms var(--ease), box-shadow 220ms var(--ease);
    }

    .hero-cta:hover {
      transform: translateY(-2px);
      box-shadow: 0 22px 44px rgba(31, 111, 103, 0.22);
    }

    .hero-stats {
      display: flex;
      flex-wrap: wrap;
      gap: 30px;
      margin-top: 32px;
      padding-top: 32px;
      border-top: 1px solid var(--line-strong);
    }

    .hero-stat-value {
      display: block;
      font-family: "Fraunces", serif;
      font-size: clamp(2rem, 3.6vw, 2.7rem);
      line-height: 1;
      color: var(--ink);
    }

    .hero-stat-label {
      display: block;
      margin-top: 8px;
      color: var(--muted);
      font-size: 0.92rem;
      line-height: 1.45;
    }

    .hero-media {
      position: relative;
      min-height: 650px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .portrait-card {
      width: 100%;
      min-height: 650px;
      position: relative;
      overflow: hidden;
      border-radius: 42px;
      background:
        radial-gradient(circle at 20% 16%, rgba(255, 255, 255, 0.3), transparent 28%),
        linear-gradient(180deg, #d6ccc1 0%, #c6b6a1 28%, #8d7a68 100%);
      box-shadow: var(--shadow);
    }

    .portrait-card::after {
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(180deg, rgba(255,255,255,0) 34%, rgba(24,36,38,0.12) 100%);
      pointer-events: none;
    }

    .hero-media-note {
      position: absolute;
      top: 28px;
      left: 30px;
      z-index: 2;
      color: rgba(255, 250, 244, 0.78);
      font-family: "IBM Plex Mono", monospace;
      font-size: 0.76rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .portrait-svg {
      width: 100%;
      height: 100%;
      display: block;
    }

    .floating-stack,
    .floating-stat-card,
    .floating-tag-card {
      position: absolute;
      z-index: 3;
      box-shadow: 0 18px 40px rgba(45, 39, 31, 0.14);
    }

    .floating-stack {
      top: 26px;
      right: 22px;
      display: grid;
      gap: 10px;
    }

    .check-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 14px;
      border-radius: 999px;
      background: rgba(248, 244, 236, 0.9);
      color: var(--ink);
      border: 1px solid rgba(24, 36, 38, 0.08);
      font-size: 0.88rem;
      backdrop-filter: blur(10px);
    }

    .check-pill svg {
      width: 14px;
      height: 14px;
      fill: var(--ok);
      flex: 0 0 auto;
    }

    .floating-stat-card {
      width: 154px;
      padding: 18px;
      border-radius: 26px;
      background: var(--accent);
      color: #f8f4ec;
    }

    .floating-stat-left {
      top: 176px;
      left: -18px;
    }

    .floating-stat-right {
      right: -12px;
      bottom: 30px;
      background: var(--accent-2);
    }

    .floating-stat-value {
      display: block;
      font-family: "Fraunces", serif;
      font-size: 2.2rem;
      line-height: 1;
    }

    .floating-stat-label {
      display: block;
      margin-top: 10px;
      font-size: 0.88rem;
      line-height: 1.4;
      color: rgba(248, 244, 236, 0.86);
    }

    .floating-tag-card {
      left: 22px;
      bottom: 40px;
      width: min(300px, calc(100% - 74px));
      padding: 18px;
      border-radius: 26px;
      background: rgba(255, 253, 248, 0.95);
      color: var(--ink);
    }

    .floating-tag-title {
      font-family: "Fraunces", serif;
      font-size: 1rem;
      margin-bottom: 12px;
    }

    .tag-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .tag-chip {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 8px 10px;
      border-radius: 999px;
      border: 1px solid rgba(24, 36, 38, 0.12);
      background: #fff;
      color: var(--muted);
      font-size: 0.84rem;
    }

    .section-band {
      margin-top: 34px;
      padding: 30px;
      border-radius: var(--radius-xl);
      border: 1px solid var(--line);
      background: rgba(255, 252, 246, 0.72);
      box-shadow: 0 24px 60px rgba(45, 39, 31, 0.08);
      backdrop-filter: blur(12px);
    }

    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 22px;
      margin-bottom: 22px;
    }

    .section-header-copy {
      max-width: 650px;
    }

    .section-title {
      margin-top: 8px;
      font-family: "Fraunces", serif;
      font-size: clamp(1.7rem, 2.3vw, 2.15rem);
      line-height: 1.06;
      letter-spacing: -0.04em;
    }

    .section-summary {
      margin-top: 10px;
      color: var(--muted);
      line-height: 1.7;
    }

    .section-actions {
      color: var(--muted);
      font-family: "IBM Plex Mono", monospace;
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      white-space: nowrap;
    }

    .grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 22px;
    }

    .panel {
      border-radius: 28px;
      border: 1px solid var(--line);
      background: var(--surface);
      box-shadow: 0 18px 42px rgba(45, 39, 31, 0.06);
      backdrop-filter: blur(10px);
    }

    .section-panel {
      padding: 26px;
    }

    .panel-heading {
      font-family: "Fraunces", serif;
      font-size: 1.34rem;
      letter-spacing: -0.03em;
    }

    .panel-summary {
      margin-top: 8px;
      color: var(--muted);
      line-height: 1.64;
    }

    .source-list,
    .skill-list,
    .runs {
      display: grid;
      gap: 14px;
      margin-top: 18px;
    }

    .listing-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      margin-top: 18px;
    }

    .source-card,
    .listing-card,
    .run-card {
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: var(--radius-md);
      background: var(--surface-strong);
      transition: transform 220ms var(--ease), box-shadow 220ms var(--ease), border-color 220ms var(--ease);
    }

    .source-card:hover,
    .listing-card:hover,
    .run-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 14px 28px rgba(45, 39, 31, 0.08);
      border-color: rgba(31, 111, 103, 0.22);
    }

    .source-head,
    .listing-head,
    .run-head {
      display: flex;
      justify-content: space-between;
      align-items: start;
      gap: 14px;
    }

    .card-title {
      font-size: 1rem;
      line-height: 1.45;
      letter-spacing: -0.02em;
    }

    .badge {
      white-space: nowrap;
      font-size: 0.72rem;
      text-transform: uppercase;
      color: var(--accent);
      padding: 7px 10px;
      border-radius: 999px;
      background: var(--accent-soft);
      border: 1px solid rgba(31, 111, 103, 0.14);
    }

    .muted {
      color: var(--muted);
      line-height: 1.65;
    }

    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }

    .chip {
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid rgba(24, 36, 38, 0.1);
      background: rgba(255, 255, 255, 0.7);
      color: var(--muted);
      font-size: 0.8rem;
    }

    .meta {
      margin-top: 12px;
      font-size: 0.75rem;
      color: var(--muted);
    }

    .form-grid {
      display: grid;
      gap: 18px;
      margin-top: 20px;
    }

    .field-group {
      display: grid;
      gap: 8px;
    }

    .field-label {
      color: var(--accent);
      font-family: "IBM Plex Mono", monospace;
      font-size: 0.76rem;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }

    .field-hint {
      color: var(--muted);
      font-size: 0.88rem;
      line-height: 1.58;
    }

    input,
    textarea,
    button {
      font: inherit;
      border-radius: 18px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.72);
      color: var(--ink);
    }

    input,
    textarea {
      width: 100%;
      padding: 15px 16px;
    }

    textarea {
      min-height: 136px;
      resize: vertical;
    }

    button {
      padding: 15px 18px;
      background: var(--accent);
      color: #f8f4ec;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 14px 28px rgba(31, 111, 103, 0.18);
      transition: transform 220ms var(--ease), box-shadow 220ms var(--ease), filter 220ms var(--ease);
    }

    button:hover {
      transform: translateY(-1px);
      filter: brightness(1.03);
      box-shadow: 0 18px 34px rgba(31, 111, 103, 0.2);
    }

    .query-card {
      margin-top: 18px;
      min-height: 184px;
      padding: 20px;
      border-radius: 22px;
      border: 1px solid var(--line);
      background: rgba(248, 244, 236, 0.92);
    }

    .status-title {
      display: block;
      margin-bottom: 10px;
      font-family: "Fraunces", serif;
      font-size: 1.06rem;
    }

    .answer {
      color: var(--ink);
      line-height: 1.72;
      white-space: pre-wrap;
    }

    .source-links {
      display: grid;
      gap: 8px;
      margin-top: 14px;
    }

    .source-links a {
      color: var(--accent);
      text-decoration: none;
      word-break: break-word;
    }

    .footer-note {
      margin-top: 18px;
      padding-top: 16px;
      border-top: 1px solid var(--line);
      color: var(--muted);
      font-size: 0.92rem;
      line-height: 1.62;
    }

    .reveal {
      opacity: 0;
      transform: translateY(24px);
      transition: opacity 600ms var(--ease), transform 600ms var(--ease);
    }

    .reveal.visible {
      opacity: 1;
      transform: translateY(0);
    }

    .hero-copy-inner > * {
      opacity: 0;
      transform: translateY(18px);
      animation: heroRise 700ms var(--ease) forwards;
    }

    .hero-copy-inner > *:nth-child(1) { animation-delay: 80ms; }
    .hero-copy-inner > *:nth-child(2) { animation-delay: 160ms; }
    .hero-copy-inner > *:nth-child(3) { animation-delay: 240ms; }
    .hero-copy-inner > *:nth-child(4) { animation-delay: 320ms; }
    .hero-copy-inner > *:nth-child(5) { animation-delay: 400ms; }

    .floating-stack,
    .floating-stat-card,
    .floating-tag-card {
      animation: floatIn 760ms var(--ease) forwards;
      opacity: 0;
      transform: translateY(16px);
    }

    .floating-stack { animation-delay: 220ms; }
    .floating-stat-left { animation-delay: 300ms; }
    .floating-tag-card { animation-delay: 380ms; }
    .floating-stat-right { animation-delay: 460ms; }

    @keyframes heroRise {
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    @keyframes floatIn {
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    @media (max-width: 980px) {
      .hero,
      .grid-2,
      .listing-grid {
        grid-template-columns: 1fr;
      }

      .hero-copy,
      .hero-media {
        min-height: auto;
      }

      .hero {
        gap: 30px;
      }

      .section-header {
        flex-direction: column;
        align-items: start;
      }
    }

    @media (max-width: 640px) {
      .page {
        width: min(100%, calc(100% - 24px));
        padding-top: 18px;
      }

      .topbar {
        border-radius: 26px;
        align-items: start;
        flex-direction: column;
      }

      .headline {
        font-size: clamp(2.5rem, 14vw, 4.4rem);
      }

      .portrait-card {
        min-height: 520px;
      }

      .floating-stat-left {
        left: 10px;
        top: 160px;
      }

      .floating-stat-right {
        right: 10px;
        bottom: 22px;
      }

      .floating-tag-card {
        left: 14px;
        bottom: 94px;
        width: calc(100% - 88px);
      }

      .floating-stack {
        top: 14px;
        right: 14px;
      }

      .section-band,
      .section-panel {
        padding-left: 18px;
        padding-right: 18px;
      }
    }

    @media (prefers-reduced-motion: reduce) {
      html { scroll-behavior: auto; }
      *, *::before, *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
      }
      .reveal,
      .hero-copy-inner > *,
      .floating-stack,
      .floating-stat-card,
      .floating-tag-card {
        opacity: 1 !important;
        transform: none !important;
      }
    }
  </style>
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <div class="page">
    <header class="topbar reveal">
      <div>
        <div class="brand-kicker">Scrapy + Groq + pgvector</div>
        <div class="brand-title">JobSignal AI</div>
      </div>
      <div class="code">/docs /stats /query /sources</div>
    </header>

    <main id="main">
      <section class="hero">
        <article class="hero-copy">
          <div class="hero-copy-inner">
            <div class="trust-badge">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 2.7l2.73 5.53 6.1.89-4.41 4.3 1.04 6.08L12 16.6l-5.46 2.87 1.05-6.08-4.41-4.3 6.1-.89L12 2.7z"></path>
              </svg>
              <span class="trust-score">4.9/5</span>
              <span>Portfolio Review</span>
            </div>
            <h1 class="headline">
              Turn live hiring pages into
              <span class="headline-avatars" aria-hidden="true">
                <span class="avatar-one"></span>
                <span class="avatar-two"></span>
                <span class="avatar-three"></span>
              </span>
              market-ready <span class="headline-emphasis">signal</span>
            </h1>
            <p class="hero-summary">
              A production-style intelligence pipeline that scrapes live India job listings,
              extracts skills, stores semantic vectors, and answers recruiter-facing questions
              from grounded evidence rather than static feeds.
            </p>
            <a class="hero-cta" href="#demo">Explore Live Demo</a>
            <div class="hero-stats" aria-label="Hero stats">
              <div>
                <span class="hero-stat-value" id="total-listings">-</span>
                <span class="hero-stat-label">Listings indexed</span>
              </div>
              <div>
                <span class="hero-stat-value" id="source-count">-</span>
                <span class="hero-stat-label">Active sources</span>
              </div>
              <div>
                <span class="hero-stat-value" id="recent-run-count">-</span>
                <span class="hero-stat-label">Tracked crawl runs</span>
              </div>
            </div>
          </div>
        </article>

        <aside class="hero-media reveal" aria-label="Platform preview">
          <div class="portrait-card">
            <div class="hero-media-note">Live extraction preview</div>
            <svg class="portrait-svg" viewBox="0 0 760 860" role="img" aria-label="Stylized professional portrait">
              <defs>
                <linearGradient id="portraitBase" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="#ddd4ca"></stop>
                  <stop offset="56%" stop-color="#bfae99"></stop>
                  <stop offset="100%" stop-color="#7b6858"></stop>
                </linearGradient>
                <linearGradient id="coatGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="#1b2d2f"></stop>
                  <stop offset="100%" stop-color="#32484b"></stop>
                </linearGradient>
              </defs>
              <rect width="760" height="860" fill="url(#portraitBase)"></rect>
              <circle cx="560" cy="184" r="140" fill="rgba(255,255,255,0.16)"></circle>
              <circle cx="182" cy="174" r="90" fill="rgba(255,255,255,0.12)"></circle>
              <path d="M216 826c16-180 95-262 165-262h16c78 0 156 83 166 262H216z" fill="url(#coatGrad)"></path>
              <path d="M380 568c-76 0-140-61-140-148V286c0-104 66-171 149-171s149 67 149 171v134c0 87-64 148-158 148z" fill="#c9936e"></path>
              <path d="M272 282c26-102 95-146 173-146 81 0 132 44 148 129-32-18-83-35-135-35-70 0-130 17-186 52z" fill="#243436"></path>
              <path d="M266 304c13-91 70-168 173-168 92 0 150 57 158 160-39-37-89-63-158-63-69 0-120 19-173 71z" fill="#1b2628"></path>
              <ellipse cx="331" cy="343" rx="14" ry="9" fill="#223031"></ellipse>
              <ellipse cx="448" cy="343" rx="14" ry="9" fill="#223031"></ellipse>
              <path d="M355 391c15 12 41 12 56 0" stroke="#88553a" stroke-width="10" stroke-linecap="round" fill="none"></path>
              <path d="M323 467c42 28 95 28 133-1" stroke="#7c4734" stroke-width="11" stroke-linecap="round" fill="none"></path>
            </svg>
          </div>
          <div class="floating-stack">
            <div class="check-pill">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M20.29 5.71a1 1 0 0 1 0 1.41l-9 9a1 1 0 0 1-1.41 0l-4-4a1 1 0 0 1 1.41-1.41l3.3 3.29 8.29-8.29a1 1 0 0 1 1.41 0z"></path>
              </svg>
              <span>Live crawl</span>
            </div>
            <div class="check-pill">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M20.29 5.71a1 1 0 0 1 0 1.41l-9 9a1 1 0 0 1-1.41 0l-4-4a1 1 0 0 1 1.41-1.41l3.3 3.29 8.29-8.29a1 1 0 0 1 1.41 0z"></path>
              </svg>
              <span>Role matched</span>
            </div>
          </div>
          <div class="floating-stat-card floating-stat-left">
            <span class="floating-stat-value" id="hero-media-total">-</span>
            <span class="floating-stat-label">verified<br>records</span>
          </div>
          <div class="floating-tag-card">
            <div class="floating-tag-title">Signal clusters</div>
            <div class="tag-row">
              <span class="tag-chip">+ Python</span>
              <span class="tag-chip">+ APIs</span>
              <span class="tag-chip">+ Docker</span>
              <span class="tag-chip">+ Kubernetes</span>
            </div>
          </div>
          <div class="floating-stat-card floating-stat-right">
            <span class="floating-stat-value" id="hero-media-runs">-</span>
            <span class="floating-stat-label">recent<br>runs</span>
          </div>
        </aside>
      </section>

      <section class="section-band reveal">
        <div class="section-header">
          <div class="section-header-copy">
            <div class="section-kicker">Coverage</div>
            <h2 class="section-title">Source coverage and extracted demand themes</h2>
            <p class="section-summary">Safe crawlers and a results-page demo scraper feed one normalized intelligence layer, so the page reads like a platform rather than a crawler log.</p>
          </div>
          <div class="section-actions">Live source catalog</div>
        </div>
        <div class="grid-2">
          <article class="panel section-panel">
            <h3 class="panel-heading">Source Modes</h3>
            <p class="panel-summary">Each source is labeled by collection mode so recruiters can distinguish safe discovery from direct site scraping.</p>
            <div class="source-list" id="source-list"></div>
          </article>
          <article class="panel section-panel">
            <h3 class="panel-heading">Top Skills</h3>
            <p class="panel-summary">Frequent skills are derived from stored descriptions and exposed as current market signals.</p>
            <div class="skill-list" id="skill-list"></div>
          </article>
        </div>
      </section>

      <section class="section-band reveal" id="demo">
        <div class="section-header">
          <div class="section-header-copy">
            <div class="section-kicker">Interactive Demo</div>
            <h2 class="section-title">Run the system from one clean interface</h2>
            <p class="section-summary">This area is designed for recruiter walkthroughs: ask a market question, trigger an ingest, and show cited outputs without dropping into the terminal.</p>
          </div>
          <div class="section-actions">API plus UI workflow</div>
        </div>
        <div class="grid-2">
          <article class="panel section-panel">
            <h3 class="panel-heading">Ask the Dataset</h3>
            <p class="panel-summary">Run retrieval-backed questions over the currently stored job listings.</p>
            <form id="query-form" class="form-grid">
              <div class="field-group">
                <label for="question" class="field-label">Question</label>
                <textarea id="question" name="question">What skills are trending in software engineer roles in India?</textarea>
                <div class="field-hint">Use role, skill, city, or stack-specific prompts to show grounded market analysis.</div>
              </div>
              <button type="submit">Run Market Query</button>
            </form>
            <div class="query-card" id="query-result">
              <span class="status-title">Query Result</span>
              <div class="muted">Query output will appear here.</div>
            </div>
          </article>
          <article class="panel section-panel">
            <h3 class="panel-heading">Trigger Ingest</h3>
            <p class="panel-summary">Start a fresh crawl directly from the dashboard. Use <span class="code">greenhouse_playwright</span> for the browser-automation walkthrough.</p>
            <form id="ingest-form" class="form-grid">
              <div class="field-group">
                <label for="role" class="field-label">Role</label>
                <input id="role" name="role" value="software engineer">
              </div>
              <div class="field-group">
                <label for="sources" class="field-label">Sources</label>
                <input id="sources" name="sources" value="greenhouse_playwright">
                <div class="field-hint">Comma-separate values such as <span class="code">cutshort,foundit</span> for safe mode.</div>
              </div>
              <button type="submit">Start Ingest</button>
            </form>
            <div class="query-card" id="ingest-result">
              <span class="status-title">Ingest Status</span>
              <div class="muted">Ingest status will appear here.</div>
            </div>
          </article>
        </div>
      </section>

      <section class="section-band reveal">
        <div class="section-header">
          <div class="section-header-copy">
            <div class="section-kicker">Evidence Layer</div>
            <h2 class="section-title">Recent records and crawl telemetry</h2>
            <p class="section-summary">The page stays grounded in actual listings and recent run logs, which makes the demo materially stronger than a static product mockup.</p>
          </div>
          <div class="section-actions">Inspectable output</div>
        </div>
        <div class="grid-2">
          <article class="panel section-panel">
            <h3 class="panel-heading">Recent Listings</h3>
            <p class="panel-summary">Fresh records show title, company, location, skill tags, and confidence from the enrichment step.</p>
            <div class="listing-grid" id="listing-grid"></div>
          </article>
          <article class="panel section-panel">
            <h3 class="panel-heading">Recent Runs</h3>
            <p class="panel-summary">Operational telemetry shows what each crawl fetched, stored, or skipped.</p>
            <div class="runs" id="run-list"></div>
            <p class="footer-note">Safe sources follow robot and throttle defaults. Demo scrapers are controlled portfolio examples for results-page and browser-rendered extraction.</p>
          </article>
        </div>
      </section>
    </main>
  </div>

  <script>
    const sourceCatalog = __SOURCE_CATALOG__;

    function fmt(value) {
      return value ?? "-";
    }

    function relativeTime(value) {
      if (!value) return "unknown";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return value;
      const diffMs = Date.now() - date.getTime();
      const diffMin = Math.round(diffMs / 60000);
      if (diffMin < 1) return "just now";
      if (diffMin < 60) return `${diffMin} min ago`;
      const diffHr = Math.round(diffMin / 60);
      if (diffHr < 24) return `${diffHr} hr ago`;
      const diffDay = Math.round(diffHr / 24);
      return `${diffDay} day ago`;
    }

    function setHTML(id, html) {
      const el = document.getElementById(id);
      el.innerHTML = html;
      enhanceReveals(el);
    }

    function enhanceReveals(scope = document) {
      const observer = window.revealObserver;
      if (!observer) return;
      scope.querySelectorAll(".reveal").forEach((el) => observer.observe(el));
    }

    function initRevealObserver() {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        document.querySelectorAll(".reveal").forEach((el) => el.classList.add("visible"));
        return;
      }
      window.revealObserver = new IntersectionObserver((entries, obs) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            obs.unobserve(entry.target);
          }
        });
      }, { threshold: 0.15, rootMargin: "0px 0px -10% 0px" });
      enhanceReveals(document);
    }

    async function loadDashboard() {
      const [statsResponse, listingsResponse] = await Promise.all([
        fetch("/stats"),
        fetch("/listings/recent?limit=8")
      ]);
      const stats = await statsResponse.json();
      const listings = await listingsResponse.json();

      document.getElementById("total-listings").textContent = fmt(stats.total_listings);
      document.getElementById("source-count").textContent = Object.keys(stats.by_source || {}).length;
      document.getElementById("recent-run-count").textContent = stats.last_5_runs?.length || 0;
      document.getElementById("hero-media-total").textContent = fmt(stats.total_listings);
      document.getElementById("hero-media-runs").textContent = stats.last_5_runs?.length || 0;

      setHTML("source-list", sourceCatalog.map(source => `
        <article class="source-card reveal">
          <div class="source-head">
            <h3 class="card-title">${source.name}</h3>
            <span class="badge">${source.mode}</span>
          </div>
          <p class="muted">${source.description}</p>
        </article>
      `).join(""));

      setHTML("skill-list", (stats.top_skills || []).map(skill => `
        <article class="run-card reveal">
          <div class="run-head">
            <h3 class="card-title">${skill.skill}</h3>
            <span class="badge">${skill.count} hits</span>
          </div>
        </article>
      `).join("") || '<div class="muted">No skill data yet.</div>');

      setHTML("listing-grid", listings.map(listing => `
        <article class="listing-card reveal">
          <div class="listing-head">
            <h3 class="card-title"><a href="${listing.url}" target="_blank" rel="noreferrer">${listing.title}</a></h3>
            <span class="badge">${listing.source}</span>
          </div>
          <p class="muted">${listing.company} / ${listing.location}</p>
          <div class="chips">${(listing.skills || []).slice(0, 4).map(skill => `<span class="chip">${skill}</span>`).join("")}</div>
          <div class="meta">Confidence ${Number(listing.confidence || 0).toFixed(2)} / ${relativeTime(listing.ingested_at)}</div>
        </article>
      `).join("") || '<div class="muted">No listings available yet.</div>');

      setHTML("run-list", (stats.last_5_runs || []).map(run => `
        <article class="run-card reveal">
          <div class="run-head">
            <h3 class="card-title">${run.source}</h3>
            <span class="badge">${relativeTime(run.started_at)}</span>
          </div>
          <p class="muted">Fetched ${run.fetched} / Stored ${run.stored} / Low confidence ${run.skipped_low_confidence}</p>
          <div class="meta">${run.run_id}</div>
        </article>
      `).join("") || '<div class="muted">No runs captured yet.</div>');
    }

    document.getElementById("query-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const question = document.getElementById("question").value.trim();
      setHTML("query-result", '<span class="status-title">Query Result</span><div class="muted">Running query...</div>');
      const response = await fetch(`/query?q=${encodeURIComponent(question)}`);
      const data = await response.json();
      setHTML("query-result", `
        <span class="status-title">Query Result</span>
        <div class="answer">${data.answer}</div>
        <div class="source-links">${(data.sources || []).map(url => `<a href="${url}" target="_blank" rel="noreferrer">${url}</a>`).join("")}</div>
      `);
    });

    document.getElementById("ingest-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const role = document.getElementById("role").value.trim();
      const sources = document.getElementById("sources").value.split(",").map(value => value.trim()).filter(Boolean);
      setHTML("ingest-result", '<span class="status-title">Ingest Status</span><div class="muted">Starting ingest...</div>');
      const response = await fetch("/ingest", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ role, sources })
      });
      const data = await response.json();
      setHTML("ingest-result", `
        <span class="status-title">Ingest Status</span>
        <div class="answer">Run started.</div>
        <div class="source-links">
          <div>Run ID: ${data.run_id}</div>
          <div>Sources: ${(data.sources || []).join(", ")}</div>
        </div>
      `);
    });

    initRevealObserver();
    loadDashboard().catch((error) => {
      const message = error?.message || "Dashboard load failed.";
      setHTML("query-result", `<span class="status-title">Query Result</span><div class="muted">${message}</div>`);
    });
  </script>
</body>
</html>
"""


def _run_ingest_sources(role: str, sources: list[str], run_id: str) -> None:
    for source in sources:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "scrapy",
                "crawl",
                source,
                "-a",
                f"role={role}",
                "-a",
                f"run_id={run_id}",
            ],
            check=False,
        )


@app.get("/", response_class=HTMLResponse)
def landing() -> HTMLResponse:
    page = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(page.replace("__SOURCE_CATALOG__", json.dumps(SOURCE_CATALOG)))


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "favicon.svg", media_type="image/svg+xml")


@app.get("/health")
def health():
    try:
        Database().ping()
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "degraded", "database": "unavailable", "detail": str(exc)},
        )
    return {"status": "ok", "database": "reachable"}


@app.get("/sources")
def sources():
    return SOURCE_CATALOG


@app.post("/ingest")
def ingest(request: IngestRequest):
    if not get_settings().public_ingest_enabled:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "status": "disabled",
                "detail": "Public ingest is disabled for this deployment.",
            },
        )
    run_id = str(uuid.uuid4())
    thread = threading.Thread(
        target=_run_ingest_sources,
        args=(request.role, request.sources, run_id),
        daemon=True,
    )
    thread.start()
    return {"run_id": run_id, "status": "started", "sources": request.sources}


@app.get("/query", response_model=QueryResponse)
def query(q: str):
    Database().ensure_schema()
    answer, sources = RagService().query(q)
    return QueryResponse(answer=answer, sources=sources)


@app.get("/stats", response_model=StatsResponse)
def stats():
    database = Database()
    database.ensure_schema()
    summary = database.stats()
    summary["last_5_runs"] = RunLogStore().last_runs(limit=5)
    return StatsResponse(**summary)


@app.get("/listings/recent", response_model=list[ListingPreview])
def recent_listings(limit: int = 12):
    safe_limit = max(1, min(limit, 24))
    database = Database()
    database.ensure_schema()
    return database.recent_listings(limit=safe_limit)
