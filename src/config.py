"""Project paths and Neo4j connection settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
CYPHER_DIR = ROOT / "cypher"


@dataclass(frozen=True)
class Settings:
    uri: str
    user: str
    password: str
    database: str
    query_timeout: float

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv(ROOT / ".env")
        password = os.getenv("NEO4J_PASSWORD", "movielens32m")
        if not password:
            raise ValueError("NEO4J_PASSWORD is empty. Copy .env.example to .env and set it.")
        return cls(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            user=os.getenv("NEO4J_USER", "neo4j"),
            password=password,
            database=os.getenv("NEO4J_DATABASE", "neo4j"),
            query_timeout=float(os.getenv("NEO4J_QUERY_TIMEOUT", "45")),
        )
