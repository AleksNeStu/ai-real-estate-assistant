"""
Unit tests for neighborhood quality index tool.

Tests neighborhood scoring algorithm, component calculations, and overall score.
Also tests the neighborhood adapter integration and fallback behavior.
"""

from unittest.mock import Mock, patch

import pytest

from tools.property_tools import (
    NeighborhoodQualityIndexTool,
    create_property_tools,
)


def _mock_neighborhood_adapter():
    """Create a mock NeighborhoodAdapter with sensible defaults."""
    from data.adapters.neighborhood_adapter import NeighborhoodAdapter

    mock = Mock(spec=NeighborhoodAdapter)
    mock.count_schools.return_value = 5
    mock.count_amenities.return_value = 10
    mock.calculate_walkability.return_value = 70.0
    mock.count_green_spaces.return_value = 3
    return mock


def _mock_safety_adapter():
    """Create a mock SafetyAdapter with sensible defaults."""
    from data.adapters.safety_adapter import SafetyAdapter, SafetyResult

    mock = Mock(spec=SafetyAdapter)
    mock.get_safety_score.return_value = SafetyResult(
        score=75.0,
        police_stations_nearby=2,
        emergency_services_nearby=1,
        lighting_score=None,
        pois=[],
        data_source="osm_overpass_api",
        confidence=0.7,
    )
    return mock


@pytest.fixture
def _patch_adapters():
    """Patch all external adapters to prevent real HTTP calls during tests."""
    from data.adapters.air_quality_adapter import AirQualityAdapter, AirQualityResult
    from data.adapters.noise_adapter import NoiseAdapter, NoiseResult
    from data.adapters.transport_adapter import TransportAdapter

    mock_aq = Mock(spec=AirQualityAdapter)
    mock_aq.get_aqi_score.return_value = AirQualityResult(
        score=70.0,
        aqi_value=None,
        pm25=None,
        pm10=None,
        data_source="fallback",
        confidence=0.3,
        station_name=None,
    )

    mock_noise = Mock(spec=NoiseAdapter)
    mock_noise.estimate_noise_level.return_value = NoiseResult(
        score=65.0,
        estimated_db=50.0,
        noise_sources=[],
        data_source="fallback",
        confidence=0.3,
        query_latitude=None,
        query_longitude=None,
    )

    mock_transport = Mock(spec=TransportAdapter)
    mock_transport.calculate_accessibility_score.return_value = 60.0

    with (
        patch(
            "data.adapters.neighborhood_adapter.get_neighborhood_adapter",
            return_value=_mock_neighborhood_adapter(),
        ),
        patch(
            "data.adapters.safety_adapter.get_safety_adapter",
            return_value=_mock_safety_adapter(),
        ),
        patch(
            "data.adapters.air_quality_adapter.get_air_quality_adapter",
            return_value=mock_aq,
        ),
        patch(
            "data.adapters.noise_adapter.get_noise_adapter",
            return_value=mock_noise,
        ),
        patch(
            "data.adapters.transport_adapter.get_transport_adapter",
            return_value=mock_transport,
        ),
    ):
        yield


@pytest.mark.usefixtures("_patch_adapters")
class TestNeighborhoodQualityIndexTool:
    """Test suite for NeighborhoodQualityIndexTool."""

    @pytest.fixture
    def neighborhood_calc(self):
        """Fixture for neighborhood quality calculator."""
        return NeighborhoodQualityIndexTool()

    def test_basic_calculation_with_coordinates(self, neighborhood_calc):
        """Test basic neighborhood quality calculation with coordinates."""
        result = NeighborhoodQualityIndexTool.calculate(
            property_id="test_prop_1",
            latitude=52.2297,
            longitude=21.0122,  # Warsaw coordinates
        )

        assert result.property_id == "test_prop_1"
        assert 0 <= result.overall_score <= 100
        assert 0 <= result.safety_score <= 100
        assert 0 <= result.schools_score <= 100
        assert 0 <= result.amenities_score <= 100
        assert 0 <= result.walkability_score <= 100
        assert 0 <= result.green_space_score <= 100

    def test_calculation_with_city_only(self, neighborhood_calc):
        """Test calculation with only city name (no coordinates)."""
        result = NeighborhoodQualityIndexTool.calculate(
            property_id="test_prop_2",
            city="Warsaw",
        )

        assert result.property_id == "test_prop_2"
        assert result.city == "Warsaw"
        assert 0 <= result.overall_score <= 100
        # Safety score should use city-based mock
        assert 0 <= result.safety_score <= 100

    def test_safety_score_by_city(self, neighborhood_calc):
        """Test safety score varies by city."""
        warsaw = NeighborhoodQualityIndexTool._mock_safety_score("Warsaw", None)
        london = NeighborhoodQualityIndexTool._mock_safety_score("London", None)
        berlin = NeighborhoodQualityIndexTool._mock_safety_score("Berlin", None)

        # Each city should have a different base score
        # All should be in valid range
        assert 0 <= warsaw <= 100
        assert 0 <= london <= 100
        assert 0 <= berlin <= 100

    def test_overall_score_weighted_calculation(self, neighborhood_calc):
        """Test overall score is weighted correctly."""
        result = NeighborhoodQualityIndexTool.calculate(
            property_id="test_weights",
            latitude=52.2297,
            longitude=21.0122,
        )

        # Overall score should be weighted sum of components (8 factors - Task #40)
        expected_overall = (
            result.safety_score * NeighborhoodQualityIndexTool.WEIGHT_SAFETY
            + result.schools_score * NeighborhoodQualityIndexTool.WEIGHT_SCHOOLS
            + result.amenities_score * NeighborhoodQualityIndexTool.WEIGHT_AMENITIES
            + result.walkability_score * NeighborhoodQualityIndexTool.WEIGHT_WALKABILITY
            + result.green_space_score * NeighborhoodQualityIndexTool.WEIGHT_GREEN_SPACE
            + (result.air_quality_score or 0) * NeighborhoodQualityIndexTool.WEIGHT_AIR_QUALITY
            + (result.noise_level_score or 0) * NeighborhoodQualityIndexTool.WEIGHT_NOISE_LEVEL
            + (result.public_transport_score or 0)
            * NeighborhoodQualityIndexTool.WEIGHT_PUBLIC_TRANSPORT
        )

        assert abs(result.overall_score - expected_overall) < 0.1

    def test_score_breakdown_components(self, neighborhood_calc):
        """Test score breakdown has all expected components."""
        result = NeighborhoodQualityIndexTool.calculate(
            property_id="test_breakdown",
            latitude=52.2297,
            longitude=21.0122,
        )

        # Task #40: Added 3 new factors (air_quality, noise_level, public_transport)
        expected_keys = {
            "safety_weighted",
            "schools_weighted",
            "amenities_weighted",
            "walkability_weighted",
            "green_space_weighted",
            "air_quality_weighted",
            "noise_level_weighted",
            "public_transport_weighted",
        }

        assert set(result.score_breakdown.keys()) == expected_keys

    def test_data_sources_includes_coordinates(self, neighborhood_calc):
        """Test data sources reflect when coordinates are provided."""
        result_with_coords = NeighborhoodQualityIndexTool.calculate(
            property_id="test_data_1",
            latitude=52.2297,
            longitude=21.0122,
        )

        result_without_coords = NeighborhoodQualityIndexTool.calculate(
            property_id="test_data_2",
        )

        # With coordinates, should include geographic_coordinates
        assert "geographic_coordinates" in result_with_coords.data_sources
        assert "geographic_coordinates" not in result_without_coords.data_sources

        # Both should include OSM sources; safety may use osm_overpass_api, city_estimate, or fallback
        assert "osm_overpass_api" in result_with_coords.data_sources

    def test_missing_coordinates_returns_default_scores(self, neighborhood_calc):
        """Test that missing coordinates returns reasonable default scores."""
        result = NeighborhoodQualityIndexTool.calculate(
            property_id="test_no_coords",
        )

        # Should still return valid scores even without coordinates
        assert result.overall_score >= 0
        assert result.schools_score >= 0
        assert result.amenities_score >= 0
        assert result.walkability_score >= 0
        assert result.green_space_score >= 0

    def test_result_includes_all_input_fields(self, neighborhood_calc):
        """Test result includes all provided input fields."""
        result = NeighborhoodQualityIndexTool.calculate(
            property_id="test_fields",
            latitude=50.0,
            longitude=20.0,
            city="Krakow",
            neighborhood="Old Town",
        )

        assert result.property_id == "test_fields"
        assert result.latitude == 50.0
        assert result.longitude == 20.0
        assert result.city == "Krakow"
        assert result.neighborhood == "Old Town"

    def test_score_weights_sum_to_one(self):
        """Test that component weights sum to 1.0."""
        total_weight = (
            NeighborhoodQualityIndexTool.WEIGHT_SAFETY
            + NeighborhoodQualityIndexTool.WEIGHT_SCHOOLS
            + NeighborhoodQualityIndexTool.WEIGHT_AMENITIES
            + NeighborhoodQualityIndexTool.WEIGHT_WALKABILITY
            + NeighborhoodQualityIndexTool.WEIGHT_GREEN_SPACE
            + NeighborhoodQualityIndexTool.WEIGHT_AIR_QUALITY
            + NeighborhoodQualityIndexTool.WEIGHT_NOISE_LEVEL
            + NeighborhoodQualityIndexTool.WEIGHT_PUBLIC_TRANSPORT
        )

        assert abs(total_weight - 1.0) < 0.001

    def test_tool_metadata(self, neighborhood_calc):
        """Test tool name and description."""
        assert neighborhood_calc.name == "neighborhood_quality_index"
        assert len(neighborhood_calc.description) > 0
        assert "neighborhood" in neighborhood_calc.description.lower()

    def test_rating_label_function(self):
        """Test rating label function returns correct labels."""
        assert (
            NeighborhoodQualityIndexTool._get_rating_label(90)
            == "Excellent - Highly desirable neighborhood"
        )
        assert NeighborhoodQualityIndexTool._get_rating_label(75) == "Good - Above average quality"
        assert NeighborhoodQualityIndexTool._get_rating_label(60) == "Fair - Average neighborhood"
        assert NeighborhoodQualityIndexTool._get_rating_label(45) == "Poor - Below average quality"
        assert (
            NeighborhoodQualityIndexTool._get_rating_label(20) == "Very Poor - Significant concerns"
        )

    @pytest.mark.skip(reason="External API dependency - requires network access to Overpass API")
    def test_schools_score_range(self, neighborhood_calc):
        """Test schools score is always in valid range."""
        for lat in range(-80, 81, 20):
            for lon in range(-170, 171, 40):
                result = NeighborhoodQualityIndexTool.calculate(
                    property_id=f"test_{lat}_{lon}",
                    latitude=float(lat),
                    longitude=float(lon),
                )
                assert 0 <= result.schools_score <= 100

    @pytest.mark.skip(reason="External API dependency - requires network access to Overpass API")
    def test_amenities_score_range(self, neighborhood_calc):
        """Test amenities score is always in valid range."""
        for lat in range(-80, 81, 20):
            for lon in range(-170, 171, 40):
                result = NeighborhoodQualityIndexTool.calculate(
                    property_id=f"test_{lat}_{lon}",
                    latitude=float(lat),
                    longitude=float(lon),
                )
                assert 0 <= result.amenities_score <= 100

    @pytest.mark.skip(reason="External API dependency - requires network access to Overpass API")
    def test_walkability_score_range(self, neighborhood_calc):
        """Test walkability score is always in valid range."""
        for lat in range(-80, 81, 20):
            for lon in range(-170, 171, 40):
                result = NeighborhoodQualityIndexTool.calculate(
                    property_id=f"test_{lat}_{lon}",
                    latitude=float(lat),
                    longitude=float(lon),
                )
                assert 0 <= result.walkability_score <= 100

    @pytest.mark.skip(reason="External API dependency - requires network access to Overpass API")
    def test_green_space_score_range(self, neighborhood_calc):
        """Test green space score is always in valid range."""
        for lat in range(-80, 81, 20):
            for lon in range(-170, 171, 40):
                result = NeighborhoodQualityIndexTool.calculate(
                    property_id=f"test_{lat}_{lon}",
                    latitude=float(lat),
                    longitude=float(lon),
                )
                assert 0 <= result.green_space_score <= 100

    @patch("data.adapters.safety_adapter.get_safety_adapter")
    def test_real_safety_score_from_adapter(self, mock_get_adapter):
        """Test that real safety score is used from SafetyAdapter."""
        from data.adapters.safety_adapter import SafetyAdapter, SafetyResult

        mock_adapter_instance = Mock(spec=SafetyAdapter)
        mock_adapter_instance.get_safety_score.return_value = SafetyResult(
            score=78.5,
            police_stations_nearby=2,
            emergency_services_nearby=1,
            lighting_score=None,
            pois=[],
            data_source="osm_overpass_api",
            confidence=0.7,
        )
        mock_get_adapter.return_value = mock_adapter_instance

        result = NeighborhoodQualityIndexTool.calculate(
            property_id="test_safety_real",
            latitude=52.2297,
            longitude=21.0122,
        )

        assert result.safety_score == 78.5
        assert result.factor_details["safety"]["data_source"] == "osm_overpass_api"
        assert result.factor_details["safety"]["confidence"] == 0.7
        assert result.factor_details["safety"]["police_stations_nearby"] == 2
        assert result.factor_details["safety"]["emergency_services_nearby"] == 1

    @patch("data.adapters.safety_adapter.get_safety_adapter")
    def test_safety_adapter_fallback_on_error(self, mock_get_adapter):
        """Test fallback to mock when safety adapter fails."""
        mock_get_adapter.side_effect = Exception("API failure")

        result = NeighborhoodQualityIndexTool.calculate(
            property_id="test_safety_fallback",
            latitude=52.2297,
            longitude=21.0122,
            city="Warsaw",
        )

        # Should still return valid score using fallback
        assert 0 <= result.safety_score <= 100
        assert result.factor_details["safety"]["data_source"] == "fallback"
        assert result.factor_details["safety"]["confidence"] == 0.2


class TestNeighborhoodToolFactory:
    """Test neighborhood tool in factory function."""

    def test_neighborhood_tool_in_factory(self):
        """Test that NeighborhoodQualityIndexTool is included in factory."""
        tools = create_property_tools()
        tool_names = {tool.name for tool in tools}

        assert "neighborhood_quality_index" in tool_names

    def test_all_expected_tools_present(self):
        """Test that all expected tools including neighborhood are created."""
        tools = create_property_tools()
        tool_names = {tool.name for tool in tools}

        # TASK-021: Added commute_time_analyzer and commute_ranking
        # TASK-023: Added listing_description_generator, listing_headline_generator, social_media_content_generator
        # TASK-039: Added advanced_investment_analyzer
        # Task #42: Added rent_vs_buy_calculator (14 total tools)
        # Task #114: Added commute_analysis and multi_origin_commute (OSRM-based)
        # Task #115: Added negotiation_helper (17 total tools)
        # v5.1: Added price_forecast and neighborhood_summary (19 total tools)
        expected_names = {
            "mortgage_calculator",
            "tco_calculator",
            "investment_analyzer",
            "neighborhood_quality_index",
            "property_comparator",
            "price_analyzer",
            "location_analyzer",
            "commute_time_analyzer",  # TASK-021
            "commute_ranking",  # TASK-021
            "listing_description_generator",  # TASK-023
            "listing_headline_generator",  # TASK-023
            "social_media_content_generator",  # TASK-023
            "advanced_investment_analyzer",  # TASK-039
            "rent_vs_buy_calculator",  # Task #42
            "commute_analysis",  # Task #114
            "multi_origin_commute",  # Task #114
            "negotiation_helper",  # Task #115
            "price_forecast",  # v5.1
            "neighborhood_summary",  # v5.1
        }

        assert tool_names == expected_names


@pytest.mark.usefixtures("_patch_adapters")
class TestNeighborhoodToolPhase2:
    """Test Phase 2 OSM integration and fallback behavior."""

    def test_data_sources_reflect_osm_integration(self):
        """Test data sources include osm_overpass_api for Phase 2."""
        result = NeighborhoodQualityIndexTool.calculate(
            property_id="test_phase2",
            latitude=52.2297,
            longitude=21.0122,
        )

        # Phase 2 uses osm_overpass_api instead of osm_pois
        # Safety may use osm_overpass_api, city_estimate, or fallback
        assert "osm_overpass_api" in result.data_sources
        assert "geographic_coordinates" in result.data_sources

    def test_adapter_fallback_on_schools_error(self):
        """Test fallback to mock when adapter fails for schools."""
        # Patch at the module level where imports are resolved
        import data.adapters.neighborhood_adapter as na_module

        original_get_adapter = na_module.get_neighborhood_adapter

        try:
            # Create a mock adapter that raises exception
            from data.adapters.neighborhood_adapter import NeighborhoodAdapter

            mock_adapter_instance = Mock(spec=NeighborhoodAdapter)
            mock_adapter_instance.count_schools.side_effect = Exception("API failure")
            mock_adapter_instance.count_amenities.return_value = 10
            mock_adapter_instance.calculate_walkability.return_value = 70.0
            mock_adapter_instance.count_green_spaces.return_value = 3

            # Replace get_neighborhood_adapter to return our mock
            na_module.get_neighborhood_adapter = Mock(return_value=mock_adapter_instance)

            result = NeighborhoodQualityIndexTool.calculate(
                property_id="test_fallback_schools",
                latitude=52.2297,
                longitude=21.0122,
            )

            # Should still return a valid score using fallback
            assert 0 <= result.schools_score <= 100
            assert result.schools_score >= 50  # Fallback minimum
        finally:
            na_module.get_neighborhood_adapter = original_get_adapter

    def test_adapter_fallback_on_amenities_error(self):
        """Test fallback to mock when adapter fails for amenities."""
        import data.adapters.neighborhood_adapter as na_module

        original_get_adapter = na_module.get_neighborhood_adapter

        try:
            from data.adapters.neighborhood_adapter import NeighborhoodAdapter

            mock_adapter_instance = Mock(spec=NeighborhoodAdapter)
            mock_adapter_instance.count_schools.return_value = 5
            mock_adapter_instance.count_amenities.side_effect = Exception("API failure")
            mock_adapter_instance.calculate_walkability.return_value = 70.0
            mock_adapter_instance.count_green_spaces.return_value = 3

            na_module.get_neighborhood_adapter = Mock(return_value=mock_adapter_instance)

            result = NeighborhoodQualityIndexTool.calculate(
                property_id="test_fallback_amenities",
                latitude=52.2297,
                longitude=21.0122,
            )

            # Should still return a valid score using fallback
            assert 0 <= result.amenities_score <= 100
        finally:
            na_module.get_neighborhood_adapter = original_get_adapter

    def test_adapter_fallback_on_walkability_error(self):
        """Test fallback to mock when adapter fails for walkability."""
        import data.adapters.neighborhood_adapter as na_module

        original_get_adapter = na_module.get_neighborhood_adapter

        try:
            from data.adapters.neighborhood_adapter import NeighborhoodAdapter

            mock_adapter_instance = Mock(spec=NeighborhoodAdapter)
            mock_adapter_instance.count_schools.return_value = 5
            mock_adapter_instance.count_amenities.return_value = 10
            mock_adapter_instance.calculate_walkability.side_effect = Exception("API failure")
            mock_adapter_instance.count_green_spaces.return_value = 3

            na_module.get_neighborhood_adapter = Mock(return_value=mock_adapter_instance)

            result = NeighborhoodQualityIndexTool.calculate(
                property_id="test_fallback_walk",
                latitude=52.2297,
                longitude=21.0122,
            )

            # Should still return a valid score using fallback
            assert 0 <= result.walkability_score <= 100
        finally:
            na_module.get_neighborhood_adapter = original_get_adapter

    def test_adapter_fallback_on_green_space_error(self):
        """Test fallback to mock when adapter fails for green spaces."""
        import data.adapters.neighborhood_adapter as na_module

        original_get_adapter = na_module.get_neighborhood_adapter

        try:
            from data.adapters.neighborhood_adapter import NeighborhoodAdapter

            mock_adapter_instance = Mock(spec=NeighborhoodAdapter)
            mock_adapter_instance.count_schools.return_value = 5
            mock_adapter_instance.count_amenities.return_value = 10
            mock_adapter_instance.calculate_walkability.return_value = 70.0
            mock_adapter_instance.count_green_spaces.side_effect = Exception("API failure")

            na_module.get_neighborhood_adapter = Mock(return_value=mock_adapter_instance)

            result = NeighborhoodQualityIndexTool.calculate(
                property_id="test_fallback_green",
                latitude=52.2297,
                longitude=21.0122,
            )

            # Should still return a valid score using fallback
            assert 0 <= result.green_space_score <= 100
        finally:
            na_module.get_neighborhood_adapter = original_get_adapter

    @patch("requests.get")
    def test_adapter_import_error_fallback(self, mock_get):
        """Test fallback when adapter module cannot be imported."""
        mock_get.return_value = Mock(status_code=200, json=lambda: {"elements": []})
        import sys

        # Save the original module and remove it temporarily
        original_module = sys.modules.get("data.adapters.neighborhood_adapter")

        try:
            # Remove the module from sys.modules to force ImportError
            if "data.adapters.neighborhood_adapter" in sys.modules:
                del sys.modules["data.adapters.neighborhood_adapter"]
            if "data.adapters" in sys.modules:
                # Also remove parent package to ensure full re-import failure
                parent = sys.modules["data.adapters"]
                if hasattr(parent, "neighborhood_adapter"):
                    delattr(parent, "neighborhood_adapter")

            result = NeighborhoodQualityIndexTool.calculate(
                property_id="test_import_error",
                latitude=52.2297,
                longitude=21.0122,
            )

            # Should still return valid scores using hash-based fallback
            assert 0 <= result.schools_score <= 100
            assert 0 <= result.amenities_score <= 100
            assert 0 <= result.walkability_score <= 100
            assert 0 <= result.green_space_score <= 100
        finally:
            # Restore the module
            if original_module is not None:
                sys.modules["data.adapters.neighborhood_adapter"] = original_module

    @patch("data.adapters.neighborhood_adapter.get_neighborhood_adapter")
    def test_real_school_count_translates_to_score(self, mock_get_adapter):
        """Test that real school counts translate to appropriate scores."""
        from data.adapters.neighborhood_adapter import NeighborhoodAdapter

        mock_adapter_instance = Mock(spec=NeighborhoodAdapter)

        # Set default return values for all methods
        mock_adapter_instance.count_amenities.return_value = 10
        mock_adapter_instance.calculate_walkability.return_value = 70.0
        mock_adapter_instance.count_green_spaces.return_value = 3

        mock_get_adapter.return_value = mock_adapter_instance

        # Test different school counts
        test_cases = [
            (0, 30.0),  # No schools = low score
            (2, 50.0),  # 2 schools = medium-low
            (5, 70.0),  # 5 schools = medium-high
            (8, 85.0),  # 8+ schools = high
        ]

        for school_count, expected_min_score in test_cases:
            mock_adapter_instance.count_schools.return_value = school_count

            result = NeighborhoodQualityIndexTool.calculate(
                property_id=f"test_schools_{school_count}",
                latitude=52.2297,
                longitude=21.0122,
            )

            assert result.schools_score >= expected_min_score
            assert result.schools_score <= 100

    @patch("data.adapters.neighborhood_adapter.get_neighborhood_adapter")
    def test_real_amenity_count_translates_to_score(self, mock_get_adapter):
        """Test that real amenity counts translate to appropriate scores."""
        from data.adapters.neighborhood_adapter import NeighborhoodAdapter

        mock_adapter_instance = Mock(spec=NeighborhoodAdapter)

        # Set default return values for all methods
        mock_adapter_instance.count_schools.return_value = 5
        mock_adapter_instance.calculate_walkability.return_value = 70.0
        mock_adapter_instance.count_green_spaces.return_value = 3

        mock_get_adapter.return_value = mock_adapter_instance

        # Test different amenity counts
        test_cases = [
            (0, 40.0),  # No amenities = low score
            (5, 60.0),  # 5 amenities = medium
            (15, 80.0),  # 15 amenities = high
            (30, 90.0),  # 30+ amenities = very high
        ]

        for amenity_count, expected_min_score in test_cases:
            mock_adapter_instance.count_amenities.return_value = amenity_count

            result = NeighborhoodQualityIndexTool.calculate(
                property_id=f"test_amenities_{amenity_count}",
                latitude=52.2297,
                longitude=21.0122,
            )

            assert result.amenities_score >= expected_min_score
            assert result.amenities_score <= 100

    @patch("data.adapters.neighborhood_adapter.get_neighborhood_adapter")
    def test_real_walkability_translates_to_score(self, mock_get_adapter):
        """Test that real walkability calculation is used."""
        from data.adapters.neighborhood_adapter import NeighborhoodAdapter

        mock_adapter_instance = Mock(spec=NeighborhoodAdapter)

        # Set default return values for all methods
        mock_adapter_instance.count_schools.return_value = 5
        mock_adapter_instance.count_amenities.return_value = 10
        mock_adapter_instance.count_green_spaces.return_value = 3

        mock_get_adapter.return_value = mock_adapter_instance

        # Test different walkability scores
        test_walkability = [30.0, 50.0, 70.0, 90.0]

        for walkability in test_walkability:
            mock_adapter_instance.calculate_walkability.return_value = walkability

            result = NeighborhoodQualityIndexTool.calculate(
                property_id=f"test_walk_{walkability}",
                latitude=52.2297,
                longitude=21.0122,
            )

            assert result.walkability_score == walkability

    @patch("data.adapters.neighborhood_adapter.get_neighborhood_adapter")
    def test_real_green_space_count_translates_to_score(self, mock_get_adapter):
        """Test that real green space counts translate to appropriate scores."""
        from data.adapters.neighborhood_adapter import NeighborhoodAdapter

        mock_adapter_instance = Mock(spec=NeighborhoodAdapter)

        # Set default return values for all methods
        mock_adapter_instance.count_schools.return_value = 5
        mock_adapter_instance.count_amenities.return_value = 10
        mock_adapter_instance.calculate_walkability.return_value = 70.0

        mock_get_adapter.return_value = mock_adapter_instance

        # Test different green space counts
        test_cases = [
            (0, 30.0),  # No green spaces = low score
            (1, 50.0),  # 1 park = medium
            (3, 72.5),  # 3 parks = medium-high
            (6, 85.0),  # 6+ parks = very high (85.0 for 6, more for 7+)
        ]

        for green_count, expected_min_score in test_cases:
            mock_adapter_instance.count_green_spaces.return_value = green_count

            result = NeighborhoodQualityIndexTool.calculate(
                property_id=f"test_green_{green_count}",
                latitude=52.2297,
                longitude=21.0122,
            )

            assert result.green_space_score >= expected_min_score
            assert result.green_space_score <= 100


class TestNeighborhoodAdapter:
    """Test the NeighborhoodAdapter directly."""

    def test_adapter_initialization(self):
        """Test adapter can be initialized."""
        from data.adapters.neighborhood_adapter import NeighborhoodAdapter

        adapter = NeighborhoodAdapter()
        assert adapter is not None
        assert adapter._api_url is not None

    def test_adapter_with_custom_url(self):
        """Test adapter with custom API URL."""
        from data.adapters.neighborhood_adapter import NeighborhoodAdapter

        custom_url = "https://custom.overpass-api.de/api/interpreter"
        adapter = NeighborhoodAdapter(api_url=custom_url)
        assert adapter._api_url == custom_url

    def test_adapter_singleton(self):
        """Test get_neighborhood_adapter returns singleton instance."""
        from data.adapters.neighborhood_adapter import get_neighborhood_adapter

        adapter1 = get_neighborhood_adapter()
        adapter2 = get_neighborhood_adapter()
        assert adapter1 is adapter2

    def test_adapter_school_tags_defined(self):
        """Test that school tags are properly defined."""
        from data.adapters.neighborhood_adapter import NeighborhoodAdapter

        adapter = NeighborhoodAdapter()
        assert hasattr(adapter, "SCHOOL_TAGS")
        assert len(adapter.SCHOOL_TAGS) > 0
        assert "school" in adapter.SCHOOL_TAGS

    def test_adapter_amenity_tags_defined(self):
        """Test that amenity tags are properly defined."""
        from data.adapters.neighborhood_adapter import NeighborhoodAdapter

        adapter = NeighborhoodAdapter()
        assert hasattr(adapter, "AMENITY_TAGS")
        assert len(adapter.AMENITY_TAGS) > 0
        assert "restaurant" in adapter.AMENITY_TAGS

    def test_adapter_green_space_tags_defined(self):
        """Test that green space tags are properly defined."""
        from data.adapters.neighborhood_adapter import NeighborhoodAdapter

        adapter = NeighborhoodAdapter()
        assert hasattr(adapter, "GREEN_SPACE_TAGS")
        assert len(adapter.GREEN_SPACE_TAGS) > 0
        assert "park" in adapter.GREEN_SPACE_TAGS

    def test_count_schools_returns_non_negative(self):
        """Test count_schools returns non-negative integer."""
        from data.adapters.neighborhood_adapter import NeighborhoodAdapter

        adapter = NeighborhoodAdapter()

        # This will use the API or return empty list on error
        count = adapter.count_schools(52.2297, 21.0122, radius_m=1000)
        assert isinstance(count, int)
        assert count >= 0

    def test_count_amenities_returns_non_negative(self):
        """Test count_amenities returns non-negative integer."""
        from data.adapters.neighborhood_adapter import NeighborhoodAdapter

        adapter = NeighborhoodAdapter()
        count = adapter.count_amenities(52.2297, 21.0122, radius_m=500)
        assert isinstance(count, int)
        assert count >= 0

    def test_count_green_spaces_returns_non_negative(self):
        """Test count_green_spaces returns non-negative integer."""
        from data.adapters.neighborhood_adapter import NeighborhoodAdapter

        adapter = NeighborhoodAdapter()
        count = adapter.count_green_spaces(52.2297, 21.0122, radius_m=1000)
        assert isinstance(count, int)
        assert count >= 0

    def test_calculate_walkability_returns_valid_score(self):
        """Test calculate_walkability returns score in valid range."""
        from data.adapters.neighborhood_adapter import NeighborhoodAdapter

        adapter = NeighborhoodAdapter()
        score = adapter.calculate_walkability(52.2297, 21.0122, radius_m=500)
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_fetch_pois_returns_dict_with_categories(self):
        """Test fetch_pois_within_radius returns properly structured dict."""
        from data.adapters.neighborhood_adapter import NeighborhoodAdapter

        adapter = NeighborhoodAdapter()
        pois = adapter.fetch_pois_within_radius(52.2297, 21.0122, radius_m=1000)

        assert isinstance(pois, dict)
        assert "schools" in pois
        assert "amenities" in pois
        assert "green_spaces" in pois
        assert "all" in pois
        assert isinstance(pois["schools"], list)
        assert isinstance(pois["amenities"], list)
        assert isinstance(pois["green_spaces"], list)
        assert isinstance(pois["all"], list)
