"""Print EXPLAIN or PROFILE output for the recommendation queries."""

from __future__ import annotations

import argparse

from src.db import open_database
from src.recommend import RecommendParams, explain_query


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Show the Neo4j plan for both strategies")
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--mode", choices=["explain", "profile"], default="explain")
    args = parser.parse_args(argv)
    params = RecommendParams()
    mode = args.mode.upper()
    try:
        database = open_database()
    except Exception as exc:
        print(f"Cannot connect to Neo4j: {exc}")
        return 2

    checks = (
        ("Strategy A user-based CF", "user_based_cf.cypher", params.cf_parameters(args.user_id)),
        ("Strategy B content hybrid", "content_hybrid.cypher", params.content_parameters(args.user_id)),
    )
    failed = False
    with database:
        for label, filename, parameters in checks:
            print(f"\n{label} ({mode})")
            try:
                plan = explain_query(database, filename, parameters, mode=mode)
            except Exception as exc:
                print(f"Query failed: {exc}")
                return 1
            print(plan["text"])
            if plan.get("db_hits") is not None:
                print(f"Total dbHits: {plan['db_hits']}")
            if plan["index_seek"]:
                print("Index seek: yes")
            else:
                print("Index seek: no")
                failed = True
            if plan["all_nodes_scan"]:
                print("AllNodesScan: yes")
                failed = True
            else:
                print("AllNodesScan: no")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
