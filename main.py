from __future__ import annotations

import argparse
import subprocess
import sys
import uuid

from src.database import Database
from src.rag import RagService
from src.run_log import RunLogStore


def run_ingest(role: str, sources: list[str]) -> None:
    Database().ensure_schema()
    run_id = str(uuid.uuid4())
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
            check=True,
        )
    print({"run_id": run_id, "status": "completed", "sources": sources})


def run_query(question: str) -> None:
    answer, sources = RagService().query(question)
    print({"answer": answer, "sources": sources})


def run_stats() -> None:
    summary = Database().stats()
    summary["last_5_runs"] = [entry.model_dump() for entry in RunLogStore().last_runs(limit=5)]
    print(summary)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Competitive intelligence pipeline CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest")
    ingest_parser.add_argument("--role", required=True)
    ingest_parser.add_argument("--sources", nargs="+", required=True)

    query_parser = subparsers.add_parser("query")
    query_parser.add_argument("--q", required=True)

    subparsers.add_parser("stats")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "ingest":
        run_ingest(args.role, args.sources)
    elif args.command == "query":
        run_query(args.q)
    elif args.command == "stats":
        run_stats()


if __name__ == "__main__":
    main()
