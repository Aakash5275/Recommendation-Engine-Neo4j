"""CSV preparation tests."""

from __future__ import annotations

import unittest

import pandas as pd

from src.transform import movie_rows, parse_genres, rating_rows, tag_rows


class TransformTests(unittest.TestCase):
    def test_parse_genres_splits_pipes_and_drops_placeholder(self) -> None:
        self.assertEqual(parse_genres("Sci-Fi|Action|Sci-Fi"), ["Sci-Fi", "Action"])
        self.assertEqual(parse_genres("(no genres listed)"), [])
        self.assertEqual(parse_genres(None), [])

    def test_movie_rows_merge_duplicate_ids(self) -> None:
        frame = pd.DataFrame(
            [
                {"movieId": 1, "title": "Alpha", "genres": "Sci-Fi|Action"},
                {"movieId": 1, "title": "Alpha", "genres": "Drama"},
                {"movieId": 2, "title": " ", "genres": "Comedy"},
            ]
        )
        prepared = movie_rows(frame)
        self.assertEqual(prepared.skipped, 1)
        self.assertEqual(len(prepared.rows), 1)
        self.assertEqual(prepared.rows[0]["genres"], ["Sci-Fi", "Action", "Drama"])

    def test_rating_rows_reject_out_of_range_and_keep_last_duplicate(self) -> None:
        frame = pd.DataFrame(
            [
                {"userId": 1, "movieId": 6, "rating": 5.0, "timestamp": 10},
                {"userId": 1, "movieId": 6, "rating": 4.5, "timestamp": 11},
                {"userId": 1, "movieId": 7, "rating": 9.0, "timestamp": 12},
            ]
        )
        prepared = rating_rows(frame)
        self.assertEqual(prepared.skipped, 1)
        self.assertEqual(prepared.rows, [
            {"userId": 1, "movieId": 6, "rating": 4.5, "timestamp": 11},
        ])

    def test_tag_rows_normalize_whitespace(self) -> None:
        frame = pd.DataFrame(
            [
                {"userId": 1, "movieId": 1, "tag": "  mind-bending  ", "timestamp": 3},
                {"userId": 1, "movieId": 1, "tag": "", "timestamp": 4},
            ]
        )
        prepared = tag_rows(frame)
        self.assertEqual(prepared.skipped, 1)
        self.assertEqual(prepared.rows[0]["tag"], "mind-bending")


if __name__ == "__main__":
    unittest.main()
