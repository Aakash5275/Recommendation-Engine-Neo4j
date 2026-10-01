"""Apply uniqueness constraints before ingestion."""

from __future__ import annotations

import argparse

from src.config import CYPHER_DIR
from src.cypher_io import split_statements
from src.db import Database, open_database


def apply_file(db: Database, filename: str) -> int:
    script = (CYPHER_DIR / filename).read_text(encoding="utf-8")
    statements = split_statements(script)
    for statement in statements:
        db.run_autocommit(statement)
    return len(statements)


def apply_constraints(db: Database) -> int:
    return apply_file(db, "constraints.cypher")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create MovieLens uniqueness constraints")
    parser.parse_args(argv)
    try:
        database = open_database()
    except Exception as exc:
        print(f"Cannot connect to Neo4j: {exc}")
        return 2
    with database:
        count = apply_constraints(database)
    print(f"Applied {count} uniqueness constraints.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
