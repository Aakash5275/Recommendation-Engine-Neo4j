"""Plan tree helpers."""

from __future__ import annotations

import unittest

from src.plan import format_plan, node_to_dict, total_db_hits, tree_flags


class _Node:
    def __init__(self, operator: str, details: str = "", children: list | None = None, db_hits: int = 0):
        self.operator_type = operator
        self.arguments = {"Details": details}
        self.children = children or []
        self.db_hits = db_hits


class PlanTests(unittest.TestCase):
    def test_index_seek_flag(self) -> None:
        tree = {
            "operator": "ProduceResults",
            "details": "",
            "children": [
                {
                    "operator": "NodeUniqueIndexSeek",
                    "details": ":User(userId) WHERE userId = $userId",
                    "children": [],
                }
            ],
        }
        flags = tree_flags(tree)
        self.assertTrue(flags["index_seek"])
        self.assertFalse(flags["all_nodes_scan"])
        text = format_plan(tree)
        self.assertIn("NodeUniqueIndexSeek", text)
        self.assertIn(":User(userId)", text)

    def test_all_nodes_scan_and_db_hits(self) -> None:
        tree = {
            "operator": "AllNodesScan",
            "details": "",
            "db_hits": 4,
            "children": [{"operator": "Filter", "details": "", "db_hits": 6, "children": []}],
        }
        flags = tree_flags(tree)
        self.assertTrue(flags["all_nodes_scan"])
        self.assertEqual(total_db_hits(tree), 10)

    def test_node_to_dict_reads_driver_shaped_objects(self) -> None:
        node = node_to_dict(_Node("NodeUniqueIndexSeek", ":Movie(movieId)", db_hits=1))
        self.assertEqual(node["operator"], "NodeUniqueIndexSeek")
        self.assertEqual(node["db_hits"], 1)
        self.assertTrue(tree_flags(node)["index_seek"])


if __name__ == "__main__":
    unittest.main()
