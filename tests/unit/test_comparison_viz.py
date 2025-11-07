"""
Tests for property comparison and visualization module.
"""

import pytest
import pandas as pd
from ui.comparison_viz import PropertyComparison, create_comparison_chart, create_price_trend_chart
from data.schemas import Property, PropertyType


@pytest.fixture
def comparison_properties():
    """Create sample properties for comparison testing."""
    return [
        Property(
            id="comp1",
            city="Krakow",
            rooms=2,
            bathrooms=1,
            price=850,
            area_sqm=50,
            has_parking=True,
            has_garden=False,
            has_pool=False,
            is_furnished=False,
            has_balcony=True,
            has_elevator=False,
            property_type=PropertyType.APARTMENT
        ),
        Property(
            id="comp2",
            city="Warsaw",
            rooms=3,
            bathrooms=2,
            price=1400,
            area_sqm=75,
            has_parking=True,
            has_garden=True,
            has_pool=False,
            is_furnished=True,
            has_balcony=True,
            has_elevator=True,
            property_type=PropertyType.APARTMENT
        ),
        Property(
            id="comp3",
            city="Krakow",
            rooms=1,
            bathrooms=1,
            price=600,
            area_sqm=35,
            has_parking=False,
            has_garden=False,
            has_pool=False,
            is_furnished=False,
            has_balcony=False,
            has_elevator=False,
            property_type=PropertyType.STUDIO
        ),
    ]


class TestPropertyComparison:
    """Tests for PropertyComparison class."""

    def test_initialization_valid(self, comparison_properties):
        """Test initializing comparison with 2-3 properties."""
        # 2 properties
        comparison = PropertyComparison(comparison_properties[:2])
        assert comparison is not None
        assert len(comparison.df) == 2

        # 3 properties
        comparison = PropertyComparison(comparison_properties)
        assert len(comparison.df) == 3

    def test_initialization_four_properties(self, comparison_properties):
        """Test initializing comparison with 4 properties."""
        four_props = comparison_properties + [
            Property(
                id="comp4",
                city="Gdansk",
                rooms=2,
                bathrooms=1,
                price=950,
                area_sqm=55,
                property_type=PropertyType.APARTMENT
            )
        ]

        comparison = PropertyComparison(four_props)
        assert len(comparison.df) == 4

    def test_initialization_too_few(self, comparison_properties):
        """Test initialization fails with < 2 properties."""
        with pytest.raises(ValueError, match="at least 2"):
            PropertyComparison([comparison_properties[0]])

    def test_initialization_too_many(self, comparison_properties):
        """Test initialization fails with > 4 properties."""
        five_props = comparison_properties + [
            Property(id="extra1", city="Test", rooms=2, price=1000, property_type=PropertyType.APARTMENT),
            Property(id="extra2", city="Test", rooms=2, price=1000, property_type=PropertyType.APARTMENT)
        ]

        with pytest.raises(ValueError, match="maximum 4"):
            PropertyComparison(five_props)

    def test_dataframe_structure(self, comparison_properties):
        """Test DataFrame has correct structure."""
        comparison = PropertyComparison(comparison_properties)
        df = comparison.df

        # Check columns exist
        assert 'Property' in df.columns
        assert 'City' in df.columns
        assert 'Price' in df.columns
        assert 'Price_Numeric' in df.columns
        assert 'Rooms' in df.columns
        assert 'Bathrooms' in df.columns
        assert 'Parking' in df.columns
        assert 'Amenity_Count' in df.columns

        # Check row count
        assert len(df) == 3

    def test_get_comparison_table(self, comparison_properties):
        """Test getting formatted comparison table."""
        comparison = PropertyComparison(comparison_properties)
        table = comparison.get_comparison_table()

        assert isinstance(table, pd.DataFrame)
        # Index should be 'Property'
        assert table.index.name == 'Property'
        # Should have expected columns
        assert 'City' in table.columns
        assert 'Price' in table.columns
        assert 'Rooms' in table.columns

    def test_get_price_comparison(self, comparison_properties):
        """Test price comparison metrics."""
        comparison = PropertyComparison(comparison_properties)
        price_comp = comparison.get_price_comparison()

        assert 'cheapest' in price_comp
        assert 'most_expensive' in price_comp
        assert 'avg_price' in price_comp
        assert 'price_range' in price_comp

        # Check cheapest
        assert price_comp['cheapest']['price'] == 600
        assert price_comp['cheapest']['city'] == "Krakow"

        # Check most expensive
        assert price_comp['most_expensive']['price'] == 1400
        assert price_comp['most_expensive']['city'] == "Warsaw"

        # Check average
        assert price_comp['avg_price'] == pytest.approx((850 + 1400 + 600) / 3)

        # Check range
        assert price_comp['price_range'] == 800  # 1400 - 600

    def test_get_best_value(self, comparison_properties):
        """Test best value determination."""
        comparison = PropertyComparison(comparison_properties)
        best_value = comparison.get_best_value()

        assert 'property' in best_value
        assert 'city' in best_value
        assert 'price' in best_value
        assert 'value_score' in best_value
        assert 'reasoning' in best_value

        # Value score should be between 0 and 1
        assert 0 <= best_value['value_score'] <= 1

        # Reasoning should be a string
        assert isinstance(best_value['reasoning'], str)
        assert len(best_value['reasoning']) > 0

    def test_get_amenity_comparison(self, comparison_properties):
        """Test amenity comparison matrix."""
        comparison = PropertyComparison(comparison_properties)
        amenity_comp = comparison.get_amenity_comparison()

        assert isinstance(amenity_comp, pd.DataFrame)
        # Index should be 'Property'
        assert amenity_comp.index.name == 'Property'
        # Should have amenity columns
        assert 'Parking' in amenity_comp.columns
        assert 'Garden' in amenity_comp.columns
        assert 'Amenity_Count' in amenity_comp.columns

    def test_amenity_count_calculation(self, comparison_properties):
        """Test amenity count is calculated correctly."""
        comparison = PropertyComparison(comparison_properties)
        df = comparison.df

        # First property has: parking, balcony = 2
        assert df.iloc[0]['Amenity_Count'] == 2

        # Second property has: parking, garden, furnished, balcony, elevator = 5
        assert df.iloc[1]['Amenity_Count'] == 5

        # Third property has: none = 0
        assert df.iloc[2]['Amenity_Count'] == 0

    def test_amenity_symbols(self, comparison_properties):
        """Test amenity columns use ✓/✗ symbols."""
        comparison = PropertyComparison(comparison_properties)
        table = comparison.get_comparison_table()

        # Check for symbols by converting to string and joining
        table_str = ' '.join(table.values.flatten().astype(str))
        assert '✓' in table_str or '✗' in table_str

    def test_price_per_sqm_calculation(self, comparison_properties):
        """Test price per sqm is calculated."""
        comparison = PropertyComparison(comparison_properties)
        df = comparison.df

        # First property: 850 / 50 = 17
        assert '$17.00' in df.iloc[0]['Price/sqm']

        # Second property: 1400 / 75 = 18.67
        assert '$18.67' in df.iloc[1]['Price/sqm']

    def test_price_per_sqm_missing_area(self):
        """Test price per sqm when area is missing."""
        props_no_area = [
            Property(id="p1", city="Test", rooms=2, price=1000, property_type=PropertyType.APARTMENT),
            Property(id="p2", city="Test", rooms=2, price=1200, property_type=PropertyType.APARTMENT)
        ]

        comparison = PropertyComparison(props_no_area)
        df = comparison.df

        # Should show N/A
        assert df.iloc[0]['Price/sqm'] == 'N/A'


class TestCreateComparisonChart:
    """Tests for create_comparison_chart function."""

    def test_create_comparison_chart_basic(self, comparison_properties):
        """Test creating comparison chart data."""
        chart_data = create_comparison_chart(comparison_properties)

        assert isinstance(chart_data, dict)
        assert 'price_comparison' in chart_data
        assert 'room_comparison' in chart_data
        assert 'amenity_comparison' in chart_data

    def test_price_comparison_data(self, comparison_properties):
        """Test price comparison chart data."""
        chart_data = create_comparison_chart(comparison_properties)
        price_data = chart_data['price_comparison']

        assert 'labels' in price_data
        assert 'prices' in price_data
        assert 'cities' in price_data

        assert len(price_data['labels']) == 3
        assert len(price_data['prices']) == 3
        assert len(price_data['cities']) == 3

        # Check values
        assert price_data['prices'] == [850, 1400, 600]
        assert 'Krakow' in price_data['cities']
        assert 'Warsaw' in price_data['cities']

    def test_room_comparison_data(self, comparison_properties):
        """Test room comparison chart data."""
        chart_data = create_comparison_chart(comparison_properties)
        room_data = chart_data['room_comparison']

        assert 'labels' in room_data
        assert 'rooms' in room_data
        assert 'bathrooms' in room_data

        assert len(room_data['rooms']) == 3
        assert room_data['rooms'] == [2, 3, 1]
        assert room_data['bathrooms'] == [1, 2, 1]

    def test_amenity_comparison_data(self, comparison_properties):
        """Test amenity comparison chart data."""
        chart_data = create_comparison_chart(comparison_properties)
        amenity_data = chart_data['amenity_comparison']

        assert 'labels' in amenity_data
        assert 'amenity_counts' in amenity_data

        assert len(amenity_data['amenity_counts']) == 3
        # Based on our test data: 2, 5, 0 amenities
        assert amenity_data['amenity_counts'] == [2, 5, 0]


class TestCreatePriceTrendChart:
    """Tests for create_price_trend_chart function."""

    def test_create_price_trend_chart_with_labels(self):
        """Test creating price trend chart with labels."""
        prices = [800, 900, 1000, 1100, 1200]
        labels = ["Jan", "Feb", "Mar", "Apr", "May"]

        chart_data = create_price_trend_chart(prices, labels)

        assert isinstance(chart_data, dict)
        assert chart_data['labels'] == labels
        assert chart_data['prices'] == prices
        assert chart_data['avg_price'] == 1000
        assert chart_data['min_price'] == 800
        assert chart_data['max_price'] == 1200

    def test_create_price_trend_chart_without_labels(self):
        """Test creating price trend chart without labels."""
        prices = [800, 900, 1000]

        chart_data = create_price_trend_chart(prices)

        assert 'labels' in chart_data
        # Should generate default labels
        assert chart_data['labels'] == ["Property 1", "Property 2", "Property 3"]

    def test_price_trend_chart_calculations(self):
        """Test price trend chart statistical calculations."""
        prices = [500, 1000, 1500]

        chart_data = create_price_trend_chart(prices)

        assert chart_data['avg_price'] == 1000
        assert chart_data['min_price'] == 500
        assert chart_data['max_price'] == 1500

    def test_price_trend_chart_empty_prices(self):
        """Test price trend chart with empty prices."""
        chart_data = create_price_trend_chart([])

        assert chart_data['labels'] == []
        assert chart_data['prices'] == []
        assert chart_data['avg_price'] == 0
        assert chart_data['min_price'] == 0
        assert chart_data['max_price'] == 0

    def test_price_trend_chart_single_price(self):
        """Test price trend chart with single price."""
        prices = [1000]

        chart_data = create_price_trend_chart(prices)

        assert chart_data['avg_price'] == 1000
        assert chart_data['min_price'] == 1000
        assert chart_data['max_price'] == 1000


class TestValueScoringAlgorithm:
    """Tests for value scoring algorithm."""

    def test_value_score_cheap_property(self):
        """Test value score favors cheap properties."""
        # One cheap property, one expensive
        props = [
            Property(
                id="cheap",
                city="Test",
                rooms=2,
                bathrooms=1,
                price=600,
                area_sqm=50,
                has_parking=True,
                has_garden=False,
                property_type=PropertyType.APARTMENT
            ),
            Property(
                id="expensive",
                city="Test",
                rooms=2,
                bathrooms=1,
                price=1400,
                area_sqm=50,
                has_parking=True,
                has_garden=False,
                property_type=PropertyType.APARTMENT
            ),
        ]

        comparison = PropertyComparison(props)
        best = comparison.get_best_value()

        # Cheaper property should have better value
        assert best['city'] == "Test"
        # First property (cheap one) should be selected
        assert best['price'] == 600

    def test_value_score_more_amenities(self):
        """Test value score favors more amenities."""
        props = [
            Property(
                id="basic",
                city="Test",
                rooms=2,
                bathrooms=1,
                price=1000,
                area_sqm=50,
                has_parking=False,
                has_garden=False,
                property_type=PropertyType.APARTMENT
            ),
            Property(
                id="featured",
                city="Test",
                rooms=2,
                bathrooms=1,
                price=1000,
                area_sqm=50,
                has_parking=True,
                has_garden=True,
                has_pool=True,
                property_type=PropertyType.APARTMENT
            ),
        ]

        comparison = PropertyComparison(props)
        best = comparison.get_best_value()

        # Property with more amenities should win (same price)
        assert best['property'] == "Property 2"  # The featured one

    def test_value_score_balanced(self):
        """Test value score balances multiple factors."""
        props = [
            Property(
                id="balanced",
                city="Test",
                rooms=2,
                bathrooms=1,
                price=900,
                area_sqm=50,
                has_parking=True,
                has_garden=True,
                property_type=PropertyType.APARTMENT
            ),
            Property(
                id="cheap_but_bare",
                city="Test",
                rooms=1,
                bathrooms=1,
                price=600,
                area_sqm=30,
                has_parking=False,
                has_garden=False,
                property_type=PropertyType.STUDIO
            ),
            Property(
                id="expensive_featured",
                city="Test",
                rooms=4,
                bathrooms=2,
                price=1800,
                area_sqm=100,
                has_parking=True,
                has_garden=True,
                has_pool=True,
                property_type=PropertyType.HOUSE
            ),
        ]

        comparison = PropertyComparison(props)
        best = comparison.get_best_value()

        # Should have a value score
        assert 0 <= best['value_score'] <= 1
        # Should have reasoning
        assert len(best['reasoning']) > 0


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_comparison_identical_prices(self):
        """Test comparison when all prices are identical."""
        props = [
            Property(id="p1", city="Test1", rooms=2, price=1000, property_type=PropertyType.APARTMENT),
            Property(id="p2", city="Test2", rooms=2, price=1000, property_type=PropertyType.APARTMENT),
            Property(id="p3", city="Test3", rooms=2, price=1000, property_type=PropertyType.APARTMENT),
        ]

        comparison = PropertyComparison(props)
        price_comp = comparison.get_price_comparison()

        assert price_comp['avg_price'] == 1000
        assert price_comp['price_range'] == 0

    def test_comparison_identical_rooms(self):
        """Test comparison when all have same rooms."""
        props = [
            Property(id="p1", city="Test", rooms=2, price=800, property_type=PropertyType.APARTMENT),
            Property(id="p2", city="Test", rooms=2, price=900, property_type=PropertyType.APARTMENT),
            Property(id="p3", city="Test", rooms=2, price=1000, property_type=PropertyType.APARTMENT),
        ]

        comparison = PropertyComparison(props)
        # Should not crash
        table = comparison.get_comparison_table()
        assert len(table) == 3

    def test_comparison_no_amenities(self):
        """Test comparison when properties have no amenities."""
        props = [
            Property(id="p1", city="Test", rooms=2, price=800, property_type=PropertyType.APARTMENT),
            Property(id="p2", city="Test", rooms=2, price=900, property_type=PropertyType.APARTMENT),
        ]

        comparison = PropertyComparison(props)
        df = comparison.df

        # All should have 0 amenities
        assert df['Amenity_Count'].sum() == 0

    def test_comparison_all_amenities(self):
        """Test comparison when properties have all amenities."""
        props = [
            Property(
                id="p1",
                city="Test",
                rooms=2,
                price=1500,
                has_parking=True,
                has_garden=True,
                has_pool=True,
                is_furnished=True,
                has_balcony=True,
                has_elevator=True,
                property_type=PropertyType.APARTMENT
            ),
            Property(
                id="p2",
                city="Test",
                rooms=2,
                price=1600,
                has_parking=True,
                has_garden=True,
                has_pool=True,
                is_furnished=True,
                has_balcony=True,
                has_elevator=True,
                property_type=PropertyType.APARTMENT
            ),
        ]

        comparison = PropertyComparison(props)
        df = comparison.df

        # Both should have 6 amenities
        assert df['Amenity_Count'].iloc[0] == 6
        assert df['Amenity_Count'].iloc[1] == 6

    def test_comparison_different_property_types(self):
        """Test comparison with different property types."""
        props = [
            Property(id="apt", city="Test", rooms=2, price=900, property_type=PropertyType.APARTMENT),
            Property(id="house", city="Test", rooms=3, price=1200, property_type=PropertyType.HOUSE),
            Property(id="studio", city="Test", rooms=1, price=600, property_type=PropertyType.STUDIO),
        ]

        comparison = PropertyComparison(props)
        table = comparison.get_comparison_table()

        assert 'Apartment' in table['Type'].values
        assert 'House' in table['Type'].values
        assert 'Studio' in table['Type'].values
