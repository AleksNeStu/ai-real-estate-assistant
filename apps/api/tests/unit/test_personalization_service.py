"""Unit tests for PersonalizationService."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.personalization_service import (
    DeclaredPreferences,
    PersonalizationService,
    UserPreferences,
    _parse_budget,
    _scale_amount,
)


def _make_profile(**overrides):
    """Create a mock UserPreferenceProfile."""
    defaults = {
        "user_id": "user-001",
        "preferred_cities": [],
        "preferred_price_min": None,
        "preferred_price_max": None,
        "preferred_rooms": [],
        "preferred_property_types": [],
        "amenity_weights": {},
        "preference_embedding": None,
        "view_count": 0,
        "favorite_count": 0,
    }
    defaults.update(overrides)
    profile = MagicMock()
    for k, v in defaults.items():
        setattr(profile, k, v)
    return profile


def _make_memory(*facts):
    """Create a mock BuyerMemoryService that recalls the given facts."""
    memory = MagicMock()
    memory.recall_for_user = AsyncMock(return_value=list(facts))
    return memory


def _fact(kind, content, listing_id=None):
    """Create a fact the way the buyer-memory service hands them over."""
    return SimpleNamespace(kind=kind, content=content, listing_id=listing_id, confidence=1.0)


class TestUserPreferencesFromModel:
    """Tests for UserPreferences.from_model classmethod."""

    def test_converts_cities_from_list_to_dict(self):
        """Converts [{"city": "Kraków", "weight": 0.8}] to {"Kraków": 0.8}."""
        profile = _make_profile(
            preferred_cities=[{"city": "Kraków", "weight": 0.8}],
            view_count=5,
        )
        prefs = UserPreferences.from_model(profile)

        assert prefs.preferred_cities == {"Kraków": 0.8}
        assert prefs.view_count == 5
        assert prefs.user_id == "user-001"

    def test_handles_empty_cities(self):
        """Returns empty dict when preferred_cities is empty."""
        profile = _make_profile(preferred_cities=[])
        prefs = UserPreferences.from_model(profile)

        assert prefs.preferred_cities == {}

    def test_handles_none_cities(self):
        """Returns empty dict when preferred_cities is None."""
        profile = _make_profile()
        profile.preferred_cities = None
        prefs = UserPreferences.from_model(profile)

        assert prefs.preferred_cities == {}

    def test_handles_malformed_city_entries(self):
        """Skips entries that don't have both 'city' and 'weight' keys."""
        profile = _make_profile(
            preferred_cities=[
                {"city": "Kraków", "weight": 0.5},
                {"name": "Warszawa"},  # Missing 'city' and 'weight'
            ]
        )
        prefs = UserPreferences.from_model(profile)

        assert prefs.preferred_cities == {"Kraków": 0.5}

    def test_preserves_price_range(self):
        """Preserves price_min and price_max from profile."""
        profile = _make_profile(
            preferred_price_min=100000.0,
            preferred_price_max=500000.0,
        )
        prefs = UserPreferences.from_model(profile)

        assert prefs.preferred_price_min == 100000.0
        assert prefs.preferred_price_max == 500000.0


class TestGetUserPreferences:
    """Tests for get_user_preferences method."""

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_user(self):
        """Returns None when user has no preference profile."""
        mock_session = AsyncMock()
        # session.execute() returns awaitable → mock_result (MagicMock)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        service = PersonalizationService(mock_session)
        result = await service.get_user_preferences("unknown-user")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_preferences_for_existing_user(self):
        """Returns UserPreferences when profile exists."""
        profile = _make_profile(view_count=10, favorite_count=3)
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = profile
        mock_session.execute.return_value = mock_result

        service = PersonalizationService(mock_session)
        result = await service.get_user_preferences("user-001")

        assert result is not None
        assert result.user_id == "user-001"
        assert result.view_count == 10


class TestGetOrCreatePreferences:
    """Tests for get_or_create_preferences method."""

    @pytest.mark.asyncio
    async def test_returns_existing_preferences(self):
        """Returns existing preferences without creating new ones."""
        profile = _make_profile(view_count=5)
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = profile
        mock_session.execute.return_value = mock_result

        service = PersonalizationService(mock_session)
        result = await service.get_or_create_preferences("user-001")

        assert result.view_count == 5
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_new_preferences_when_missing(self):
        """Creates and returns new preferences when user has none."""
        mock_session = AsyncMock()
        # First call: get_user_preferences returns None
        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None
        # Second call: refresh after create
        new_profile = _make_profile(view_count=0)
        mock_result_new = MagicMock()
        mock_result_new.scalar_one_or_none.return_value = new_profile

        mock_session.execute.side_effect = [mock_result_none, mock_result_new]

        service = PersonalizationService(mock_session)
        result = await service.get_or_create_preferences("new-user")

        assert result is not None
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


class TestUpdatePreferencesFromInteraction:
    """Tests for update_preferences_from_interaction method."""

    @pytest.mark.asyncio
    async def test_updates_city_preference_on_view(self):
        """Adds city weight on view interaction."""
        profile = _make_profile(
            preferred_cities={},
            preferred_rooms=[],
            preferred_property_types=[],
            amenity_weights={},
            view_count=2,
        )
        mock_session = AsyncMock()
        # First call: get_or_create_preferences → get_user_preferences
        mock_result_first = MagicMock()
        mock_result_first.scalar_one_or_none.return_value = profile
        # Second call: update_preferences → re-fetch profile
        mock_result_second = MagicMock()
        mock_result_second.scalar_one_or_none.return_value = profile

        mock_session.execute.side_effect = [mock_result_first, mock_result_second]

        service = PersonalizationService(mock_session)
        await service.update_preferences_from_interaction(
            "user-001",
            {"city": "Kraków"},
            "view",
        )

        assert profile.view_count == 3
        assert "Kraków" in profile.preferred_cities
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_favorite_gets_higher_weight(self):
        """Favorite interaction uses FAVORITE_WEIGHT (2.0)."""
        profile = _make_profile(
            preferred_cities={},
            preferred_rooms=[],
            preferred_property_types=[],
            amenity_weights={},
            view_count=0,
            favorite_count=0,
        )
        mock_session = AsyncMock()
        mock_result_first = MagicMock()
        mock_result_first.scalar_one_or_none.return_value = profile
        mock_result_second = MagicMock()
        mock_result_second.scalar_one_or_none.return_value = profile
        mock_session.execute.side_effect = [mock_result_first, mock_result_second]

        service = PersonalizationService(mock_session)
        await service.update_preferences_from_interaction(
            "user-001",
            {"city": "Warszawa"},
            "favorite",
        )

        assert profile.favorite_count == 1
        # Weight should be FAVORITE_WEIGHT * 0.1 = 0.2
        assert profile.preferred_cities["Warszawa"] == 0.2

    @pytest.mark.asyncio
    async def test_updates_price_range(self):
        """Adjusts price range based on viewed property price."""
        profile = _make_profile(
            preferred_price_min=None,
            preferred_price_max=None,
            preferred_cities={},
            preferred_rooms=[],
            preferred_property_types=[],
            amenity_weights={},
        )
        mock_session = AsyncMock()
        mock_result_first = MagicMock()
        mock_result_first.scalar_one_or_none.return_value = profile
        mock_result_second = MagicMock()
        mock_result_second.scalar_one_or_none.return_value = profile
        mock_session.execute.side_effect = [mock_result_first, mock_result_second]

        service = PersonalizationService(mock_session)
        await service.update_preferences_from_interaction(
            "user-001",
            {"price": 300000},
            "view",
        )

        assert profile.preferred_price_min == 300000.0
        assert profile.preferred_price_max == 300000.0

    @pytest.mark.asyncio
    async def test_updates_rooms_preference(self):
        """Adds room count to preferred_rooms if not already there."""
        profile = _make_profile(
            preferred_rooms=[],
            preferred_cities={},
            preferred_property_types=[],
            amenity_weights={},
        )
        mock_session = AsyncMock()
        mock_result_first = MagicMock()
        mock_result_first.scalar_one_or_none.return_value = profile
        mock_result_second = MagicMock()
        mock_result_second.scalar_one_or_none.return_value = profile
        mock_session.execute.side_effect = [mock_result_first, mock_result_second]

        service = PersonalizationService(mock_session)
        await service.update_preferences_from_interaction(
            "user-001",
            {"rooms": 3},
            "view",
        )

        assert 3 in profile.preferred_rooms


class TestCalculatePersonalizationBoost:
    """Tests for calculate_personalization_boost method."""

    def test_returns_zero_boost_below_min_interactions(self):
        """Returns zero boost when total interactions < MIN_INTERACTIONS."""
        mock_session = AsyncMock()
        service = PersonalizationService(mock_session)

        prefs = UserPreferences(user_id="u1", view_count=1, favorite_count=0)
        prop = {"id": "p1", "city": "Kraków", "price": 300000}

        boost = service.calculate_personalization_boost(prop, prefs)

        assert boost.total_boost == 0.0
        assert boost.city_boost == 0.0

    def test_city_boost_when_matching(self):
        """Applies city boost when property city matches preference."""
        mock_session = AsyncMock()
        service = PersonalizationService(mock_session)

        prefs = UserPreferences(
            user_id="u1",
            view_count=5,
            favorite_count=2,
            preferred_cities={"Kraków": 0.8},
        )
        prop = {"id": "p1", "city": "Kraków"}

        boost = service.calculate_personalization_boost(prop, prefs)

        assert boost.city_boost == pytest.approx(0.24)  # 0.8 * 0.3

    def test_price_boost_when_in_range(self):
        """Applies positive price boost when price is within preferred range."""
        mock_session = AsyncMock()
        service = PersonalizationService(mock_session)

        prefs = UserPreferences(
            user_id="u1",
            view_count=5,
            favorite_count=2,
            preferred_price_min=200000,
            preferred_price_max=400000,
        )
        prop = {"id": "p1", "price": 300000}

        boost = service.calculate_personalization_boost(prop, prefs)

        assert boost.price_boost == 0.2

    def test_rooms_boost_when_matching(self):
        """Applies rooms boost when room count matches preference."""
        mock_session = AsyncMock()
        service = PersonalizationService(mock_session)

        prefs = UserPreferences(
            user_id="u1",
            view_count=10,
            preferred_rooms=[2, 3],
        )
        prop = {"id": "p1", "rooms": 3}

        boost = service.calculate_personalization_boost(prop, prefs)

        assert boost.rooms_boost == 0.15

    def test_property_type_boost_when_matching(self):
        """Applies type boost when property type matches preference."""
        mock_session = AsyncMock()
        service = PersonalizationService(mock_session)

        prefs = UserPreferences(
            user_id="u1",
            view_count=10,
            preferred_property_types=["apartment"],
        )
        prop = {"id": "p1", "property_type": "apartment"}

        boost = service.calculate_personalization_boost(prop, prefs)

        assert boost.type_boost == 0.2

    def test_amenity_boost(self):
        """Applies amenity boost based on matching amenities."""
        mock_session = AsyncMock()
        service = PersonalizationService(mock_session)

        prefs = UserPreferences(
            user_id="u1",
            view_count=10,
            amenity_weights={"parking": 0.8, "balcony": 0.5},
        )
        prop = {"id": "p1", "amenities": ["parking", "balcony"]}

        boost = service.calculate_personalization_boost(prop, prefs)

        # (0.8 + 0.5) * 0.1 = 0.13
        assert boost.amenity_boost == pytest.approx(0.13)

    def test_zero_weight_means_no_boost(self):
        """Zero personalization weight results in zero total boost."""
        mock_session = AsyncMock()
        service = PersonalizationService(mock_session)

        prefs = UserPreferences(
            user_id="u1",
            view_count=10,
            preferred_cities={"Kraków": 1.0},
        )
        prop = {"id": "p1", "city": "Kraków"}

        boost = service.calculate_personalization_boost(prop, prefs, personalization_weight=0.0)

        assert boost.total_boost == 0.0

    def test_no_matching_preferences_gives_zero_component_boosts(self):
        """All component boosts are zero when nothing matches."""
        mock_session = AsyncMock()
        service = PersonalizationService(mock_session)

        prefs = UserPreferences(
            user_id="u1",
            view_count=10,
            preferred_cities={"Kraków": 0.5},
            preferred_price_min=100000,
            preferred_price_max=200000,
            preferred_rooms=[2],
            preferred_property_types=["house"],
        )
        prop = {
            "id": "p1",
            "city": "Warszawa",
            "price": 500000,
            "rooms": 5,
            "property_type": "studio",
        }

        boost = service.calculate_personalization_boost(prop, prefs)

        assert boost.city_boost == 0.0
        assert boost.rooms_boost == 0.0
        assert boost.type_boost == 0.0


class TestCalculatePreferenceEmbedding:
    """Tests for calculate_preference_embedding method."""

    @pytest.mark.asyncio
    async def test_returns_none_not_implemented(self):
        """Returns None as embedding calculation is not yet implemented."""
        mock_session = AsyncMock()
        service = PersonalizationService(mock_session)

        result = await service.calculate_preference_embedding("user-001", {})

        assert result is None


class TestApplyPersonalizationToResults:
    """Tests for apply_personalization_to_results method."""

    @pytest.mark.asyncio
    async def test_returns_original_results_when_no_preferences(self):
        """Returns unchanged results when user has no preferences."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        service = PersonalizationService(mock_session)
        doc = MagicMock()
        results = [(doc, 0.9)]

        output = await service.apply_personalization_to_results(results, "unknown-user")

        assert output == results

    @pytest.mark.asyncio
    async def test_reranks_results_based_on_preferences(self):
        """Re-sorts results after applying personalization boosts."""
        profile = _make_profile(
            view_count=5,
            favorite_count=3,
            preferred_cities=[{"city": "Kraków", "weight": 1.0}],
        )
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = profile
        mock_session.execute.return_value = mock_result

        service = PersonalizationService(mock_session)

        doc_krakow = MagicMock()
        doc_krakow.metadata = {"id": "p1", "city": "Kraków"}
        doc_warsaw = MagicMock()
        doc_warsaw.metadata = {"id": "p2", "city": "Warszawa"}

        # Warsaw has higher base score, but Kraków gets boost
        results = [(doc_warsaw, 0.9), (doc_krakow, 0.7)]

        output = await service.apply_personalization_to_results(results, "user-001")

        # Verify scores changed (Kraków boosted, Warsaw unchanged)
        warsaw_score = next(s for d, s in output if d == doc_warsaw)
        krakow_score = next(s for d, s in output if d == doc_krakow)
        assert krakow_score > 0.7  # Boosted
        assert warsaw_score == pytest.approx(0.9)  # Unchanged


class TestDeclaredPreferencesParsing:
    """Tests for the free-text parsing of the buyer's declared facts."""

    def test_reads_a_budget_ceiling(self):
        """'up to 500k' is a ceiling of 500000."""
        declared = DeclaredPreferences.from_facts([_fact("budget", "up to 500k")])

        assert declared.price_max == 500000
        assert declared.price_min is None

    def test_reads_a_budget_floor(self):
        """'over 300k' is a floor of 300000."""
        declared = DeclaredPreferences.from_facts([_fact("budget", "at least 300k")])

        assert declared.price_min == 300000
        assert declared.price_max is None

    def test_reads_a_budget_range(self):
        """'between 200k and 400k' is both a floor and a ceiling."""
        declared = DeclaredPreferences.from_facts([_fact("budget", "between 200k and 400k")])

        assert declared.price_min == 200000
        assert declared.price_max == 400000

    def test_reads_a_bare_budget_as_a_ceiling(self):
        """'500k PLN' with no keyword is a ceiling."""
        declared = DeclaredPreferences.from_facts([_fact("budget", "500k PLN")])

        assert declared.price_max == 500000

    def test_ignores_a_budget_it_cannot_read(self):
        """A fact that is not an amount is ignored, not guessed at."""
        declared = DeclaredPreferences.from_facts([_fact("budget", "some time in the spring")])

        assert declared.price_min is None
        assert declared.price_max is None
        assert declared.is_active is False

    def test_ignores_a_room_count_in_a_budget(self):
        """A number below a thousand is not a price."""
        declared = DeclaredPreferences.from_facts([_fact("budget", "3 rooms, up to 500k")])

        assert declared.price_min is None
        assert declared.price_max == 500000

    def test_takes_the_tightest_of_several_budgets(self):
        """Two stated budgets narrow the range to the tightest one."""
        declared = DeclaredPreferences.from_facts(
            [_fact("budget", "up to 500k"), _fact("budget", "up to 400k")]
        )

        assert declared.price_max == 400000

    def test_a_negated_budget_is_a_ceiling(self):
        """'I don't want to spend more than 500k' is a ceiling, not a floor."""
        declared = DeclaredPreferences.from_facts(
            [_fact("budget", "I don't want to spend more than 500k")]
        )

        assert declared.price_max == 500000
        assert declared.price_min is None

    def test_do_not_want_to_spend_more_than_is_a_ceiling(self):
        """'do not want to spend more than 500k' is a ceiling."""
        declared = DeclaredPreferences.from_facts(
            [_fact("budget", "do not want to spend more than 500k")]
        )

        assert declared.price_max == 500000
        assert declared.price_min is None

    def test_no_more_than_is_a_ceiling(self):
        """'no more than 500k' is a ceiling."""
        declared = DeclaredPreferences.from_facts([_fact("budget", "no more than 500k")])

        assert declared.price_max == 500000
        assert declared.price_min is None

    def test_not_more_than_is_a_ceiling(self):
        """'not more than 500k' is a ceiling."""
        declared = DeclaredPreferences.from_facts([_fact("budget", "not more than 500k")])

        assert declared.price_max == 500000
        assert declared.price_min is None

    def test_less_than_is_a_ceiling(self):
        """'less than 500k' is a ceiling."""
        declared = DeclaredPreferences.from_facts([_fact("budget", "less than 500k")])

        assert declared.price_max == 500000
        assert declared.price_min is None

    def test_at_most_is_a_ceiling(self):
        """'at most 500k' is a ceiling."""
        declared = DeclaredPreferences.from_facts([_fact("budget", "at most 500k")])

        assert declared.price_max == 500000
        assert declared.price_min is None

    def test_more_than_is_a_floor(self):
        """'more than 500k' is a floor."""
        declared = DeclaredPreferences.from_facts([_fact("budget", "more than 500k")])

        assert declared.price_min == 500000
        assert declared.price_max is None

    def test_minimum_is_a_floor(self):
        """'minimum 300k' is a floor."""
        declared = DeclaredPreferences.from_facts([_fact("budget", "minimum 300k")])

        assert declared.price_min == 300000
        assert declared.price_max is None

    def test_starting_from_is_a_floor(self):
        """'starting from 300k' is a floor."""
        declared = DeclaredPreferences.from_facts([_fact("budget", "starting from 300k")])

        assert declared.price_min == 300000
        assert declared.price_max is None

    def test_between_is_a_floor_and_a_ceiling(self):
        """'between 300k and 450k' is both."""
        declared = DeclaredPreferences.from_facts([_fact("budget", "between 300k and 450k")])

        assert declared.price_min == 300000
        assert declared.price_max == 450000


class TestAmountReading:
    """Tests for the reader that turns written numbers into amounts."""

    def test_reads_european_thousands_separators(self):
        """'1.500.000' is one and a half million, not one thousand five hundred."""
        assert _scale_amount("1.500.000", None) == 1500000.0

    def test_reads_a_single_thousands_separator(self):
        """'500.000' is five hundred thousand."""
        assert _scale_amount("500.000", None) == 500000.0

    def test_reads_a_space_separated_amount(self):
        """'1 500 000' is one and a half million."""
        assert _parse_budget("1 500 000") == (None, 1500000.0)

    def test_reads_a_decimal_comma(self):
        """'500,50' is five hundred and a half."""
        assert _scale_amount("500,50", None) == 500.5

    def test_reads_a_decimal_point(self):
        """'500.50' is five hundred and a half."""
        assert _scale_amount("500.50", None) == 500.5

    def test_reads_a_comma_thousands_separator(self):
        """'500,000' is five hundred thousand."""
        assert _scale_amount("500,000", None) == 500000.0

    def test_a_european_amount_in_a_fact_is_read_as_a_ceiling(self):
        """'1.500.000 PLN' is a budget of 1.5 million, not of 1500."""
        declared = DeclaredPreferences.from_facts([_fact("budget", "1.500.000 PLN")])

        assert declared.price_max == 1500000.0
        assert declared.price_min is None

    def test_an_unreadable_amount_yields_no_budget(self):
        """A number that cannot be read unambiguously is ignored, not guessed."""
        declared = DeclaredPreferences.from_facts([_fact("budget", "12.05.2024")])

        assert declared.price_min is None
        assert declared.price_max is None
        assert declared.is_active is False

    def test_a_bare_number_is_still_ignored(self):
        """A room count is not a price."""
        assert _parse_budget("500") == (None, None)


class TestRuledOutAreaMatching:
    """Tests for how a ruled-out area is matched against a property."""

    def _declared(self, content):
        return DeclaredPreferences.from_facts([_fact("ruled_out_area", content)])

    def test_a_multi_word_area_does_not_rule_out_a_partial_match(self):
        """'Nowe Miasto' does not rule out the district 'Miasto'."""
        declared = self._declared("Nowe Miasto")

        assert declared.excludes_property({"district": "Miasto"}) is False

    def test_a_multi_word_area_rules_out_the_same_area(self):
        """'Nowe Miasto' rules out the district 'Nowe Miasto'."""
        declared = self._declared("Nowe Miasto")

        assert declared.excludes_property({"district": "Nowe Miasto"}) is True

    def test_a_city_does_not_rule_out_another_district(self):
        """'Kraków' does not rule out the district 'Nowa Huta'."""
        declared = self._declared("Kraków")

        assert declared.excludes_property({"district": "Nowa Huta"}) is False

    def test_a_city_rules_out_the_same_city(self):
        """'Kraków' rules out the city 'Kraków'."""
        declared = self._declared("Kraków")

        assert declared.excludes_property({"city": "Kraków"}) is True

    def test_a_city_rules_out_a_district_that_contains_it(self):
        """'Kraków' rules out the district 'Kraków Stare Miasto'."""
        declared = self._declared("Kraków")

        assert declared.excludes_property({"district": "Kraków Stare Miasto"}) is True

    def test_the_neighborhood_is_checked(self):
        """The neighborhood is a place too - the Chroma metadata carries it."""
        declared = self._declared("Nowe Miasto")

        assert declared.excludes_property({"neighborhood": "Nowe Miasto"}) is True
        assert declared.excludes_property({"neighborhood": "Stary Rynek"}) is False

    def test_a_negated_area_is_still_ruled_out(self):
        """'no Kraków' rules out Kraków - the negation is not the place."""
        declared = self._declared("no Kraków")

        assert declared.excludes_property({"city": "Kraków"}) is True


class TestDeclaredFactsSteerTheRanking:
    """Tests for the declared facts reaching the ranking."""

    @pytest.mark.asyncio
    async def test_ruled_out_area_removes_the_result(self):
        """A ruled-out area removes the result - it is a filter, not a weight."""
        profile = _make_profile(
            view_count=5,
            favorite_count=3,
            preferred_cities=[{"city": "Kraków", "weight": 1.0}],
        )
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = profile
        mock_session.execute.return_value = mock_result

        service = PersonalizationService(
            mock_session, memory_service=_make_memory(_fact("ruled_out_area", "Kraków"))
        )

        doc_krakow = MagicMock()
        doc_krakow.metadata = {"id": "p1", "city": "Kraków"}
        doc_warsaw = MagicMock()
        doc_warsaw.metadata = {"id": "p2", "city": "Warszawa"}

        results = [(doc_krakow, 0.9), (doc_warsaw, 0.8)]

        output = await service.apply_personalization_to_results(results, "user-001")

        # The Kraków result is gone entirely, not pushed down the list.
        assert doc_krakow not in [doc for doc, _ in output]
        assert doc_warsaw in [doc for doc, _ in output]
        assert len(output) == 1

    @pytest.mark.asyncio
    async def test_ruled_out_area_beats_a_strong_behavioural_preference(self):
        """A city the buyer likes is still removed when they ruled it out."""
        profile = _make_profile(
            view_count=20,
            favorite_count=10,
            preferred_cities=[{"city": "Kraków", "weight": 1.0}],
        )
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = profile
        mock_session.execute.return_value = mock_result

        service = PersonalizationService(
            mock_session, memory_service=_make_memory(_fact("ruled_out_area", "no Kraków"))
        )

        doc_krakow = MagicMock()
        doc_krakow.metadata = {"id": "p1", "city": "Kraków"}

        output = await service.apply_personalization_to_results([(doc_krakow, 0.9)], "user-001")

        assert output == []

    def test_stated_budget_beats_a_wider_behavioural_one(self):
        """The stated budget narrows the price range the behaviour suggests."""
        service = PersonalizationService(AsyncMock())

        prefs = UserPreferences(
            user_id="u1",
            view_count=10,
            favorite_count=5,
            preferred_price_min=100000,
            preferred_price_max=800000,
        )
        prop = {"id": "p1", "price": 600000}

        behavioural = service.calculate_personalization_boost(prop, prefs)
        assert behavioural.price_boost == 0.2  # inside the wide behavioural range

        declared = DeclaredPreferences.from_facts([_fact("budget", "up to 500k")])
        stated = service.calculate_personalization_boost(prop, prefs, 0.2, declared)

        # 600k is outside the stated budget, so the boost turns negative.
        # (Changed from "boost < 0" to the exact value: the stated budget is
        # enforced, and the exact number pins the enforcement.)
        assert stated.price_boost == pytest.approx(-0.1)
        assert stated.price_boost != behavioural.price_boost

    def test_a_stated_ceiling_wins_over_a_conflicting_behavioural_range(self):
        """
        A stated budget beats a behavioural one that contradicts it.

        The buyer looked at a 600k flat and then said "up to 500k". The
        stated ceiling wins: the 400k listing is inside it, the 600k and the
        900k listings are above it and are pushed down.
        """
        service = PersonalizationService(AsyncMock())

        prefs = UserPreferences(
            user_id="u1",
            view_count=10,
            favorite_count=5,
            preferred_price_min=600000,
            preferred_price_max=650000,
        )
        declared = DeclaredPreferences.from_facts([_fact("budget", "up to 500k")])

        below = service.calculate_personalization_boost(
            {"id": "p1", "price": 400000}, prefs, 0.2, declared
        )
        at_the_behavioural_floor = service.calculate_personalization_boost(
            {"id": "p2", "price": 600000}, prefs, 0.2, declared
        )
        above = service.calculate_personalization_boost(
            {"id": "p3", "price": 900000}, prefs, 0.2, declared
        )

        # Inside the stated ceiling: not penalised.
        assert below.price_boost == pytest.approx(0.2)
        # Above the stated ceiling: penalised, and not the zero the old
        # code produced for every property.
        assert at_the_behavioural_floor.price_boost == pytest.approx(-0.06)
        assert above.price_boost == pytest.approx(-0.24)

        # The stated budget beats the behavioural one everywhere.
        behavioural_below = service.calculate_personalization_boost(
            {"id": "p1", "price": 400000}, prefs
        )
        behavioural_at_floor = service.calculate_personalization_boost(
            {"id": "p2", "price": 600000}, prefs
        )
        assert below.price_boost > behavioural_below.price_boost
        assert at_the_behavioural_floor.price_boost < behavioural_at_floor.price_boost

    def test_a_stated_floor_wins_over_a_conflicting_behavioural_range(self):
        """A stated floor above the behavioural range is enforced too."""
        service = PersonalizationService(AsyncMock())

        prefs = UserPreferences(
            user_id="u1",
            view_count=10,
            favorite_count=5,
            preferred_price_min=300000,
            preferred_price_max=400000,
        )
        declared = DeclaredPreferences.from_facts([_fact("budget", "at least 700k")])

        below = service.calculate_personalization_boost(
            {"id": "p1", "price": 600000}, prefs, 0.2, declared
        )
        above = service.calculate_personalization_boost(
            {"id": "p2", "price": 800000}, prefs, 0.2, declared
        )

        # Below the stated floor: penalised (the old code penalised nothing).
        assert below.price_boost < 0
        assert above.price_boost == pytest.approx(0.2)

    def test_a_stated_budget_applies_without_a_click_history(self):
        """A buyer who said what they want does not need a click history."""
        service = PersonalizationService(AsyncMock())

        prefs = UserPreferences(user_id="u1", view_count=0, favorite_count=0)
        prop = {"id": "p1", "price": 200000}

        declared = DeclaredPreferences.from_facts([_fact("budget", "up to 500k")])
        boost = service.calculate_personalization_boost(prop, prefs, 0.2, declared)

        assert boost.price_boost == 0.2
        assert boost.total_boost > 0

    def test_a_liked_feature_adds_weight(self):
        """A liked feature weighs like a favourite."""
        service = PersonalizationService(AsyncMock())

        prefs = UserPreferences(user_id="u1", view_count=10)
        prop = {"id": "p1", "amenities": ["balcony"]}

        declared = DeclaredPreferences.from_facts([_fact("liked", "I love the balcony")])
        boost = service.calculate_personalization_boost(prop, prefs, 0.2, declared)

        assert boost.amenity_boost == pytest.approx(0.1)
        assert boost.declared_boost == pytest.approx(0.1)

    @pytest.mark.asyncio
    async def test_with_no_memory_the_behaviour_is_unchanged(self):
        """With no declared facts the ranking is exactly what it was."""
        profile = _make_profile(
            view_count=5,
            favorite_count=3,
            preferred_cities=[{"city": "Kraków", "weight": 1.0}],
        )
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = profile
        mock_session.execute.return_value = mock_result

        service = PersonalizationService(mock_session, memory_service=_make_memory())

        doc_krakow = MagicMock()
        doc_krakow.metadata = {"id": "p1", "city": "Kraków"}
        doc_warsaw = MagicMock()
        doc_warsaw.metadata = {"id": "p2", "city": "Warszawa"}

        results = [(doc_warsaw, 0.9), (doc_krakow, 0.7)]

        output = await service.apply_personalization_to_results(results, "user-001")

        # Nothing is removed and the scores are the ones the old code gave.
        assert len(output) == 2
        warsaw_score = next(s for d, s in output if d == doc_warsaw)
        krakow_score = next(s for d, s in output if d == doc_krakow)
        assert warsaw_score == pytest.approx(0.9)
        assert krakow_score == pytest.approx(0.7 * (1.0 + 0.3 * 0.2))

    @pytest.mark.asyncio
    async def test_with_no_memory_and_no_preferences_nothing_changes(self):
        """With neither memory nor preferences the results come back untouched."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        service = PersonalizationService(mock_session, memory_service=_make_memory())

        doc = MagicMock()
        doc.metadata = {"id": "p1", "city": "Kraków"}
        results = [(doc, 0.9)]

        output = await service.apply_personalization_to_results(results, "user-001")

        assert output == results


class TestTheDislikedAndLikedListings:
    """A like and a dislike that name a LISTING."""

    @pytest.mark.asyncio
    async def test_a_disliked_listing_is_removed(self):
        """A listing the buyer disliked is not returned at all."""
        profile = _make_profile(view_count=5, favorite_count=3)
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = profile
        mock_session.execute.return_value = mock_result

        service = PersonalizationService(
            mock_session,
            memory_service=_make_memory(_fact("disliked", "the flat with the lift", "p9")),
        )

        disliked = MagicMock()
        disliked.metadata = {"id": "p9", "city": "Kraków"}
        other = MagicMock()
        other.metadata = {"id": "p1", "city": "Kraków"}

        output = await service.apply_personalization_to_results(
            [(disliked, 0.9), (other, 0.8)], "user-001"
        )

        assert disliked not in [doc for doc, _ in output]
        assert other in [doc for doc, _ in output]

    @pytest.mark.asyncio
    async def test_a_liked_listing_weighs_that_listing_and_not_every_flat(self):
        """A like that names a listing does not widen into a feature class."""
        profile = _make_profile(view_count=5, favorite_count=3)
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = profile
        mock_session.execute.return_value = mock_result

        service = PersonalizationService(
            mock_session,
            memory_service=_make_memory(_fact("liked", "the balcony flat", "p9")),
        )

        liked = MagicMock()
        liked.metadata = {
            "id": "p9",
            "city": "Kraków",
            "property_type": "flat",
            "amenities": ["balcony"],
        }
        other_flat = MagicMock()
        other_flat.metadata = {
            "id": "p1",
            "city": "Kraków",
            "property_type": "flat",
            "amenities": ["balcony"],
        }

        output = await service.apply_personalization_to_results(
            [(other_flat, 0.8), (liked, 0.8)], "user-001"
        )

        # The liked listing comes first - and the other flat, which is the
        # same kind of flat with the same balcony, is not lifted with it.
        assert [doc for doc, _ in output] == [liked, other_flat]
        other_score = next(score for doc, score in output if doc == other_flat)
        assert other_score == pytest.approx(0.8)

    def test_a_liked_feature_still_matches_by_its_words(self):
        """A like that names a FEATURE (no listing id) keeps the token match."""
        declared = DeclaredPreferences.from_facts([_fact("liked", "flats with a balcony")])

        assert declared.liked_features
        assert not declared.liked_listing_ids
        assert declared.liked_boost({"property_type": "flat", "amenities": ["balcony"]})[2] > 0


class TestTheCurrency:
    """The catalogue is priced in PLN; a budget in another currency is ignored."""

    def test_a_budget_in_the_catalogue_currency_is_used(self):
        declared = DeclaredPreferences.from_facts([_fact("budget", "up to 500000 PLN")])

        assert declared.price_max == 500000
        assert declared.price_currency == "PLN"

    def test_a_budget_without_a_currency_is_the_catalogue_currency(self):
        declared = DeclaredPreferences.from_facts([_fact("budget", "up to 500000")])

        assert declared.price_max == 500000
        assert declared.price_currency == "PLN"

    def test_a_budget_in_another_currency_is_ignored(self):
        """It cannot be compared with the catalogue's prices - and it is not guessed."""
        declared = DeclaredPreferences.from_facts([_fact("budget", "up to 500000 EUR")])

        assert declared.price_min is None
        assert declared.price_max is None
        assert not declared.is_active

    @pytest.mark.asyncio
    async def test_a_budget_in_another_currency_does_not_move_the_prices(self):
        profile = _make_profile(view_count=5, favorite_count=3)
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = profile
        mock_session.execute.return_value = mock_result

        service = PersonalizationService(
            mock_session, memory_service=_make_memory(_fact("budget", "up to 500000 EUR"))
        )

        doc = MagicMock()
        doc.metadata = {"id": "p1", "city": "Kraków", "price": 900000, "currency": "PLN"}

        output = await service.apply_personalization_to_results([(doc, 0.9)], "user-001")

        # No budget, no price boost: the listing is where the search put it.
        assert output[0][1] == pytest.approx(0.9)


class TestTheOrderTheBuyerAskedFor:
    """An explicit sort is the buyer's order too."""

    @pytest.mark.asyncio
    async def test_an_explicit_sort_is_kept(self):
        """The results keep the order the caller brought."""
        profile = _make_profile(view_count=5, favorite_count=3)
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = profile
        mock_session.execute.return_value = mock_result

        service = PersonalizationService(
            mock_session, memory_service=_make_memory(_fact("budget", "up to 500000"))
        )

        cheap = MagicMock()
        cheap.metadata = {"id": "p1", "city": "Kraków", "price": 300000}
        dear = MagicMock()
        dear.metadata = {"id": "p2", "city": "Kraków", "price": 900000}

        output = await service.apply_personalization_to_results(
            [(cheap, 0.9), (dear, 0.8)], "user-001", keep_order=True
        )

        assert [doc for doc, _ in output] == [cheap, dear]

    @pytest.mark.asyncio
    async def test_the_order_is_kept_and_the_ruled_out_area_is_still_removed(self):
        profile = _make_profile(view_count=5, favorite_count=3)
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = profile
        mock_session.execute.return_value = mock_result

        service = PersonalizationService(
            mock_session, memory_service=_make_memory(_fact("ruled_out_area", "Kraków"))
        )

        cheap = MagicMock()
        cheap.metadata = {"id": "p1", "city": "Kraków", "price": 300000}
        other = MagicMock()
        other.metadata = {"id": "p2", "city": "Warszawa", "price": 400000}

        output = await service.apply_personalization_to_results(
            [(cheap, 0.9), (other, 0.8)], "user-001", keep_order=True
        )

        assert [doc for doc, _ in output] == [other]
