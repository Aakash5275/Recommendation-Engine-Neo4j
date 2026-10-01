"""Run both strategies against a live database and check the sample expectations."""

from __future__ import annotations

import argparse

from src.db import open_database
from src.recommend import (
    RecommendParams,
    content_hybrid,
    explain_query,
    graph_counts,
    user_based,
    user_profile,
)
from src.sample_data import (
    DEMO_USER_ID,
    EXPECTED_CF_MOVIES,
    EXPECTED_CONTENT_MOVIES,
    FORBIDDEN_CF_MOVIES,
)


def _ids(rows: list[dict]) -> set[int]:
    return {int(row["movieId"]) for row in rows}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check live recommendation queries")
    parser.add_argument("--user-id", type=int, default=DEMO_USER_ID)
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Assert the synthetic demo recommendations for user 1",
    )
    args = parser.parse_args(argv)
    params = RecommendParams()
    try:
        database = open_database()
    except Exception as exc:
        print(f"Cannot connect to Neo4j: {exc}")
        return 2

    with database:
        counts = graph_counts(database)
        print(
            "Graph: "
            + ", ".join(f"{key}={value}" for key, value in counts.items())
        )
        if counts["users"] == 0 or counts["movies"] == 0:
            print("Graph is empty. Load data before running this check.")
            return 1

        profile = user_profile(database, args.user_id, params.min_rating)
        if profile is None:
            print(f"No User node with userId {args.user_id}.")
            return 1
        print(f"User {args.user_id} ratings={profile['ratingCount']} genres={profile['topGenres']}")

        cf_rows = user_based(database, args.user_id, params)
        content_rows = content_hybrid(database, args.user_id, params)
        print("Strategy A:", ", ".join(str(row["movieId"]) for row in cf_rows) or "(none)")
        print("Strategy B:", ", ".join(str(row["movieId"]) for row in content_rows) or "(none)")

        for label, filename, parameters in (
            ("A", "user_based_cf.cypher", params.cf_parameters(args.user_id)),
            ("B", "content_hybrid.cypher", params.content_parameters(args.user_id)),
        ):
            plan = explain_query(database, filename, parameters)
            print(
                f"Plan {label}: index_seek={plan['index_seek']} "
                f"all_nodes_scan={plan['all_nodes_scan']}"
            )
            if not plan["index_seek"] or plan["all_nodes_scan"]:
                print(plan["text"])
                print(f"Strategy {label} is not anchored on a property index.")
                return 1

        if args.sample:
            if args.user_id != DEMO_USER_ID:
                print("--sample is defined for demo user 1.")
                return 2
            cf_ids = _ids(cf_rows)
            content_ids = _ids(content_rows)
            missing_cf = [movie_id for movie_id in EXPECTED_CF_MOVIES if movie_id not in cf_ids]
            missing_content = [
                movie_id for movie_id in EXPECTED_CONTENT_MOVIES if movie_id not in content_ids
            ]
            forbidden = [movie_id for movie_id in FORBIDDEN_CF_MOVIES if movie_id in cf_ids]
            if missing_cf or missing_content or forbidden:
                print(
                    f"Sample check failed. missing_cf={missing_cf} "
                    f"missing_content={missing_content} forbidden_in_cf={forbidden}"
                )
                return 1
            print("Sample expectations matched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
