"""Explain and PROFILE plan trees."""

from __future__ import annotations

from typing import Any, Iterator


def node_to_dict(node: Any) -> dict[str, Any]:
    arguments = getattr(node, "arguments", {}) or {}
    details = ""
    if isinstance(arguments, dict):
        details = str(arguments.get("Details", "") or "")
    data: dict[str, Any] = {
        "operator": getattr(node, "operator_type", "Unknown"),
        "details": details,
        "children": [node_to_dict(child) for child in getattr(node, "children", [])],
    }
    if hasattr(node, "db_hits"):
        data["db_hits"] = node.db_hits
    if hasattr(node, "records"):
        data["rows"] = node.records
    return data


def format_plan(node: dict[str, Any], depth: int = 0) -> str:
    line = f"{'  ' * depth}{node.get('operator', 'Unknown')}"
    details = node.get("details") or ""
    if details:
        line += f" | {details}"
    if node.get("db_hits") is not None:
        line += f" | dbHits={node['db_hits']}"
    if node.get("rows") is not None:
        line += f" | rows={node['rows']}"
    lines = [line]
    for child in node.get("children", []):
        lines.append(format_plan(child, depth + 1))
    return "\n".join(lines)


def iter_operators(node: dict[str, Any]) -> Iterator[str]:
    yield f"{node.get('operator', '')} {node.get('details', '')}".strip()
    for child in node.get("children", []):
        yield from iter_operators(child)


def tree_flags(node: dict[str, Any]) -> dict[str, Any]:
    operators = list(iter_operators(node))
    return {
        "index_seek": any("IndexSeek" in operator for operator in operators),
        "all_nodes_scan": any("AllNodesScan" in operator for operator in operators),
        "operators": operators,
    }


def total_db_hits(node: dict[str, Any]) -> int:
    total = int(node.get("db_hits") or 0)
    for child in node.get("children", []):
        total += total_db_hits(child)
    return total
