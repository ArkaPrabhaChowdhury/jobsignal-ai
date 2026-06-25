from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from typing import Iterator

import psycopg2
from pgvector import Vector
from pgvector.psycopg2 import register_vector
from psycopg2.extras import Json

from src.config import get_settings
from src.models import JobListing, ListingPreview


class Database:
    def __init__(self, dsn: str | None = None) -> None:
        self.settings = get_settings()
        self.dsn = dsn or self.settings.database_url

    @contextmanager
    def connect(
        self, *, register_vector_type: bool = True
    ) -> Iterator[psycopg2.extensions.connection]:
        conn = psycopg2.connect(
            self.dsn,
            connect_timeout=self.settings.db_connect_timeout_seconds,
        )
        if register_vector_type:
            register_vector(conn)
        try:
            yield conn
        finally:
            conn.close()

    def ping(self) -> bool:
        with self.connect(register_vector_type=False) as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
            return cur.fetchone() == (1,)

    def ensure_schema(self) -> None:
        with self.connect(register_vector_type=False) as conn, conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.commit()
            register_vector(conn)
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS job_listings (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    url TEXT NOT NULL,
                    description TEXT NOT NULL,
                    location TEXT NOT NULL,
                    source TEXT NOT NULL,
                    posted_at TEXT,
                    skills JSONB NOT NULL DEFAULT '[]'::jsonb,
                    confidence DOUBLE PRECISION NOT NULL,
                    embedding vector({self.settings.embedding_dimensions}),
                    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            conn.commit()

    def exists(self, listing_id: str) -> bool:
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM job_listings WHERE id = %s", (listing_id,))
            return cur.fetchone() is not None

    def upsert_listing(self, listing: JobListing) -> bool:
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO job_listings
                (id, title, company, url, description, location, source, posted_at,
                 skills, confidence, embedding, ingested_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    listing.id,
                    listing.title,
                    listing.company,
                    listing.url,
                    listing.description,
                    listing.location,
                    listing.source,
                    listing.posted_at,
                    Json(listing.skills),
                    listing.confidence,
                    listing.embedding,
                    listing.ingested_at,
                ),
            )
            inserted = cur.rowcount == 1
            conn.commit()
            return inserted

    def similarity_search(self, embedding: list[float], limit: int = 15) -> list[JobListing]:
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, company, url, description, location, source, posted_at,
                       skills, confidence, embedding, ingested_at
                FROM job_listings
                ORDER BY embedding <-> %s
                LIMIT %s
                """,
                (Vector(embedding), limit),
            )
            rows = cur.fetchall()
        return [
            JobListing(
                id=row[0],
                title=row[1],
                company=row[2],
                url=row[3],
                description=row[4],
                location=row[5],
                source=row[6],
                posted_at=row[7],
                skills=row[8],
                confidence=row[9],
                embedding=row[10],
                ingested_at=row[11],
            )
            for row in rows
        ]

    def stats(self) -> dict:
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM job_listings")
            total = cur.fetchone()[0]

            cur.execute("SELECT source, COUNT(*) FROM job_listings GROUP BY source")
            by_source = {source: count for source, count in cur.fetchall()}

            cur.execute("SELECT skills FROM job_listings")
            skill_rows = cur.fetchall()

        counts = Counter()
        for row in skill_rows:
            for skill in row[0]:
                counts[skill] += 1

        top_skills = [{"skill": skill, "count": count} for skill, count in counts.most_common(10)]
        return {
            "total_listings": total,
            "by_source": by_source,
            "top_skills": top_skills,
        }

    def recent_listings(self, limit: int = 12) -> list[ListingPreview]:
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, company, url, location, source, posted_at,
                       skills, confidence, ingested_at
                FROM job_listings
                ORDER BY ingested_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
        return [
            ListingPreview(
                id=row[0],
                title=row[1],
                company=row[2],
                url=row[3],
                location=row[4],
                source=row[5],
                posted_at=row[6],
                skills=row[7],
                confidence=row[8],
                ingested_at=row[9],
            )
            for row in rows
        ]
