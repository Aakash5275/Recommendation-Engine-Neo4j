"""Path drawing and the synthetic demo fixture."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.graph_view import cf_elements, content_elements, narrate_cf, narrate_content, render_html
from src.ingest import resolve_data_dir
from src.sample_data import (
    DEMO_USER_ID,
    EXPECTED_CF_MOVIES,
    FORBIDDEN_CF_MOVIES,
    build_sample,
    write_sample,
)


class GraphViewTests(unittest.TestCase):
    def test_cf_elements_follow_rated_edges(self) -> None:
        rows = [
            {
                "targetId": 1,
                "sharedId": 2,
                "sharedTitle": "Beta Station (2001)",
                "myRating": 5.0,
                "peerId": 2,
                "peerSharedRating": 5.0,
                "recId": 6,
                "recTitle": "Zeta Horizon (2010)",
                "recRating": 5.0,
            }
        ]
        nodes, edges = cf_elements(rows)
        node_ids = {node["id"] for node in nodes}
        self.assertEqual(node_ids, {"user-1", "user-2", "movie-2", "movie-6"})
        pairs = {(edge["source"], edge["target"]) for edge in edges}
        self.assertIn(("user-1", "movie-2"), pairs)
        self.assertIn(("user-2", "movie-2"), pairs)
        self.assertIn(("user-2", "movie-6"), pairs)
        self.assertIn("Zeta Horizon", narrate_cf(rows, 1))

    def test_content_elements_include_genre_and_tag(self) -> None:
        rows = [
            {
                "targetId": 1,
                "likedId": 2,
                "likedTitle": "Beta Station (2001)",
                "myRating": 5.0,
                "genre": "Sci-Fi",
                "recId": 7,
                "recTitle": "Eta Vector (2012)",
                "tag": "space",
            }
        ]
        nodes, edges = content_elements(rows)
        node_ids = {node["id"] for node in nodes}
        self.assertIn("genre-Sci-Fi", node_ids)
        self.assertIn("tag-space", node_ids)
        titles = {edge["title"] for edge in edges}
        self.assertIn("IN_GENRE", titles)
        self.assertIn("HAS_TAG", titles)
        text = narrate_content(rows, 1)
        self.assertIn("Sci-Fi", text)
        self.assertIn("space", text)

    def test_empty_path_narration(self) -> None:
        self.assertIn("No similar-user path", narrate_cf([], 1))
        self.assertIn("No genre or tag path", narrate_content([], 1))

    def test_render_html_returns_a_network_document(self) -> None:
        html = render_html(
            [
                {
                    "id": "movie-1",
                    "label": "Amelie",
                    "title": "Amélie",
                    "color": "#f87171",
                    "size": 12,
                }
            ],
            [],
        )
        self.assertIn("movie-1", html)
        self.assertIn("Amelie", html)
        self.assertIn("<html>", html)


class SampleFixtureTests(unittest.TestCase):
    def test_demo_user_has_not_rated_the_expected_recommendations(self) -> None:
        data = build_sample()
        seen = {row["movieId"] for row in data["ratings"] if row["userId"] == DEMO_USER_ID}
        for movie_id in EXPECTED_CF_MOVIES:
            self.assertNotIn(movie_id, seen)
        for movie_id in FORBIDDEN_CF_MOVIES:
            self.assertIn(movie_id, seen)

    def test_neighbors_share_at_least_three_high_ratings(self) -> None:
        data = build_sample()

        def high(user_id: int) -> set[int]:
            return {
                int(row["movieId"])
                for row in data["ratings"]
                if row["userId"] == user_id and float(row["rating"]) > 4
            }

        self.assertGreaterEqual(len(high(1) & high(2)), 3)
        self.assertGreaterEqual(len(high(1) & high(3)), 3)
        peer_unseen = {
            int(row["movieId"])
            for row in data["ratings"]
            if row["userId"] in {2, 3} and float(row["rating"]) >= 4
        } - high(1)
        self.assertTrue(set(EXPECTED_CF_MOVIES) <= peer_unseen)

    def test_resolve_data_dir_finds_movies_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "ml-32m"
            nested.mkdir()
            (nested / "movies.csv").write_text("movieId,title,genres\n", encoding="utf-8")
            self.assertEqual(resolve_data_dir(root), nested.resolve())
            self.assertEqual(resolve_data_dir(nested), nested.resolve())

    def test_write_sample_creates_the_three_csv_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = write_sample(Path(tmp) / "sample")
            for name in ("movies.csv", "ratings.csv", "tags.csv"):
                self.assertTrue((out / name).is_file())


if __name__ == "__main__":
    unittest.main()
