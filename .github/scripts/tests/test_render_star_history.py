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
fetch_stargazers = render_star_history.fetch_stargazers
FetchError = render_star_history.FetchError


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


class TestFetchStargazers(unittest.TestCase):
    """Tests for fetch_stargazers GraphQL response parsing.

    Coverage added 2026-08-15 after run #31863104558 failed with
    `Resource not accessible by personal access token` (the GH_STAR_TOKEN
    had insufficient scopes for GraphQL `repository.stargazers`). The
    real failure path was completely uncovered before; this class
    locks the behaviour so any future token/permission/rate-limit
    failure raises FetchError (which main() converts to a degraded
    metrics file + exit 0) instead of sys.exit(1).
    """

    def _mock_response(self, status_code=200, payload=None, text=None):
        """Build a mock requests.post response that returns the given payload."""
        r = MagicMock()
        r.status_code = status_code
        if text is not None:
            r.text = text
        if payload is not None:
            r.json.return_value = payload
        else:
            r.json.side_effect = ValueError("not JSON")
        return r

    def _ok_payload(self, edges, has_next_page=False, end_cursor=None, remaining=9999):
        return {
            "data": {
                "repository": {
                    "stargazers": {
                        "edges": edges,
                        "pageInfo": {"hasNextPage": has_next_page, "endCursor": end_cursor},
                    }
                },
                "rateLimit": {"remaining": remaining, "resetAt": "2026-08-15T00:00:00Z"},
            }
        }

    def test_success_single_page_returns_sorted_dates(self):
        """Single-page success returns dates sorted ascending."""
        edges = [
            {"starredAt": "2026-01-03T00:00:00Z", "node": {"login": "b"}},
            {"starredAt": "2026-01-01T00:00:00Z", "node": {"login": "a"}},
            {"starredAt": "2026-01-02T00:00:00Z", "node": {"login": "c"}},
        ]
        resp = self._mock_response(payload=self._ok_payload(edges))

        with patch("requests.post", return_value=resp) as mock_post:
            dates = fetch_stargazers("AleksNeStu/ai-real-estate-assistant", "fake_token")

        self.assertEqual(len(dates), 3)
        self.assertLessEqual(dates[0], dates[1])
        self.assertLessEqual(dates[1], dates[2])
        # All returned timestamps are UTC-aware
        for d in dates:
            self.assertEqual(d.tzinfo, timezone.utc)
        # Verify the GraphQL request was sent to /graphql
        called_args, _ = mock_post.call_args
        self.assertIn("/graphql", called_args[0])

    def test_success_paginates_until_has_next_page_false(self):
        """Multi-page success walks the cursor until hasNextPage=false."""
        page1 = self._mock_response(payload=self._ok_payload(
            [{"starredAt": "2026-01-01T00:00:00Z", "node": {"login": "a"}}],
            has_next_page=True, end_cursor="CURSOR_1",
        ))
        page2 = self._mock_response(payload=self._ok_payload(
            [{"starredAt": "2026-01-02T00:00:00Z", "node": {"login": "b"}}],
            has_next_page=False, end_cursor=None,
        ))

        with patch("requests.post", side_effect=[page1, page2]) as mock_post:
            dates = fetch_stargazers("AleksNeStu/ai-real-estate-assistant", "fake_token")

        self.assertEqual(len(dates), 2)
        self.assertEqual(mock_post.call_count, 2)

    def test_http_401_raises_fetch_error(self):
        """HTTP 401 raises FetchError with the HTTP code in the message."""
        resp = self._mock_response(status_code=401, text="bad credentials")

        with patch("requests.post", return_value=resp):
            with self.assertRaises(FetchError) as ctx:
                fetch_stargazers("AleksNeStu/ai-real-estate-assistant", "fake_token")

        self.assertIn("HTTP 401", str(ctx.exception))

    def test_http_403_raises_fetch_error(self):
        """HTTP 403 raises FetchError (this is the GitHub PAT-too-tight class)."""
        resp = self._mock_response(status_code=403, text="forbidden")

        with patch("requests.post", return_value=resp):
            with self.assertRaises(FetchError) as ctx:
                fetch_stargazers("AleksNeStu/ai-real-estate-assistant", "fake_token")

        self.assertIn("HTTP 403", str(ctx.exception))

    def test_graphql_errors_raises_fetch_error(self):
        """GraphQL errors[] in the payload (HTTP 200) raise FetchError.

        This is the actual shape of the run #31863104558 failure: HTTP 200
        with `errors: [{type: FORBIDDEN, ...}]`. The original script
        sys.exit(1)'d here; the new contract raises FetchError.
        """
        forbidden = self._mock_response(
            status_code=200,
            payload={
                "errors": [
                    {
                        "type": "FORBIDDEN",
                        "path": ["repository", "stargazers"],
                        "message": "Resource not accessible by personal access token",
                    }
                ],
                "data": {"repository": None, "rateLimit": {"remaining": 9999}},
            },
        )

        with patch("requests.post", return_value=forbidden):
            with self.assertRaises(FetchError) as ctx:
                fetch_stargazers("AleksNeStu/ai-real-estate-assistant", "fake_token")

        self.assertIn("GraphQL errors", str(ctx.exception))
        self.assertIn("FORBIDDEN", str(ctx.exception))

    def test_rate_limit_below_floor_raises_fetch_error(self):
        """GraphQL rateLimit.remaining below RATE_LIMIT_FLOOR raises FetchError."""
        resp = self._mock_response(payload=self._ok_payload(
            [], has_next_page=False, remaining=5,  # floor=10
        ))

        with patch("requests.post", return_value=resp):
            with self.assertRaises(FetchError) as ctx:
                fetch_stargazers("AleksNeStu/ai-real-estate-assistant", "fake_token")

        self.assertIn("rate-limit", str(ctx.exception).lower())
        self.assertIn("5", str(ctx.exception))

    def test_missing_repository_raises_fetch_error(self):
        """GraphQL response with no `repository` (None or absent) raises FetchError."""
        resp = self._mock_response(payload={
            "data": {"repository": None, "rateLimit": {"remaining": 9999}},
        })

        with patch("requests.post", return_value=resp):
            with self.assertRaises(FetchError) as ctx:
                fetch_stargazers("AleksNeStu/ai-real-estate-assistant", "fake_token")

        self.assertIn("repository not found", str(ctx.exception))

    def test_non_json_response_raises_fetch_error(self):
        """HTTP 200 with non-JSON body raises FetchError."""
        resp = self._mock_response(status_code=200, payload=None, text="<html>not json</html>")

        with patch("requests.post", return_value=resp):
            with self.assertRaises(FetchError) as ctx:
                fetch_stargazers("AleksNeStu/ai-real-estate-assistant", "fake_token")

        self.assertIn("non-JSON", str(ctx.exception))

    def test_invalid_repo_format_raises_fetch_error(self):
        """Repo string without `owner/name` shape raises FetchError immediately."""
        with self.assertRaises(FetchError) as ctx:
            fetch_stargazers("no-slash", "fake_token")

        self.assertIn("owner/name", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
