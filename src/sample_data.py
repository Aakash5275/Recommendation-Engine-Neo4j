"""Synthetic MovieLens-shaped graph used to check both strategies."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from src.config import ROOT

DEMO_USER_ID = 1
EXPECTED_CF_MOVIES = (6, 7)
EXPECTED_CONTENT_MOVIES = (6, 7)
FORBIDDEN_CF_MOVIES = (1, 2, 3, 4)


def build_sample() -> dict[str, list[dict[str, object]]]:
    movies = [
        {"movieId": 1, "title": "Alpha Protocol (1999)", "genres": "Sci-Fi"},
        {"movieId": 2, "title": "Beta Station (2001)", "genres": "Sci-Fi|Action"},
        {"movieId": 3, "title": "Gamma Drift (2004)", "genres": "Sci-Fi"},
        {"movieId": 4, "title": "Delta Circuit (2007)", "genres": "Sci-Fi|Action"},
        {"movieId": 5, "title": "Epsilon Heist (1998)", "genres": "Action"},
        {"movieId": 6, "title": "Zeta Horizon (2010)", "genres": "Sci-Fi"},
        {"movieId": 7, "title": "Eta Vector (2012)", "genres": "Sci-Fi|Action"},
        {"movieId": 8, "title": "Theta Family (1995)", "genres": "Drama"},
        {"movieId": 9, "title": "Iota Wedding (2000)", "genres": "Drama|Comedy"},
        {"movieId": 10, "title": "Kappa Laughs (2003)", "genres": "Comedy"},
    ]
    raw_ratings = [
        (1, 1, 5.0),
        (1, 2, 5.0),
        (1, 3, 4.5),
        (1, 4, 5.0),
        (1, 8, 2.0),
        (2, 1, 5.0),
        (2, 2, 5.0),
        (2, 3, 4.5),
        (2, 4, 5.0),
        (2, 6, 5.0),
        (2, 7, 4.5),
        (3, 1, 4.5),
        (3, 2, 5.0),
        (3, 3, 5.0),
        (3, 4, 4.5),
        (3, 6, 5.0),
        (3, 7, 5.0),
        (4, 8, 5.0),
        (4, 9, 5.0),
        (4, 10, 4.5),
        (4, 5, 4.0),
    ]
    ratings = [
        {
            "userId": user_id,
            "movieId": movie_id,
            "rating": rating,
            "timestamp": 1_700_000_000 + index,
        }
        for index, (user_id, movie_id, rating) in enumerate(raw_ratings)
    ]
    raw_tags = [
        (1, 1, "mind-bending"),
        (1, 2, "space"),
        (1, 3, "alien"),
        (2, 6, "mind-bending"),
        (3, 7, "space"),
    ]
    tags = [
        {
            "userId": user_id,
            "movieId": movie_id,
            "tag": tag,
            "timestamp": 1_700_000_000 + index,
        }
        for index, (user_id, movie_id, tag) in enumerate(raw_tags)
    ]
    return {"movies": movies, "ratings": ratings, "tags": tags}


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_sample(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    data = build_sample()
    _write_csv(directory / "movies.csv", ["movieId", "title", "genres"], data["movies"])
    _write_csv(
        directory / "ratings.csv",
        ["userId", "movieId", "rating", "timestamp"],
        data["ratings"],
    )
    _write_csv(
        directory / "tags.csv",
        ["userId", "movieId", "tag", "timestamp"],
        data["tags"],
    )
    return directory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write a tiny MovieLens-shaped CSV sample")
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "sample")
    args = parser.parse_args(argv)
    out = args.out if args.out.is_absolute() else Path.cwd() / args.out
    write_sample(out)
    data = build_sample()
    print(
        f"Wrote {len(data['movies'])} movies, {len(data['ratings'])} ratings, "
        f"{len(data['tags'])} tags to {out}"
    )
    print("Next: python -m src.ingest --data-dir data/sample")
    print(f"Dashboard demo userId: {DEMO_USER_ID}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
