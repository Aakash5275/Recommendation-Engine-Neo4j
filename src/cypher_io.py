"""Load Cypher files and list their parameters."""

from __future__ import annotations

import re

from src.config import CYPHER_DIR

_PARAM = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")


def split_statements(script: str) -> list[str]:
    """Split a Cypher script on semicolons, ignoring // comments."""
    statements: list[str] = []
    buffer: list[str] = []
    for line in script.splitlines():
        if line.strip().startswith("//"):
            continue
        buffer.append(line)
        if line.strip().endswith(";"):
            statement = "\n".join(buffer).strip()
            if statement.endswith(";"):
                statement = statement[:-1].strip()
            if statement:
                statements.append(statement)
            buffer = []
    tail = "\n".join(buffer).strip()
    if tail.endswith(";"):
        tail = tail[:-1].strip()
    if tail:
        statements.append(tail)
    return statements


def load_query(filename: str) -> str:
    path = CYPHER_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Missing Cypher file: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if text.endswith(";"):
        text = text[:-1].strip()
    return text


def parameter_names(query: str) -> set[str]:
    code_lines = [line for line in query.splitlines() if not line.strip().startswith("//")]
    return set(_PARAM.findall("\n".join(code_lines)))
