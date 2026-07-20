#!/usr/bin/env python3
"""Tests for render_star_history.py growth metrics functions.

Run:
    python -m unittest discover -s .github/scripts/tests -p "test_render_star_history.py" -v
"""
import unittest
import sys
import importlib.util
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

# Load the module - use relative path from test file to sibling script
test_dir = Path(__file__).parent
script_path = test_dir.parent / "render_star_history.py"
spec = importlib.util.spec_from_file_location("render_star_history", script_path)
render_star_history = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render_star_history)

summarize_growth = render_star_history.summarize_growth
fetch_optional_traffic = render_star_history.fetch_optional_traffic


class TestSummarizeGrowth(unittest.TestCase):
    """Tests for summarize_growth function."""

    def test_empty_dates_yields_all_windows_zero(self):
        """Empty dates list yields all star windows equal to 0."""
        now = datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc)
        result = summarize_growth([], now)

        self.assertEqual(result["new_stars_1d"], 0)
        self.assertEqual(result["new_stars_7d"], 0)
        self.assertEqual(result["new_stars_30d"], 0)
        self.assertEqual(result["total_stars"], 0)

    def test_one_star_inside_24h_contributes_to_all_windows(self):
        """One star inside 24h contributes to 1d/7d/30d windows."""
        now = datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc)
        star_date = datetime(2026, 7, 20, 11, 0, 0, tzinfo=timezone.utc)
        dates = [star_date]

        result = summarize_growth(dates, now)

        self.assertEqual(result["new_stars_1d"], 1)
        self.assertEqual(result["new_stars_7d"], 1)
        self.assertEqual(result["new_stars_30d"], 1)
        self.assertEqual(result["total_stars"], 1)

    def test_star_older_than_30d_not_counted(self):
        """Star older than 30 days does not contribute to any window."""
        now = datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc)
        star_date = datetime(2026, 6, 19, 11, 0, 0, tzinfo=timezone.utc)
        dates = [star_date]

        result = summarize_growth(dates, now)

        self.assertEqual(result["new_stars_1d"], 0)
        self.assertEqual(result["new_stars_7d"], 0)
        self.assertEqual(result["new_stars_30d"], 0)
        self.assertEqual(result["total_stars"], 1)

    def test_star_between_7d_and_30d(self):
        """Star between 7 and 30 days contributes to 30d only."""
        now = datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc)
        star_date = datetime(2026, 7, 10, 11, 0, 0, tzinfo=timezone.utc)
        dates = [star_date]

        result = summarize_growth(dates, now)

        self.assertEqual(result["new_stars_1d"], 0)
        self.assertEqual(result["new_stars_7d"], 0)
        self.assertEqual(result["new_stars_30d"], 1)
        self.assertEqual(result["total_stars"], 1)

    def test_star_between_1d_and_7d(self):
        """Star between 1 and 7 days contributes to 7d and 30d."""
        now = datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc)
        star_date = datetime(2026, 7, 17, 11, 0, 0, tzinfo=timezone.utc)
        dates = [star_date]

        result = summarize_growth(dates, now)

        self.assertEqual(result["new_stars_1d"], 0)
        self.assertEqual(result["new_stars_7d"], 1)
        self.assertEqual(result["new_stars_30d"], 1)
        self.assertEqual(result["total_stars"], 1)

    def test_boundary_utc_aware(self):
        """Boundary dates are UTC-aware - star exactly at 1d/7d/30d boundary."""
        now = datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc)
        star_date = datetime(2026, 7, 19, 12, 0, 0, tzinfo=timezone.utc)
        dates = [star_date]

        result = summarize_growth(dates, now)

        self.assertEqual(result["new_stars_1d"], 1)
        self.assertEqual(result["new_stars_7d"], 1)
        self.assertEqual(result["new_stars_30d"], 1)

    def test_multiple_stars_count_correctly(self):
        """Multiple stars contribute correctly to their respective windows."""
        now = datetime(2026, 7, 20, 12, 0, 0, tzinfo=timezone.utc)
        dates = [
            datetime(2026, 7, 20, 11, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 7, 15, 11, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 6, 25, 11, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 6, 10, 11, 0, 0, tzinfo=timezone.utc),
        ]

        result = summarize_growth(dates, now)

        self.assertEqual(result["new_stars_1d"], 1)
        self.assertEqual(result["new_stars_7d"], 2)
        self.assertEqual(result["new_stars_30d"], 3)
        self.assertEqual(result["total_stars"], 4)


class TestFetchOptionalTraffic(unittest.TestCase):
    """Tests for fetch_optional_traffic function."""

    def test_403_returns_traffic_available_false(self):
        """A 403 traffic response returns traffic_available: false without failing."""
        mock_response = MagicMock()
        mock_response.status_code = 403

        with patch('requests.get') as mock_get:
            mock_get.return_value = mock_response

            result = fetch_optional_traffic(
                "AleksNeStu/ai-real-estate-assistant",
                "fake_token"
            )

            self.assertEqual(result["traffic_available"], False)
            self.assertIn("traffic_error", result)

    def test_404_returns_traffic_available_false(self):
        """A 404 traffic response returns traffic_available: false without failing."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch('requests.get') as mock_get:
            mock_get.return_value = mock_response

            result = fetch_optional_traffic(
                "AleksNeStu/ai-real-estate-assistant",
                "fake_token"
            )

            self.assertEqual(result["traffic_available"], False)
            self.assertIn("traffic_error", result)

    def test_429_returns_traffic_available_false(self):
        """A 429 rate-limit traffic response returns traffic_available: false."""
        mock_response = MagicMock()
        mock_response.status_code = 429

        with patch('requests.get') as mock_get:
            mock_get.return_value = mock_response

            result = fetch_optional_traffic(
                "AleksNeStu/ai-real-estate-assistant",
                "fake_token"
            )

            self.assertEqual(result["traffic_available"], False)
            self.assertIn("traffic_error", result)

    def test_200_returns_traffic_available_true(self):
        """A 200 traffic response returns traffic_available: true with views data."""
        mock_views_response = MagicMock()
        mock_views_response.status_code = 200
        mock_views_response.json.return_value = {
            "views": [
                {"timestamp": "2026-07-19T00:00:00Z", "count": 100, "uniques": 50}
            ],
            "count": 100,
            "uniques": 50
        }

        mock_ref_response = MagicMock()
        mock_ref_response.status_code = 200
        mock_ref_response.json.return_value = {
            "referrers": [
                {"referrer": "github.com", "count": 80, "uniques": 40}
            ]
        }

        with patch('requests.get') as mock_get:
            mock_get.side_effect = [mock_views_response, mock_ref_response]

            result = fetch_optional_traffic(
                "AleksNeStu/ai-real-estate-assistant",
                "fake_token"
            )

            self.assertEqual(result["traffic_available"], True)
            self.assertEqual(result["views_14d"], 100)
            self.assertEqual(result["unique_visitors_14d"], 50)
            self.assertIn("referrers", result)


if __name__ == "__main__":
    unittest.main()
