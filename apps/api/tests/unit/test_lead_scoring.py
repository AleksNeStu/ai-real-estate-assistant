"""Tests for the lead scoring engine (pure calculation methods).

Tests the scoring formulas without requiring database access.
"""

from services.lead_scoring import (
    SCORING_WEIGHTS,
    LeadScoringEngine,
    ScoringFactors,
)


class TestSearchActivityScore:
    """Tests for _calculate_search_activity_score."""

    @staticmethod
    def _make_engine():
        """Create engine with mocked session (only pure methods used)."""
        from unittest.mock import MagicMock

        return LeadScoringEngine(session=MagicMock())

    def test_zero_searches(self):
        engine = TestSearchActivityScore._make_engine()
        factors = ScoringFactors(search_count=0)
        score = engine._calculate_search_activity_score(factors)
        assert score == 0

    def test_low_searches(self):
        engine = TestSearchActivityScore._make_engine()
        factors = ScoringFactors(search_count=3)
        score = engine._calculate_search_activity_score(factors)
        assert score == 10  # 1-5 searches = 10 points

    def test_many_searches(self):
        engine = TestSearchActivityScore._make_engine()
        factors = ScoringFactors(search_count=25)
        score = engine._calculate_search_activity_score(factors)
        assert score >= 25  # 20+ searches = 25 points for search count

    def test_saved_searches_boost(self):
        engine = TestSearchActivityScore._make_engine()
        factors = ScoringFactors(saved_search_count=2)
        score = engine._calculate_search_activity_score(factors)
        assert score >= 20  # 2 saved * 10 = 20 points

    def test_recent_searches_boost(self):
        engine = TestSearchActivityScore._make_engine()
        factors = ScoringFactors(recent_search_count_7d=3)
        score = engine._calculate_search_activity_score(factors)
        assert score >= 15  # 3 recent * 5 = 15 points

    def test_max_100(self):
        engine = TestSearchActivityScore._make_engine()
        factors = ScoringFactors(
            search_count=50,
            saved_search_count=10,
            recent_search_count_7d=20,
            advanced_filter_count=10,
        )
        score = engine._calculate_search_activity_score(factors)
        assert score <= 100


class TestEngagementScore:
    """Tests for _calculate_engagement_score."""

    @staticmethod
    def _make_engine():
        from unittest.mock import MagicMock

        return LeadScoringEngine(session=MagicMock())

    def test_no_engagement(self):
        engine = TestEngagementScore._make_engine()
        factors = ScoringFactors()
        score = engine._calculate_engagement_score(factors)
        assert score == 0

    def test_some_views(self):
        engine = TestEngagementScore._make_engine()
        factors = ScoringFactors(property_views=10)
        score = engine._calculate_engagement_score(factors)
        assert score >= 10  # 6-15 views = 10 points

    def test_heavy_engagement(self):
        engine = TestEngagementScore._make_engine()
        factors = ScoringFactors(
            property_views=60,
            favorites_count=5,
            total_time_spent_minutes=90,
            return_visits=6,
        )
        score = engine._calculate_engagement_score(factors)
        assert score >= 70  # Should be high
        assert score <= 100

    def test_favorites_cap(self):
        engine = TestEngagementScore._make_engine()
        factors = ScoringFactors(favorites_count=10)
        score = engine._calculate_engagement_score(factors)
        # Favorites capped at 30 points (5 * 6)
        assert score <= 30


class TestIntentScore:
    """Tests for _calculate_intent_score."""

    @staticmethod
    def _make_engine():
        from unittest.mock import MagicMock

        return LeadScoringEngine(session=MagicMock())

    def test_no_intent(self):
        engine = TestIntentScore._make_engine()
        factors = ScoringFactors()
        score = engine._calculate_intent_score(factors)
        assert score == 0

    def test_inquiry_high_intent(self):
        engine = TestIntentScore._make_engine()
        factors = ScoringFactors(
            inquiries_submitted=1,
            has_email=True,
            has_phone=True,
        )
        score = engine._calculate_intent_score(factors)
        assert (
            score >= 20
        )  # 40 for inquiry + 6 for profile, but 50% recency penalty (days_since_last_activity=999 > 30)

    def test_viewing_scheduled(self):
        engine = TestIntentScore._make_engine()
        factors = ScoringFactors(viewings_scheduled=1)
        score = engine._calculate_intent_score(factors)
        assert (
            score >= 40
        )  # Viewing floors to 80, but 50% recency penalty (days_since_last_activity=999 > 30)

    def test_recency_penalty_14_days(self):
        engine = TestIntentScore._make_engine()
        factors_active = ScoringFactors(
            inquiries_submitted=1,
            days_since_last_activity=5,
        )
        factors_inactive = ScoringFactors(
            inquiries_submitted=1,
            days_since_last_activity=20,
        )
        score_active = engine._calculate_intent_score(factors_active)
        score_inactive = engine._calculate_intent_score(factors_inactive)
        assert score_inactive < score_active  # 25% penalty

    def test_recency_penalty_30_days(self):
        engine = TestIntentScore._make_engine()
        factors = ScoringFactors(
            inquiries_submitted=1,
            days_since_last_activity=45,
        )
        score = engine._calculate_intent_score(factors)
        # 50% penalty after 30 days
        assert score < 40  # 40 * 0.5 = 20

    def test_profile_completeness(self):
        engine = TestIntentScore._make_engine()
        factors = ScoringFactors(
            has_email=True,
            has_phone=True,
            has_name=True,
            has_budget=True,
        )
        score = engine._calculate_intent_score(factors)
        assert (
            score == 5
        )  # 3 + 3 + 2 + 2 = 10, but 50% recency penalty (days_since_last_activity=999 > 30)


class TestGenerateRecommendations:
    """Tests for _generate_recommendations."""

    @staticmethod
    def _make_engine():
        from unittest.mock import MagicMock

        return LeadScoringEngine(session=MagicMock())

    def test_high_score_recommendation(self):
        engine = TestGenerateRecommendations._make_engine()
        factors = ScoringFactors(inquiries_submitted=1, has_email=True)
        recs = engine._generate_recommendations(factors, total_score=85)
        assert any("senior agent" in r.lower() for r in recs)

    def test_warm_score_recommendation(self):
        engine = TestGenerateRecommendations._make_engine()
        factors = ScoringFactors(inquiries_submitted=0, favorites_count=5, has_email=True)
        recs = engine._generate_recommendations(factors, total_score=65)
        assert any("proactive outreach" in r.lower() for r in recs)

    def test_max_5_recommendations(self):
        engine = TestGenerateRecommendations._make_engine()
        factors = ScoringFactors(
            inquiries_submitted=1,
            viewings_scheduled=1,
            contact_requests=1,
            favorites_count=5,
            saved_search_count=3,
            has_email=True,
        )
        recs = engine._generate_recommendations(factors, total_score=90)
        assert len(recs) <= 5


class TestScoringWeights:
    """Verify scoring weights sum to 1.0."""

    def test_weights_sum_to_one(self):
        total = sum(SCORING_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_weights_are_positive(self):
        for key, weight in SCORING_WEIGHTS.items():
            assert weight > 0, f"{key} weight must be positive"
