"""
Tests for market insights and analytics module.
"""

import pytest
import pandas as pd
from analytics import MarketInsights, PriceTrend, MarketStatistics, TrendDirection
from data.schemas import Property, PropertyCollection, PropertyType


@pytest.fixture
def sample_market_properties():
    """Create sample properties for market analysis."""
    properties = [
        Property(
            id="m1",
            city="Krakow",
            rooms=2,
            bathrooms=1,
            price=800,
            area_sqm=50,
            has_parking=True,
            has_garden=False,
            property_type=PropertyType.APARTMENT
        ),
        Property(
            id="m2",
            city="Krakow",
            rooms=2,
            bathrooms=1,
            price=900,
            area_sqm=55,
            has_parking=False,
            has_garden=True,
            property_type=PropertyType.APARTMENT
        ),
        Property(
            id="m3",
            city="Warsaw",
            rooms=3,
            bathrooms=2,
            price=1400,
            area_sqm=80,
            has_parking=True,
            has_garden=False,
            property_type=PropertyType.APARTMENT
        ),
        Property(
            id="m4",
            city="Warsaw",
            rooms=3,
            bathrooms=2,
            price=1600,
            area_sqm=85,
            has_parking=True,
            has_garden=True,
            property_type=PropertyType.APARTMENT
        ),
        Property(
            id="m5",
            city="Krakow",
            rooms=1,
            bathrooms=1,
            price=650,
            area_sqm=35,
            has_parking=False,
            has_garden=False,
            property_type=PropertyType.STUDIO
        ),
        Property(
            id="m6",
            city="Warsaw",
            rooms=2,
            bathrooms=1,
            price=1200,
            area_sqm=60,
            has_parking=True,
            has_garden=False,
            property_type=PropertyType.APARTMENT
        ),
        Property(
            id="m7",
            city="Krakow",
            rooms=3,
            bathrooms=2,
            price=1100,
            area_sqm=70,
            has_parking=True,
            has_garden=True,
            property_type=PropertyType.HOUSE
        ),
        Property(
            id="m8",
            city="Warsaw",
            rooms=4,
            bathrooms=3,
            price=2000,
            area_sqm=120,
            has_parking=True,
            has_garden=True,
            property_type=PropertyType.HOUSE
        ),
    ]
    return PropertyCollection(properties=properties, total_count=len(properties))


@pytest.fixture
def market_insights(sample_market_properties):
    """Create MarketInsights instance with sample data."""
    return MarketInsights(sample_market_properties)


class TestMarketInsights:
    """Tests for MarketInsights class."""

    def test_initialization(self, sample_market_properties):
        """Test MarketInsights initialization."""
        insights = MarketInsights(sample_market_properties)
        assert insights is not None
        assert len(insights.df) == len(sample_market_properties.properties)

    def test_dataframe_conversion(self, market_insights):
        """Test properties are correctly converted to DataFrame."""
        df = market_insights.df
        assert isinstance(df, pd.DataFrame)
        assert 'city' in df.columns
        assert 'price' in df.columns
        assert 'rooms' in df.columns
        assert len(df) == 8

    def test_overall_statistics(self, market_insights):
        """Test overall market statistics calculation."""
        stats = market_insights.get_overall_statistics()

        assert isinstance(stats, MarketStatistics)
        assert stats.total_properties == 8
        assert stats.average_price > 0
        assert stats.median_price > 0
        assert stats.min_price == 650
        assert stats.max_price == 2000
        assert stats.avg_rooms > 0

    def test_overall_statistics_amenities(self, market_insights):
        """Test amenity percentages in statistics."""
        stats = market_insights.get_overall_statistics()

        # 6 out of 8 have parking
        assert stats.parking_percentage == pytest.approx(75.0, rel=0.1)
        # 4 out of 8 have garden
        assert stats.garden_percentage == pytest.approx(50.0, rel=0.1)

    def test_overall_statistics_cities(self, market_insights):
        """Test city breakdown in statistics."""
        stats = market_insights.get_overall_statistics()

        assert 'Krakow' in stats.cities
        assert 'Warsaw' in stats.cities
        assert stats.cities['Krakow'] == 4
        assert stats.cities['Warsaw'] == 4

    def test_price_trend_analysis(self, market_insights):
        """Test price trend detection."""
        trend = market_insights.get_price_trend()

        assert isinstance(trend, PriceTrend)
        assert trend.direction in [d for d in TrendDirection]
        assert trend.sample_size == 8
        assert trend.average_price > 0
        assert trend.median_price > 0
        assert trend.confidence in ['low', 'medium', 'high']

    def test_price_trend_by_city(self, market_insights):
        """Test price trend for specific city."""
        krakow_trend = market_insights.get_price_trend(city="Krakow")

        assert krakow_trend.sample_size == 4
        assert krakow_trend.average_price < 1000  # Krakow is cheaper

    def test_price_trend_insufficient_data(self):
        """Test price trend with insufficient data."""
        # Create collection with only 2 properties
        props = [
            Property(id="p1", city="Test", rooms=2, price=800, property_type=PropertyType.APARTMENT),
            Property(id="p2", city="Test", rooms=2, price=900, property_type=PropertyType.APARTMENT)
        ]
        collection = PropertyCollection(properties=props, total_count=2)
        insights = MarketInsights(collection)

        trend = insights.get_price_trend()
        assert trend.direction == TrendDirection.INSUFFICIENT_DATA
        assert trend.confidence == "low"

    def test_location_insights(self, market_insights):
        """Test location-specific insights."""
        krakow_insights = market_insights.get_location_insights("Krakow")

        assert krakow_insights is not None
        assert krakow_insights.city == "Krakow"
        assert krakow_insights.property_count == 4
        assert krakow_insights.avg_price > 0
        assert krakow_insights.median_price > 0

    def test_location_insights_amenities(self, market_insights):
        """Test amenity availability in location insights."""
        krakow_insights = market_insights.get_location_insights("Krakow")

        assert 'parking' in krakow_insights.amenity_availability
        assert 'garden' in krakow_insights.amenity_availability
        # Values should be percentages (0-100)
        assert 0 <= krakow_insights.amenity_availability['parking'] <= 100

    def test_location_insights_nonexistent(self, market_insights):
        """Test location insights for non-existent city."""
        insights = market_insights.get_location_insights("NonExistentCity")
        assert insights is None

    def test_location_insights_price_comparison(self, market_insights):
        """Test price comparison classification."""
        krakow = market_insights.get_location_insights("Krakow")
        warsaw = market_insights.get_location_insights("Warsaw")

        # Warsaw should be more expensive
        assert warsaw.avg_price > krakow.avg_price
        # Check comparison classifications
        assert warsaw.price_comparison in ['above_average', 'below_average', 'average']

    def test_property_type_insights(self, market_insights):
        """Test property type insights."""
        apartment_insights = market_insights.get_property_type_insights("apartment")

        assert apartment_insights is not None
        assert apartment_insights.property_type == "apartment"
        assert apartment_insights.count == 5  # 5 apartments in sample data
        assert apartment_insights.avg_price > 0
        assert len(apartment_insights.popular_locations) > 0

    def test_property_type_insights_nonexistent(self, market_insights):
        """Test property type insights for non-existent type."""
        insights = market_insights.get_property_type_insights("villa")
        assert insights is None

    def test_price_distribution(self, market_insights):
        """Test price distribution histogram."""
        dist = market_insights.get_price_distribution(bins=5)

        assert 'counts' in dist
        assert 'bin_edges' in dist
        assert 'bins' in dist
        assert len(dist['counts']) == 5
        assert len(dist['bins']) == 5
        assert sum(dist['counts']) == 8  # Total properties

    def test_amenity_impact_on_price(self, market_insights):
        """Test amenity impact analysis."""
        impact = market_insights.get_amenity_impact_on_price()

        assert isinstance(impact, dict)
        # Should have impacts for parking, garden, etc.
        if 'parking' in impact:
            # Impact should be a percentage
            assert isinstance(impact['parking'], (int, float))

    def test_best_value_properties(self, market_insights):
        """Test best value property identification."""
        best_values = market_insights.get_best_value_properties(top_n=3)

        assert len(best_values) <= 3
        if best_values:
            # First property should have highest value score
            assert 'value_score' in best_values[0]
            assert 'city' in best_values[0]
            assert 'price' in best_values[0]

            # Scores should be in descending order
            if len(best_values) > 1:
                assert best_values[0]['value_score'] >= best_values[1]['value_score']

    def test_best_value_properties_empty(self):
        """Test best value with empty dataset."""
        empty_collection = PropertyCollection(properties=[], total_count=0)
        insights = MarketInsights(empty_collection)

        best_values = insights.get_best_value_properties(top_n=5)
        assert best_values == []

    def test_compare_locations(self, market_insights):
        """Test location comparison."""
        comparison = market_insights.compare_locations("Warsaw", "Krakow")

        assert 'city1' in comparison
        assert 'city2' in comparison
        assert 'price_difference' in comparison
        assert 'price_difference_percent' in comparison
        assert 'cheaper_city' in comparison

        # Warsaw should be more expensive
        assert comparison['cheaper_city'] == "Krakow"
        assert comparison['price_difference'] < 0 or comparison['price_difference'] > 0

    def test_compare_locations_nonexistent(self, market_insights):
        """Test comparison with non-existent city."""
        comparison = market_insights.compare_locations("Warsaw", "NonExistent")

        assert 'error' in comparison

    def test_price_per_sqm_calculation(self, market_insights):
        """Test price per square meter calculation."""
        stats = market_insights.get_overall_statistics()

        if stats.avg_price_per_sqm:
            # Should be reasonable (between 10 and 50 for sample data)
            assert 10 < stats.avg_price_per_sqm < 50

    def test_empty_dataset_handling(self):
        """Test handling of empty dataset."""
        empty_collection = PropertyCollection(properties=[], total_count=0)
        insights = MarketInsights(empty_collection)

        stats = insights.get_overall_statistics()
        assert stats.total_properties == 0
        assert stats.average_price == 0


class TestMarketStatistics:
    """Tests for MarketStatistics model."""

    def test_market_statistics_creation(self):
        """Test MarketStatistics model creation."""
        stats = MarketStatistics(
            total_properties=10,
            average_price=1000.0,
            median_price=950.0,
            min_price=500.0,
            max_price=2000.0,
            std_dev=300.0,
            avg_rooms=2.5,
            parking_percentage=60.0,
            garden_percentage=40.0,
            furnished_percentage=30.0
        )

        assert stats.total_properties == 10
        assert stats.average_price == 1000.0
        assert stats.parking_percentage == 60.0

    def test_market_statistics_optional_fields(self):
        """Test MarketStatistics with optional fields."""
        stats = MarketStatistics(
            total_properties=5,
            average_price=1000.0,
            median_price=950.0,
            min_price=500.0,
            max_price=2000.0,
            std_dev=300.0,
            avg_rooms=2.5,
            parking_percentage=60.0,
            garden_percentage=40.0,
            furnished_percentage=30.0,
            avg_area=65.5,
            avg_price_per_sqm=15.25
        )

        assert stats.avg_area == 65.5
        assert stats.avg_price_per_sqm == 15.25


class TestPriceTrend:
    """Tests for PriceTrend dataclass."""

    def test_price_trend_creation(self):
        """Test PriceTrend creation."""
        trend = PriceTrend(
            direction=TrendDirection.INCREASING,
            change_percent=5.5,
            average_price=1200.0,
            median_price=1150.0,
            price_range=(800.0, 1800.0),
            sample_size=20,
            confidence="high"
        )

        assert trend.direction == TrendDirection.INCREASING
        assert trend.change_percent == 5.5
        assert trend.sample_size == 20
        assert trend.confidence == "high"

    def test_trend_direction_values(self):
        """Test all TrendDirection enum values."""
        assert TrendDirection.INCREASING.value == "increasing"
        assert TrendDirection.DECREASING.value == "decreasing"
        assert TrendDirection.STABLE.value == "stable"
        assert TrendDirection.INSUFFICIENT_DATA.value == "insufficient_data"
