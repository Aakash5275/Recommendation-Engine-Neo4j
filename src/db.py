"""Neo4j driver wrapper."""

from __future__ import annotations

from typing import Any

from neo4j import GraphDatabase

from src.config import Settings


class Database:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.driver = GraphDatabase.driver(
            settings.uri,
            auth=(settings.user, settings.password),
            connection_timeout=5,
            max_connection_lifetime=3600,
        )

    def close(self) -> None:
        self.driver.close()

    def __enter__(self) -> Database:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def verify(self) -> None:
        self.driver.verify_connectivity()

    def session(self):
        return self.driver.session(database=self.settings.database)

    def run(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        timeout: float | None = None,
    ):
        with self.session() as session:
            result = session.run(
                query,
                parameters or {},
                timeout=self.settings.query_timeout if timeout is None else timeout,
            )
            rows = [record.data() for record in result]
            summary = result.consume()
            return rows, summary

    def run_write(self, query: str, parameters: dict[str, Any] | None = None) -> None:
        payload = parameters or {}

        def _work(tx, statement: str, params: dict[str, Any]) -> None:
            tx.run(statement, params).consume()

        with self.session() as session:
            session.execute_write(_work, query, payload)

    def run_autocommit(self, query: str, parameters: dict[str, Any] | None = None):
        with self.session() as session:
            result = session.run(query, parameters or {})
            return result.consume()


def open_database() -> Database:
    settings = Settings.from_env()
    database = Database(settings)
    database.verify()
    return database
