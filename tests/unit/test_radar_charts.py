"""
Unit tests for radar chart visualizations.

Tests radar chart generation functions in ui/radar_charts.py
"""

import pytest
from data.schemas import Property, PropertyType
from ui.radar_charts import (
    create_property_radar_chart,
    create_amenity_radar_chart,
    create_value_radar_chart,
    _extract_property_dimensions,
    _normalize_dimensions,
    _calculate_price_value_score,
    _calculate_space_score,
    _calculate_amenity_score
)


@pytest.fixture
def comparison_properties():
    """Create sample properties for comparison."""
    return [
        Property(
            city="Krakow",
            price=850,
            rooms=2,
            bathrooms=1,
            area_sqm=50,
            property_type=PropertyType.APARTMENT,
            has_parking=True,
            has_garden=False,
            has_pool=False,
            is_furnished=True,
            has_balcony=True,
            has_elevator=False
        ),
        Property(
            city="Warsaw",
            price=1200,
            rooms=3,
            bathrooms=2,
            area_sqm=75,
            property_type=PropertyType.APARTMENT,
            has_parking=True,
            has_garden=True,
            has_pool=False,
            is_furnished=False,
            has_balcony=True,
            has_elevator=True
        ),
        Property(
            city="Wroclaw",
            price=900,
            rooms=2,
            bathrooms=1,
            area_sqm=55,
            property_type=PropertyType.STUDIO,
            has_parking=False,
            has_garden=False,
            has_pool=False,
            is_furnished=True,
            has_balcony=False,
            has_elevator=False
        ),
    ]


class TestPropertyRadarChart:
    """Tests for property radar chart creation."""

    def test_create_radar_chart(self, comparison_properties):
        """Test creating radar chart."""
        fig = create_property_radar_chart(comparison_properties)

        assert fig is not None
        assert len(fig.data) == 3  # One trace per property

    def test_radar_with_custom_dimensions(self, comparison_properties):
        """Test radar chart with custom dimensions."""
        dimensions = ['price', 'rooms', 'amenities']
        fig = create_property_radar_chart(comparison_properties, dimensions=dimensions)

        assert fig is not None
        assert len(fig.data) == 3

    def test_radar_with_custom_title(self, comparison_properties):
        """Test radar chart with custom title."""
        title = "Custom Comparison"
        fig = create_property_radar_chart(comparison_properties, title=title)

        assert fig.layout.title.text == title

    def test_too_few_properties(self):
        """Test with fewer than 2 properties."""
        prop = Property(
            city="Krakow",
            price=850,
            rooms=2,
            bathrooms=1,
            area_sqm=50,
            property_type=PropertyType.APARTMENT
        )

        with pytest.raises(ValueError, match="At least 2 properties required"):
            create_property_radar_chart([prop])

    def test_too_many_properties(self, comparison_properties):
        """Test with more than 6 properties."""
        many_props = comparison_properties * 3  # 9 properties

        with pytest.raises(ValueError, match="Maximum 6 properties"):
            create_property_radar_chart(many_props)

    def test_default_dimensions(self, comparison_properties):
        """Test that default dimensions are used when not specified."""
        fig = create_property_radar_chart(comparison_properties, dimensions=None)

        assert fig is not None
        # Default dimensions: price, rooms, area, amenities, location
        assert len(fig.data) > 0


class TestAmenityRadarChart:
    """Tests for amenity-specific radar chart."""

    def test_create_amenity_radar(self, comparison_properties):
        """Test creating amenity radar chart."""
        fig = create_amenity_radar_chart(comparison_properties)

        assert fig is not None
        assert len(fig.data) == 3

    def test_amenity_radar_with_custom_title(self, comparison_properties):
        """Test amenity radar with custom title."""
        title = "Custom Amenity Comparison"
        fig = create_amenity_radar_chart(comparison_properties, title=title)

        assert fig.layout.title.text == title

    def test_amenity_radar_properties_validation(self):
        """Test amenity radar validates property count."""
        prop = Property(
            city="Krakow",
            price=850,
            rooms=2,
            bathrooms=1,
            area_sqm=50,
            property_type=PropertyType.APARTMENT
        )

        with pytest.raises(ValueError):
            create_amenity_radar_chart([prop])


class TestValueRadarChart:
    """Tests for value assessment radar chart."""

    def test_create_value_radar(self, comparison_properties):
        """Test creating value radar chart."""
        fig = create_value_radar_chart(comparison_properties)

        assert fig is not None
        assert len(fig.data) == 3

    def test_value_radar_with_custom_weights(self, comparison_properties):
        """Test value radar with custom weights."""
        weights = {
            'price_value': 2.0,
            'space': 1.0,
            'amenities': 1.0,
            'condition': 0.5
        }

        fig = create_value_radar_chart(comparison_properties, weights=weights)

        assert fig is not None

    def test_value_radar_default_weights(self, comparison_properties):
        """Test value radar uses equal weights by default."""
        fig = create_value_radar_chart(comparison_properties, weights=None)

        assert fig is not None


class TestExtractPropertyDimensions:
    """Tests for dimension extraction function."""

    def test_extract_price(self):
        """Test extracting price dimension."""
        prop = Property(
            city="Krakow",
            price=850,
            rooms=2,
            bathrooms=1,
            area_sqm=50,
            property_type=PropertyType.APARTMENT
        )

        values = _extract_property_dimensions(prop, ['price'])
        assert values == [850]

    def test_extract_rooms(self):
        """Test extracting rooms dimension."""
        prop = Property(
            city="Krakow",
            price=850,
            rooms=3,
            bathrooms=1,
            area_sqm=50,
            property_type=PropertyType.APARTMENT
        )

        values = _extract_property_dimensions(prop, ['rooms'])
        assert values == [3]

    def test_extract_area(self):
        """Test extracting area dimension."""
        prop = Property(
            city="Krakow",
            price=850,
            rooms=2,
            bathrooms=1,
            area_sqm=60,
            property_type=PropertyType.APARTMENT
        )

        values = _extract_property_dimensions(prop, ['area'])
        assert values == [60]

    def test_extract_amenities_count(self):
        """Test extracting amenity count."""
        prop = Property(
            city="Krakow",
            price=850,
            rooms=2,
            bathrooms=1,
            area_sqm=50,
            property_type=PropertyType.APARTMENT,
            has_parking=True,
            has_garden=True,
            has_pool=False,
            is_furnished=True,
            has_balcony=False,
            has_elevator=False
        )

        values = _extract_property_dimensions(prop, ['amenities'])
        assert values == [3]  # parking + garden + furnished

    def test_extract_multiple_dimensions(self):
        """Test extracting multiple dimensions."""
        prop = Property(
            city="Krakow",
            price=850,
            rooms=2,
            bathrooms=1,
            area_sqm=50,
            property_type=PropertyType.APARTMENT
        )

        values = _extract_property_dimensions(prop, ['price', 'rooms', 'area'])
        assert values == [850, 2, 50]

    def test_extract_with_missing_area(self):
        """Test extracting when area is None."""
        prop = Property(
            city="Krakow",
            price=850,
            rooms=2,
            bathrooms=1,
            area_sqm=None,
            property_type=PropertyType.APARTMENT
        )

        values = _extract_property_dimensions(prop, ['area'])
        assert values == [0]  # Should default to 0


class TestNormalizeDimensions:
    """Tests for dimension normalization function."""

    def test_normalize_basic(self):
        """Test basic normalization."""
        property_data = [
            [100, 2],  # property 1: price=100, rooms=2
            [200, 4],  # property 2: price=200, rooms=4
        ]
        dimensions = ['price', 'rooms']

        normalized = _normalize_dimensions(property_data, dimensions)

        # Price: lower is better, so 100 -> 1.0, 200 -> 0.0
        # Rooms: higher is better, so 2 -> 0.0, 4 -> 1.0
        assert normalized[0][0] == 1.0  # Cheapest property gets 1.0 for price
        assert normalized[1][0] == 0.0  # Most expensive gets 0.0 for price
        assert normalized[0][1] == 0.0  # Fewest rooms gets 0.0
        assert normalized[1][1] == 1.0  # Most rooms gets 1.0

    def test_normalize_same_values(self):
        """Test normalization when all values are the same."""
        property_data = [
            [100, 2],
            [100, 2],
        ]
        dimensions = ['price', 'rooms']

        normalized = _normalize_dimensions(property_data, dimensions)

        # All values should be 1.0 when identical
        assert all(v == 1.0 for values in normalized for v in values)

    def test_normalize_three_properties(self):
        """Test normalization with three properties."""
        property_data = [
            [100, 2, 3],  # Cheapest, fewest rooms, average amenities
            [150, 3, 5],  # Mid price, mid rooms, most amenities
            [200, 4, 1],  # Most expensive, most rooms, fewest amenities
        ]
        dimensions = ['price', 'rooms', 'amenities']

        normalized = _normalize_dimensions(property_data, dimensions)

        # Check that values are between 0 and 1
        for values in normalized:
            for v in values:
                assert 0 <= v <= 1


class TestScoreFunctions:
    """Tests for scoring helper functions."""

    def test_price_value_score_low(self):
        """Test price value score for low price."""
        prop = Property(
            city="Krakow",
            price=700,
            rooms=2,
            bathrooms=1,
            area_sqm=50,
            property_type=PropertyType.APARTMENT
        )

        score = _calculate_price_value_score(prop)
        assert score == 1.0

    def test_price_value_score_medium(self):
        """Test price value score for medium price."""
        prop = Property(
            city="Krakow",
            price=1000,
            rooms=2,
            bathrooms=1,
            area_sqm=50,
            property_type=PropertyType.APARTMENT
        )

        score = _calculate_price_value_score(prop)
        assert score == 0.7

    def test_price_value_score_high(self):
        """Test price value score for high price."""
        prop = Property(
            city="Krakow",
            price=1800,
            rooms=2,
            bathrooms=1,
            area_sqm=50,
            property_type=PropertyType.APARTMENT
        )

        score = _calculate_price_value_score(prop)
        assert score == 0.2

    def test_space_score_with_area(self):
        """Test space score calculation with area."""
        prop = Property(
            city="Krakow",
            price=850,
            rooms=3,
            bathrooms=1,
            area_sqm=80,
            property_type=PropertyType.APARTMENT
        )

        score = _calculate_space_score(prop)
        assert 0 <= score <= 1

    def test_space_score_without_area(self):
        """Test space score calculation without area."""
        prop = Property(
            city="Krakow",
            price=850,
            rooms=3,
            bathrooms=1,
            area_sqm=None,
            property_type=PropertyType.APARTMENT
        )

        score = _calculate_space_score(prop)
        assert score == 0.6  # 3 rooms / 5 = 0.6

    def test_amenity_score_all(self):
        """Test amenity score with all amenities."""
        prop = Property(
            city="Krakow",
            price=850,
            rooms=2,
            bathrooms=1,
            area_sqm=50,
            property_type=PropertyType.APARTMENT,
            has_parking=True,
            has_garden=True,
            has_pool=True,
            is_furnished=True,
            has_balcony=True,
            has_elevator=True
        )

        score = _calculate_amenity_score(prop)
        assert score == 1.0

    def test_amenity_score_none(self):
        """Test amenity score with no amenities."""
        prop = Property(
            city="Krakow",
            price=850,
            rooms=2,
            bathrooms=1,
            area_sqm=50,
            property_type=PropertyType.APARTMENT,
            has_parking=False,
            has_garden=False,
            has_pool=False,
            is_furnished=False,
            has_balcony=False,
            has_elevator=False
        )

        score = _calculate_amenity_score(prop)
        assert score == 0.0

    def test_amenity_score_partial(self):
        """Test amenity score with some amenities."""
        prop = Property(
            city="Krakow",
            price=850,
            rooms=2,
            bathrooms=1,
            area_sqm=50,
            property_type=PropertyType.APARTMENT,
            has_parking=True,
            has_garden=False,
            has_pool=False,
            is_furnished=True,
            has_balcony=True,
            has_elevator=False
        )

        score = _calculate_amenity_score(prop)
        assert score == 0.5  # 3 out of 6 amenities


class TestEdgeCases:
    """Tests for edge cases."""

    def test_two_properties_minimum(self, comparison_properties):
        """Test with exactly 2 properties (minimum)."""
        two_props = comparison_properties[:2]
        fig = create_property_radar_chart(two_props)

        assert fig is not None
        assert len(fig.data) == 2

    def test_six_properties_maximum(self):
        """Test with exactly 6 properties (maximum)."""
        props = [
            Property(
                city=f"City{i}",
                price=800 + i*100,
                rooms=2,
                bathrooms=1,
                area_sqm=50,
                property_type=PropertyType.APARTMENT
            )
            for i in range(6)
        ]

        fig = create_property_radar_chart(props)

        assert fig is not None
        assert len(fig.data) == 6

    def test_properties_without_area(self):
        """Test radar chart with properties missing area."""
        props = [
            Property(
                city="City1",
                price=800,
                rooms=2,
                bathrooms=1,
                area_sqm=None,
                property_type=PropertyType.APARTMENT
            ),
            Property(
                city="City2",
                price=900,
                rooms=3,
                bathrooms=1,
                area_sqm=None,
                property_type=PropertyType.APARTMENT
            ),
        ]

        fig = create_property_radar_chart(props)

        # Should handle gracefully
        assert fig is not None
