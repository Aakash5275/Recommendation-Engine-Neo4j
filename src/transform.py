"""Turn MovieLens CSV rows into graph-load payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

MIN_RATING = 0.5
MAX_RATING = 5.0
MAX_TAG_LENGTH = 200


@dataclass(frozen=True)
class PreparedRows:
    rows: list[dict[str, Any]]
    skipped: int


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(missing)


def _as_int(value: Any) -> int | None:
    if _is_missing(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if _is_missing(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_genres(value: Any) -> list[str]:
    if _is_missing(value):
        return []
    text = str(value).strip()
    if not text or text == "(no genres listed)":
        return []
    genres: list[str] = []
    for part in text.split("|"):
        name = " ".join(part.strip().split())
        if not name or name == "(no genres listed)" or name in genres:
            continue
        genres.append(name)
    return genres


def normalize_tag(value: Any) -> str | None:
    if _is_missing(value):
        return None
    text = " ".join(str(value).strip().split())
    if not text or text.lower() == "nan" or len(text) > MAX_TAG_LENGTH:
        return None
    return text


def movie_rows(frame: pd.DataFrame) -> PreparedRows:
    grouped: dict[int, dict[str, Any]] = {}
    skipped = 0
    for record in frame.itertuples(index=False):
        movie_id = _as_int(getattr(record, "movieId", None))
        title = getattr(record, "title", None)
        if movie_id is None or _is_missing(title) or not str(title).strip():
            skipped += 1
            continue
        genres = parse_genres(getattr(record, "genres", None))
        current = grouped.get(movie_id)
        if current is None:
            grouped[movie_id] = {
                "movieId": movie_id,
                "title": str(title).strip(),
                "genres": genres,
            }
            continue
        current["title"] = str(title).strip()
        merged = list(current["genres"])
        for genre in genres:
            if genre not in merged:
                merged.append(genre)
        current["genres"] = merged
    return PreparedRows(rows=list(grouped.values()), skipped=skipped)


def rating_rows(frame: pd.DataFrame) -> PreparedRows:
    grouped: dict[tuple[int, int], dict[str, Any]] = {}
    skipped = 0
    for record in frame.itertuples(index=False):
        user_id = _as_int(getattr(record, "userId", None))
        movie_id = _as_int(getattr(record, "movieId", None))
        rating = _as_float(getattr(record, "rating", None))
        timestamp = _as_int(getattr(record, "timestamp", None))
        if user_id is None or movie_id is None or rating is None:
            skipped += 1
            continue
        if rating < MIN_RATING or rating > MAX_RATING:
            skipped += 1
            continue
        grouped[(user_id, movie_id)] = {
            "userId": user_id,
            "movieId": movie_id,
            "rating": rating,
            "timestamp": 0 if timestamp is None else timestamp,
        }
    return PreparedRows(rows=list(grouped.values()), skipped=skipped)


def tag_rows(frame: pd.DataFrame) -> PreparedRows:
    grouped: dict[tuple[int, int, str], dict[str, Any]] = {}
    skipped = 0
    for record in frame.itertuples(index=False):
        user_id = _as_int(getattr(record, "userId", None))
        movie_id = _as_int(getattr(record, "movieId", None))
        tag = normalize_tag(getattr(record, "tag", None))
        timestamp = _as_int(getattr(record, "timestamp", None))
        if user_id is None or movie_id is None or tag is None:
            skipped += 1
            continue
        grouped[(user_id, movie_id, tag)] = {
            "userId": user_id,
            "movieId": movie_id,
            "tag": tag,
            "timestamp": 0 if timestamp is None else timestamp,
        }
    return PreparedRows(rows=list(grouped.values()), skipped=skipped)
