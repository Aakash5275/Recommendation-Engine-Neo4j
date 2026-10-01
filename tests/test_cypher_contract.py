"""Cypher files stay aligned with the parameter builders."""

from __future__ import annotations

import unittest

from src.cypher_io import load_query, parameter_names, split_statements
from src.config import CYPHER_DIR
from src.recommend import RecommendParams


class CypherContractTests(unittest.TestCase):
    def test_constraints_cover_user_movie_genre_and_tag(self) -> None:
        script = (CYPHER_DIR / "constraints.cypher").read_text(encoding="utf-8")
        statements = split_statements(script)
        self.assertEqual(len(statements), 4)
        joined = "\n".join(statements)
        for label in ("User", "Movie", "Genre", "Tag"):
            self.assertIn(label, joined)
        self.assertIn("userId IS UNIQUE", joined)
        self.assertIn("movieId IS UNIQUE", joined)

    def test_parameter_names_ignore_comments(self) -> None:
        query = "// uses $ignored\nMATCH (n {id: $userId}) RETURN n"
        self.assertEqual(parameter_names(query), {"userId"})

    def test_strategy_queries_match_parameter_builders(self) -> None:
        params = RecommendParams()
        pairs = (
            ("user_based_cf.cypher", params.cf_parameters(1)),
            ("content_hybrid.cypher", params.content_parameters(1)),
            ("cf_path.cypher", params.cf_path_parameters(1, 6)),
            ("content_path.cypher", params.content_path_parameters(1, 6)),
            ("user_profile.cypher", {"userId": 1}),
            ("user_genres.cypher", {"userId": 1, "minRating": 4.0}),
        )
        for filename, provided in pairs:
            query = load_query(filename)
            self.assertIn("USING INDEX", query, filename)
            self.assertEqual(parameter_names(query), set(provided), filename)

    def test_load_queries_use_batched_unwind(self) -> None:
        for filename, token in (
            ("load_movies.cypher", "IN_GENRE"),
            ("load_ratings.cypher", "RATED"),
            ("load_tags.cypher", "HAS_TAG"),
        ):
            query = load_query(filename)
            self.assertIn("UNWIND $rows", query)
            self.assertIn(token, query)
            self.assertEqual(parameter_names(query), {"rows"})


if __name__ == "__main__":
    unittest.main()
