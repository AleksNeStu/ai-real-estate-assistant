"""
Enhanced property comparison visualizations.

Provides rich visual comparisons of properties including:
- Side-by-side comparison tables
- Price comparison charts
- Amenity radar charts
- Location maps
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import streamlit as st

from data.schemas import Property


class PropertyComparison:
    """
    Enhanced property comparison with visualizations.

    Creates detailed side-by-side comparisons with charts and metrics.
    """

    def __init__(self, properties: List[Property]):
        """
        Initialize comparison with properties.

        Args:
            properties: List of 2-4 properties to compare
        """
        if len(properties) < 2:
            raise ValueError("Need at least 2 properties to compare")
        if len(properties) > 4:
            raise ValueError("Can compare maximum 4 properties")

        self.properties = properties
        self.df = self._to_dataframe()

    def _to_dataframe(self) -> pd.DataFrame:
        """Convert properties to DataFrame for comparison."""
        data = []
        for i, prop in enumerate(self.properties, 1):
            prop_type = prop.property_type.value if hasattr(prop.property_type, 'value') else str(prop.property_type)

            data.append({
                'Property': f"Property {i}",
                'City': prop.city,
                'Price': f"${prop.price}",
                'Price_Numeric': prop.price,
                'Type': prop_type.title(),
                'Rooms': int(prop.rooms),
                'Bathrooms': int(prop.bathrooms),
                'Area (sqm)': prop.area_sqm if prop.area_sqm else 'N/A',
                'Price/sqm': f"${prop.price / prop.area_sqm:.2f}" if prop.area_sqm else 'N/A',
                'Parking': '✓' if prop.has_parking else '✗',
                'Garden': '✓' if prop.has_garden else '✗',
                'Pool': '✓' if prop.has_pool else '✗',
                'Furnished': '✓' if prop.is_furnished else '✗',
                'Balcony': '✓' if prop.has_balcony else '✗',
                'Elevator': '✓' if prop.has_elevator else '✗',
                'Amenity_Count': sum([
                    prop.has_parking,
                    prop.has_garden,
                    prop.has_pool,
                    prop.is_furnished,
                    prop.has_balcony,
                    prop.has_elevator
                ])
            })

        return pd.DataFrame(data)

    def get_comparison_table(self) -> pd.DataFrame:
        """
        Get formatted comparison table.

        Returns:
            DataFrame with formatted comparison
        """
        # Select display columns
        display_cols = [
            'Property', 'City', 'Price', 'Type', 'Rooms', 'Bathrooms',
            'Area (sqm)', 'Price/sqm', 'Parking', 'Garden', 'Pool',
            'Furnished', 'Balcony', 'Elevator'
        ]

        return self.df[display_cols].set_index('Property')

    def get_price_comparison(self) -> Dict[str, Any]:
        """
        Get price comparison metrics.

        Returns:
            Dictionary with price statistics
        """
        prices = self.df['Price_Numeric']

        return {
            'cheapest': {
                'property': self.df.loc[prices.idxmin(), 'Property'],
                'price': prices.min(),
                'city': self.df.loc[prices.idxmin(), 'City']
            },
            'most_expensive': {
                'property': self.df.loc[prices.idxmax(), 'Property'],
                'price': prices.max(),
                'city': self.df.loc[prices.idxmax(), 'City']
            },
            'avg_price': prices.mean(),
            'price_range': prices.max() - prices.min(),
            'price_spread_percent': ((prices.max() - prices.min()) / prices.min()) * 100 if prices.min() > 0 else 0
        }

    def get_best_value(self) -> Dict[str, Any]:
        """
        Determine best value property.

        Returns:
            Dictionary with best value analysis
        """
        # Calculate value score
        df = self.df.copy()

        # Normalize metrics (0-1 scale)
        df['price_score'] = 1 - (df['Price_Numeric'] - df['Price_Numeric'].min()) / (df['Price_Numeric'].max() - df['Price_Numeric'].min()) if df['Price_Numeric'].max() != df['Price_Numeric'].min() else 0.5

        df['room_score'] = (df['Rooms'] - df['Rooms'].min()) / (df['Rooms'].max() - df['Rooms'].min()) if df['Rooms'].max() != df['Rooms'].min() else 0.5

        df['amenity_score'] = df['Amenity_Count'] / 6  # 6 total amenities

        # Weighted score: 40% price, 30% rooms, 30% amenities
        df['value_score'] = (
            df['price_score'] * 0.4 +
            df['room_score'] * 0.3 +
            df['amenity_score'] * 0.3
        )

        best_idx = df['value_score'].idxmax()

        return {
            'property': df.loc[best_idx, 'Property'],
            'city': df.loc[best_idx, 'City'],
            'price': df.loc[best_idx, 'Price_Numeric'],
            'value_score': df.loc[best_idx, 'value_score'],
            'reasoning': self._get_value_reasoning(df.loc[best_idx])
        }

    def _get_value_reasoning(self, row: pd.Series) -> str:
        """Generate reasoning for value selection."""
        reasons = []

        if row['price_score'] > 0.7:
            reasons.append("competitive price")
        if row['room_score'] > 0.7:
            reasons.append("spacious")
        if row['amenity_score'] > 0.5:
            reasons.append("well-equipped")

        if not reasons:
            reasons.append("balanced features")

        return f"Best value due to {', '.join(reasons)}"

    def get_amenity_comparison(self) -> pd.DataFrame:
        """
        Get amenity comparison matrix.

        Returns:
            DataFrame with amenity comparison
        """
        amenity_cols = ['Property', 'Parking', 'Garden', 'Pool', 'Furnished', 'Balcony', 'Elevator', 'Amenity_Count']
        return self.df[amenity_cols].set_index('Property')


def create_comparison_chart(properties: List[Property]) -> Dict[str, Any]:
    """
    Create comparison chart data for visualization.

    Args:
        properties: List of properties to compare

    Returns:
        Dictionary with chart data for various visualizations
    """
    comparison = PropertyComparison(properties)
    df = comparison.df

    return {
        'price_comparison': {
            'labels': df['Property'].tolist(),
            'prices': df['Price_Numeric'].tolist(),
            'cities': df['City'].tolist()
        },
        'room_comparison': {
            'labels': df['Property'].tolist(),
            'rooms': df['Rooms'].tolist(),
            'bathrooms': df['Bathrooms'].tolist()
        },
        'amenity_comparison': {
            'labels': df['Property'].tolist(),
            'amenity_counts': df['Amenity_Count'].tolist()
        }
    }


def create_price_trend_chart(
    prices: List[float],
    labels: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create price trend chart data.

    Args:
        prices: List of prices
        labels: Optional labels for data points

    Returns:
        Dictionary with chart data
    """
    if labels is None:
        labels = [f"Property {i+1}" for i in range(len(prices))]

    return {
        'labels': labels,
        'prices': prices,
        'avg_price': sum(prices) / len(prices) if prices else 0,
        'min_price': min(prices) if prices else 0,
        'max_price': max(prices) if prices else 0
    }


def display_comparison_ui(properties: List[Property]):
    """
    Display comprehensive comparison UI in Streamlit.

    Args:
        properties: List of properties to compare
    """
    if len(properties) < 2:
        st.warning("Please select at least 2 properties to compare")
        return

    comparison = PropertyComparison(properties)

    # Header
    st.subheader(f"📊 Comparing {len(properties)} Properties")

    # Price comparison
    price_comp = comparison.get_price_comparison()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Cheapest",
            f"${price_comp['cheapest']['price']:.2f}",
            f"{price_comp['cheapest']['city']}"
        )
    with col2:
        st.metric(
            "Most Expensive",
            f"${price_comp['most_expensive']['price']:.2f}",
            f"{price_comp['most_expensive']['city']}"
        )
    with col3:
        st.metric(
            "Average Price",
            f"${price_comp['avg_price']:.2f}",
            f"±{price_comp['price_spread_percent']:.1f}%"
        )

    # Best value
    best_value = comparison.get_best_value()
    st.success(f"🏆 **Best Value**: {best_value['property']} - {best_value['reasoning']}")

    # Comparison table
    st.subheader("Detailed Comparison")
    comparison_table = comparison.get_comparison_table()

    # Style the table
    st.dataframe(
        comparison_table,
        use_container_width=True,
        height=400
    )

    # Amenity comparison
    st.subheader("Amenities Comparison")
    amenity_comp = comparison.get_amenity_comparison()
    st.dataframe(
        amenity_comp,
        use_container_width=True
    )

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Price Comparison")
        chart_data = pd.DataFrame({
            'Property': comparison.df['Property'],
            'Price': comparison.df['Price_Numeric']
        })
        st.bar_chart(chart_data.set_index('Property'))

    with col2:
        st.subheader("Rooms & Amenities")
        chart_data = pd.DataFrame({
            'Property': comparison.df['Property'],
            'Rooms': comparison.df['Rooms'],
            'Amenities': comparison.df['Amenity_Count']
        })
        st.bar_chart(chart_data.set_index('Property'))


def display_market_insights_ui(insights_data: Dict[str, Any]):
    """
    Display market insights UI in Streamlit.

    Args:
        insights_data: Dictionary with market insights data
    """
    st.subheader("📈 Market Insights")

    # Overall statistics
    stats = insights_data.get('overall_stats')
    if stats:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Properties", stats.get('total_properties', 0))
        with col2:
            st.metric("Average Price", f"${stats.get('average_price', 0):.2f}")
        with col3:
            st.metric("Median Price", f"${stats.get('median_price', 0):.2f}")
        with col4:
            st.metric("Avg Rooms", f"{stats.get('avg_rooms', 0):.1f}")

    # Price distribution
    if 'price_distribution' in insights_data:
        st.subheader("Price Distribution")
        dist = insights_data['price_distribution']
        chart_data = pd.DataFrame({
            'Price Range': dist['bins'],
            'Count': dist['counts']
        })
        st.bar_chart(chart_data.set_index('Price Range'))

    # Cities breakdown
    if stats and 'cities' in stats:
        st.subheader("Properties by City")
        city_data = pd.DataFrame([
            {'City': city, 'Count': count}
            for city, count in stats['cities'].items()
        ])
        st.bar_chart(city_data.set_index('City'))

    # Amenity impact
    if 'amenity_impact' in insights_data:
        st.subheader("Amenity Impact on Price")
        impact_data = pd.DataFrame([
            {'Amenity': amenity.title(), 'Price Increase %': impact}
            for amenity, impact in insights_data['amenity_impact'].items()
        ])
        st.bar_chart(impact_data.set_index('Amenity'))
