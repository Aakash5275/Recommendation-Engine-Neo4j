"""Live recommendation traversals."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any

from src.cypher_io import load_query
from src.db import Database, open_database
from src.plan import format_plan, node_to_dict, total_db_hits, tree_flags

COUNT_QUERIES = {
    "users": "MATCH (u:User) RETURN count(u) AS c",
    "movies": "MATCH (m:Movie) RETURN count(m) AS c",
    "genres": "MATCH (g:Genre) RETURN count(g) AS c",
    "tags": "MATCH (t:Tag) RETURN count(t) AS c",
    "rated": "MATCH ()-[r:RATED]->() RETURN count(r) AS c",
    "in_genre": "MATCH ()-[r:IN_GENRE]->() RETURN count(r) AS c",
    "tagged": "MATCH ()-[r:TAGGED]->() RETURN count(r) AS c",
    "has_tag": "MATCH ()-[r:HAS_TAG]->() RETURN count(r) AS c",
}


@dataclass(frozen=True)
class RecommendParams:
    min_rating: float = 4.0
    peer_min_rating: float = 4.0
    seed_limit: int = 15
    neighbor_limit: int = 25
    min_shared: int = 3
    top_genres: int = 5
    min_genre_overlap: int = 1
    candidate_limit: int = 80
    tag_boost: float = 2.0
    limit: int = 10
    path_limit: int = 40

    def validate(self) -> None:
        if not 0.5 <= self.min_rating <= 5:
            raise ValueError("Minimum rating must be between 0.5 and 5.")
        if not 0.5 <= self.peer_min_rating <= 5:
            raise ValueError("Peer rating threshold must be between 0.5 and 5.")
        if self.tag_boost < 0:
            raise ValueError("Tag boost cannot be negative.")
        for name, value in (
            ("seed_limit", self.seed_limit),
            ("neighbor_limit", self.neighbor_limit),
            ("min_shared", self.min_shared),
            ("top_genres", self.top_genres),
            ("min_genre_overlap", self.min_genre_overlap),
            ("candidate_limit", self.candidate_limit),
            ("limit", self.limit),
            ("path_limit", self.path_limit),
        ):
            if int(value) < 1:
                raise ValueError(f"{name} must be at least 1")

    def cf_parameters(self, user_id: int) -> dict[str, Any]:
        return {
            "userId": int(user_id),
            "minRating": float(self.min_rating),
            "peerMinRating": float(self.peer_min_rating),
            "seedLimit": int(self.seed_limit),
            "neighborLimit": int(self.neighbor_limit),
            "minShared": int(self.min_shared),
            "limit": int(self.limit),
        }

    def content_parameters(self, user_id: int) -> dict[str, Any]:
        return {
            "userId": int(user_id),
            "minRating": float(self.min_rating),
            "topGenres": int(self.top_genres),
            "minGenreOverlap": int(self.min_genre_overlap),
            "candidateLimit": int(self.candidate_limit),
            "tagBoost": float(self.tag_boost),
            "limit": int(self.limit),
        }

    def cf_path_parameters(self, user_id: int, movie_id: int) -> dict[str, Any]:
        return {
            "userId": int(user_id),
            "movieId": int(movie_id),
            "minRating": float(self.min_rating),
            "peerMinRating": float(self.peer_min_rating),
            "pathLimit": int(self.path_limit),
        }

    def content_path_parameters(self, user_id: int, movie_id: int) -> dict[str, Any]:
        return {
            "userId": int(user_id),
            "movieId": int(movie_id),
            "minRating": float(self.min_rating),
            "pathLimit": int(self.path_limit),
        }


def graph_counts(db: Database) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key, query in COUNT_QUERIES.items():
        rows, _summary = db.run(query, timeout=30)
        counts[key] = int(rows[0]["c"]) if rows else 0
    return counts


def user_profile(db: Database, user_id: int, min_rating: float) -> dict[str, Any] | None:
    rows, _summary = db.run(load_query("user_profile.cypher"), {"userId": int(user_id)})
    if not rows:
        return None
    profile = dict(rows[0])
    genres, _summary = db.run(
        load_query("user_genres.cypher"),
        {"userId": int(user_id), "minRating": float(min_rating)},
    )
    profile["topGenres"] = [row["genre"] for row in genres if row.get("genre")]
    if profile.get("avgRating") is not None:
        profile["avgRating"] = round(float(profile["avgRating"]), 2)
    profile["ratingCount"] = int(profile["ratingCount"])
    return profile


def user_based(db: Database, user_id: int, params: RecommendParams) -> list[dict[str, Any]]:
    params.validate()
    rows, _summary = db.run(
        load_query("user_based_cf.cypher"),
        params.cf_parameters(user_id),
    )
    return rows


def content_hybrid(db: Database, user_id: int, params: RecommendParams) -> list[dict[str, Any]]:
    params.validate()
    rows, _summary = db.run(
        load_query("content_hybrid.cypher"),
        params.content_parameters(user_id),
    )
    return rows


def cf_paths(db: Database, user_id: int, movie_id: int, params: RecommendParams) -> list[dict[str, Any]]:
    params.validate()
    rows, _summary = db.run(
        load_query("cf_path.cypher"),
        params.cf_path_parameters(user_id, movie_id),
    )
    return rows


def content_paths(
    db: Database, user_id: int, movie_id: int, params: RecommendParams
) -> list[dict[str, Any]]:
    params.validate()
    rows, _summary = db.run(
        load_query("content_path.cypher"),
        params.content_path_parameters(user_id, movie_id),
    )
    return rows


def explain_query(db: Database, filename: str, parameters: dict[str, Any], mode: str = "EXPLAIN") -> dict[str, Any]:
    prefix = mode.upper()
    if prefix not in {"EXPLAIN", "PROFILE"}:
        raise ValueError("mode must be EXPLAIN or PROFILE")
    _rows, summary = db.run(
        f"{prefix}\n{load_query(filename)}",
        parameters,
        timeout=30 if prefix == "EXPLAIN" else 90,
    )
    tree = summary.profile if prefix == "PROFILE" and summary.profile is not None else summary.plan
    if tree is None:
        return {
            "text": "Neo4j did not return a plan.",
            "index_seek": False,
            "all_nodes_scan": False,
            "operators": [],
            "db_hits": None,
        }
    node = node_to_dict(tree)
    flags = tree_flags(node)
    db_hits = total_db_hits(node) if prefix == "PROFILE" else None
    return {"text": format_plan(node), "db_hits": db_hits, **flags}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print recommendations for one user")
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args(argv)
    params = RecommendParams(limit=args.limit)
    try:
        database = open_database()
    except Exception as exc:
        print(f"Cannot connect to Neo4j: {exc}")
        return 2
    with database:
        profile = user_profile(database, args.user_id, params.min_rating)
        if profile is None:
            print(f"No User node with userId {args.user_id}.")
            return 1
        print(
            f"User {profile['userId']}: {profile['ratingCount']} ratings, "
            f"average {profile['avgRating']}, top genres {profile['topGenres']}"
        )
        print("\nStrategy A: user-based collaborative filtering")
        for row in user_based(database, args.user_id, params):
            print(
                f"  {row['title']} | score {row['matchScore']} | "
                f"similar users {row['similarityCount']} | predicted {row['avgRating']}"
            )
        print("\nStrategy B: content-hybrid traversal")
        for row in content_hybrid(database, args.user_id, params):
            print(
                f"  {row['title']} | score {row['matchScore']} | "
                f"genres {row['genreOverlap']} | tags {row['tagOverlap']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
