"""Batch-load MovieLens CSV files into Neo4j."""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from src.cypher_io import load_query
from src.db import Database, open_database
from src.schema import apply_constraints
from src.transform import PreparedRows, movie_rows, rating_rows, tag_rows

DELETE_BATCH = """
MATCH (n)
WITH n LIMIT $batch
DETACH DELETE n
"""


def resolve_data_dir(path: Path) -> Path:
    candidate = path.expanduser()
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    candidate = candidate.resolve()
    if (candidate / "movies.csv").is_file():
        return candidate
    for nested in (candidate / "ml-32m", candidate / "ml-latest-small", candidate / "sample"):
        if (nested / "movies.csv").is_file():
            return nested
    raise FileNotFoundError(
        f"No movies.csv in {candidate}. Download MovieLens 32M or generate data/sample."
    )


def iter_csv_chunks(path: Path, batch_size: int, max_rows: int | None, **kwargs: Any):
    seen = 0
    reader = pd.read_csv(path, chunksize=batch_size, on_bad_lines="skip", **kwargs)
    for chunk in reader:
        if max_rows is not None:
            remaining = max_rows - seen
            if remaining <= 0:
                break
            if len(chunk) > remaining:
                chunk = chunk.iloc[:remaining].copy()
        yield chunk
        seen += len(chunk)
        if max_rows is not None and seen >= max_rows:
            break


def reset_database(db: Database, batch: int = 10000) -> None:
    print("Deleting existing nodes in batches...")
    removed = 0
    while True:
        _rows, summary = db.run(DELETE_BATCH, {"batch": batch}, timeout=120)
        deleted = int(summary.counters.nodes_deleted)
        if deleted == 0:
            break
        removed += deleted
        print(f"  deleted {removed:,} nodes")
    print("Graph is empty.")


def load_phase(
    db: Database,
    path: Path,
    prepare: Callable[[pd.DataFrame], PreparedRows],
    query: str,
    *,
    label: str,
    batch_size: int,
    max_rows: int | None,
    usecols: list[str],
) -> dict[str, int]:
    source = 0
    written = 0
    skipped = 0
    started = time.perf_counter()
    for chunk in iter_csv_chunks(path, batch_size, max_rows, usecols=usecols):
        source += len(chunk)
        prepared = prepare(chunk)
        skipped += prepared.skipped
        if prepared.rows:
            db.run_write(query, {"rows": prepared.rows})
            written += len(prepared.rows)
        elapsed = time.perf_counter() - started
        rate = source / elapsed if elapsed else 0
        print(
            f"{label}: read {source:,} | written {written:,} | "
            f"skipped {skipped:,} | {rate:,.0f} rows/s"
        )
    return {"source": source, "written": written, "skipped": skipped}


def ingest(
    db: Database,
    data_dir: Path,
    *,
    batch_size: int = 20000,
    max_ratings: int | None = None,
    max_tags: int | None = None,
    reset: bool = False,
    movies_only: bool = False,
    skip_tags: bool = False,
) -> dict[str, dict[str, int]]:
    if reset:
        reset_database(db)
    constraints = apply_constraints(db)
    print(f"Uniqueness constraints ready ({constraints}).")

    results: dict[str, dict[str, int]] = {}
    results["movies"] = load_phase(
        db,
        data_dir / "movies.csv",
        movie_rows,
        load_query("load_movies.cypher"),
        label="movies",
        batch_size=min(batch_size, 5000),
        max_rows=None,
        usecols=["movieId", "title", "genres"],
    )

    if not movies_only:
        ratings_path = data_dir / "ratings.csv"
        if not ratings_path.is_file():
            raise FileNotFoundError(f"Missing {ratings_path}")
        results["ratings"] = load_phase(
            db,
            ratings_path,
            rating_rows,
            load_query("load_ratings.cypher"),
            label="ratings",
            batch_size=batch_size,
            max_rows=max_ratings,
            usecols=["userId", "movieId", "rating", "timestamp"],
        )

    if not movies_only and not skip_tags:
        tags_path = data_dir / "tags.csv"
        if tags_path.is_file():
            results["tags"] = load_phase(
                db,
                tags_path,
                tag_rows,
                load_query("load_tags.cypher"),
                label="tags",
                batch_size=min(batch_size, 10000),
                max_rows=max_tags,
                usecols=["userId", "movieId", "tag", "timestamp"],
            )
        else:
            print(f"No tags.csv in {data_dir}; tag traversal will be empty.")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load MovieLens CSV files into Neo4j")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=20000)
    parser.add_argument("--max-ratings", type=int, default=None)
    parser.add_argument("--max-tags", type=int, default=None)
    parser.add_argument("--reset", action="store_true", help="Delete all nodes before loading")
    parser.add_argument("--yes", action="store_true", help="Required with --reset")
    parser.add_argument("--movies-only", action="store_true")
    parser.add_argument("--skip-tags", action="store_true")
    args = parser.parse_args(argv)

    if args.batch_size < 1:
        print("--batch-size must be at least 1")
        return 2
    if args.reset and not args.yes:
        print("Refusing to delete the graph without --yes.")
        return 2

    try:
        data_dir = resolve_data_dir(args.data_dir)
    except FileNotFoundError as exc:
        print(exc)
        return 2

    print(f"Loading {data_dir}")
    try:
        database = open_database()
    except Exception as exc:
        print(f"Cannot connect to Neo4j: {exc}")
        return 2

    started = time.perf_counter()
    try:
        with database:
            ingest(
                database,
                data_dir,
                batch_size=args.batch_size,
                max_ratings=args.max_ratings,
                max_tags=args.max_tags,
                reset=args.reset,
                movies_only=args.movies_only,
                skip_tags=args.skip_tags,
            )
    except Exception as exc:
        print(f"Load failed: {exc}")
        return 1

    elapsed = time.perf_counter() - started
    print(f"Finished in {elapsed:,.1f}s.")
    print("Next: streamlit run app.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
