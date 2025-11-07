"""
Comprehensive market dashboard with KPIs, charts, and insights.

Provides a complete market overview combining:
- Key performance indicators (KPIs)
- Interactive price charts
- Location breakdowns
- Trend indicators
- Market statistics
"""

from typing import Optional
import streamlit as st
from data.schemas import PropertyCollection
from analytics import MarketInsights, TrendDirection
from ui.price_charts import (
    create_price_distribution_chart,
    create_price_by_location_chart,
    create_price_amenity_scatter,
    create_price_per_sqm_chart
)
from ui.metrics import display_metrics_row, display_stat_box, format_number


def display_market_dashboard(
    properties: PropertyCollection,
    insights: Optional[MarketInsights] = None,
    show_charts: bool = True,
    show_kpis: bool = True
):
    """
    Display a comprehensive market dashboard.

    Args:
        properties: Collection of properties
        insights: Optional MarketInsights object (will be created if not provided)
        show_charts: Whether to display charts
        show_kpis: Whether to display KPI metrics
    """
    # Create insights if not provided
    if insights is None:
        insights = MarketInsights(properties)

    # Get statistics
    stats = insights.get_overall_statistics()
    trend = insights.get_price_trend()

    # === KPI METRICS ROW ===
    if show_kpis:
        st.markdown("### 📊 Market Overview")

        # Prepare metrics
        metrics = [
            {
                'title': 'Total Properties',
                'value': f"{stats.total_properties:,}",
                'icon': '🏠',
                'help_text': 'Total number of properties in the market'
            },
            {
                'title': 'Average Price',
                'value': f"${stats.average_price:,.0f}",
                'delta': _format_trend_delta(trend),
                'delta_color': _get_trend_color(trend),
                'icon': '💵',
                'help_text': 'Mean price across all properties'
            },
            {
                'title': 'Median Price',
                'value': f"${stats.median_price:,.0f}",
                'icon': '📊',
                'help_text': 'Middle value - less affected by outliers'
            },
            {
                'title': 'Price Range',
                'value': f"${stats.min_price:.0f} - ${stats.max_price:.0f}",
                'icon': '📏',
                'help_text': 'Minimum to maximum price'
            }
        ]

        display_metrics_row(metrics, columns=4)

        st.divider()

    # === MARKET STATISTICS ===
    if show_kpis:
        st.markdown("### 📈 Market Statistics")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            display_stat_box(
                title="Avg Rooms",
                value=f"{stats.avg_rooms:.1f}",
                subtitle=f"rooms per property",
                icon="🛏️",
                color="#1f77b4"
            )

        with col2:
            display_stat_box(
                title="With Parking",
                value=f"{stats.parking_percentage:.0f}%",
                subtitle=f"properties have parking",
                icon="🚗",
                color="#2ca02c"
            )

        with col3:
            display_stat_box(
                title="With Garden",
                value=f"{stats.garden_percentage:.0f}%",
                subtitle=f"properties have gardens",
                icon="🌳",
                color="#ff7f0e"
            )

        with col4:
            display_stat_box(
                title="Furnished",
                value=f"{stats.furnished_percentage:.0f}%",
                subtitle=f"properties are furnished",
                icon="🛋️",
                color="#d62728"
            )

        st.divider()

    # === CHARTS SECTION ===
    if show_charts:
        # Price Distribution
        st.markdown("### 📊 Price Distribution")
        fig_dist = create_price_distribution_chart(properties, bins=20, show_stats=True)
        st.plotly_chart(fig_dist, use_container_width=True)

        # Two-column layout for charts
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🏙️ Price by Location")
            fig_location = create_price_by_location_chart(properties, sort_by="median")
            st.plotly_chart(fig_location, use_container_width=True)

        with col2:
            st.markdown("### ✨ Price vs Amenities")
            fig_amenities = create_price_amenity_scatter(properties)
            st.plotly_chart(fig_amenities, use_container_width=True)

        # Price per sqm (if data available)
        if stats.avg_price_per_sqm is not None:
            st.markdown("### 📐 Price per Square Meter")
            fig_sqm = create_price_per_sqm_chart(properties)
            st.plotly_chart(fig_sqm, use_container_width=True)

    # === LOCATION INSIGHTS ===
    st.markdown("### 🗺️ Location Breakdown")

    if stats.cities:
        # Display top cities
        sorted_cities = sorted(stats.cities.items(), key=lambda x: x[1], reverse=True)

        cols = st.columns(min(len(sorted_cities), 3))

        for i, (city, count) in enumerate(sorted_cities[:3]):
            with cols[i]:
                # Get city insights
                city_insights = insights.get_location_insights(city)

                if city_insights:
                    st.markdown(f"**{city}**")
                    st.metric(
                        label="Properties",
                        value=count,
                        delta=None
                    )
                    st.metric(
                        label="Avg Price",
                        value=f"${city_insights.avg_price:,.0f}",
                        delta=None
                    )

                    # Price comparison badge
                    if city_insights.price_comparison == "above_average":
                        st.markdown("🔴 Above market average")
                    elif city_insights.price_comparison == "below_average":
                        st.markdown("🟢 Below market average")
                    else:
                        st.markdown("🟡 Near market average")

    # === MARKET INSIGHTS ===
    with st.expander("📋 Detailed Market Insights", expanded=False):
        st.markdown("#### Price Trend Analysis")

        # Trend information
        trend_emoji = {
            TrendDirection.INCREASING: "📈",
            TrendDirection.DECREASING: "📉",
            TrendDirection.STABLE: "➡️",
            TrendDirection.INSUFFICIENT_DATA: "❓"
        }

        st.write(
            f"{trend_emoji.get(trend.direction, '❓')} **{trend.direction.value.title()}** "
            f"({trend.change_percent:+.1f}%)"
        )
        st.write(f"Sample size: {trend.sample_size} properties")
        st.write(f"Confidence: {trend.confidence}")

        st.divider()

        # Best value properties
        st.markdown("#### 🎯 Best Value Properties")
        best_values = insights.get_best_value_properties(top_n=5)

        if best_values:
            for i, prop in enumerate(best_values, 1):
                col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

                with col1:
                    st.write(f"**{i}. {prop['city']}** ({prop['property_type']})")
                with col2:
                    st.write(f"${prop['price']:,.0f}/mo")
                with col3:
                    st.write(f"{prop['rooms']:.0f} rooms")
                with col4:
                    st.write(f"⭐ {prop['value_score']:.2f}")
        else:
            st.info("No properties available for value analysis")

        st.divider()

        # Amenity impact
        st.markdown("#### 🛠️ Amenity Price Impact")
        amenity_impact = insights.get_amenity_impact_on_price()

        if amenity_impact:
            # Sort by impact
            sorted_amenities = sorted(amenity_impact.items(), key=lambda x: x[1], reverse=True)

            for amenity, impact in sorted_amenities:
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.write(f"**{amenity.title()}**")
                with col2:
                    color = "🟢" if impact > 0 else "🔴" if impact < 0 else "⚪"
                    st.write(f"{color} {impact:+.1f}%")
        else:
            st.info("Insufficient data for amenity analysis")


def display_compact_dashboard(
    properties: PropertyCollection,
    insights: Optional[MarketInsights] = None
):
    """
    Display a compact version of the market dashboard.

    Args:
        properties: Collection of properties
        insights: Optional MarketInsights object
    """
    # Create insights if not provided
    if insights is None:
        insights = MarketInsights(properties)

    stats = insights.get_overall_statistics()

    # Compact metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Properties", f"{stats.total_properties:,}", help="Number of properties")

    with col2:
        st.metric("Average Price", f"${stats.average_price:,.0f}", help="Mean price")

    with col3:
        st.metric("Median Price", f"${stats.median_price:,.0f}", help="Median price")

    # Single chart
    fig = create_price_distribution_chart(properties, bins=15, show_stats=True)
    st.plotly_chart(fig, use_container_width=True)


def _format_trend_delta(trend) -> Optional[str]:
    """Format price trend as delta string."""
    if trend.direction == TrendDirection.INSUFFICIENT_DATA:
        return None

    return f"{trend.change_percent:+.1f}%"


def _get_trend_color(trend) -> str:
    """Get delta color based on trend direction."""
    if trend.direction == TrendDirection.INCREASING:
        return "inverse"  # Red for increasing (bad for buyers)
    elif trend.direction == TrendDirection.DECREASING:
        return "normal"  # Green for decreasing (good for buyers)
    else:
        return "off"


def display_location_comparison_dashboard(
    properties: PropertyCollection,
    city1: str,
    city2: str,
    insights: Optional[MarketInsights] = None
):
    """
    Display a dashboard comparing two locations.

    Args:
        properties: Collection of properties
        city1: First city to compare
        city2: Second city to compare
        insights: Optional MarketInsights object
    """
    # Create insights if not provided
    if insights is None:
        insights = MarketInsights(properties)

    st.markdown(f"### 🏙️ Comparing {city1} vs {city2}")

    # Get comparison data
    comparison = insights.compare_locations(city1, city2)

    if 'error' in comparison:
        st.error(comparison['error'])
        return

    # Display comparison metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"#### {city1}")
        st.metric("Properties", comparison['city1']['property_count'])
        st.metric("Avg Price", f"${comparison['city1']['avg_price']:,.0f}")
        st.metric("Median Price", f"${comparison['city1']['median_price']:,.0f}")

    with col2:
        st.markdown("#### Difference")
        st.metric(
            "Price Difference",
            f"${abs(comparison['price_difference']):,.0f}",
            delta=f"{comparison['price_difference_percent']:+.1f}%"
        )
        st.markdown(f"**Cheaper:** {comparison['cheaper_city']}")
        st.markdown(f"**More Properties:** {comparison['more_properties']}")

    with col3:
        st.markdown(f"#### {city2}")
        st.metric("Properties", comparison['city2']['property_count'])
        st.metric("Avg Price", f"${comparison['city2']['avg_price']:,.0f}")
        st.metric("Median Price", f"${comparison['city2']['median_price']:,.0f}")

    # Amenity comparison
    st.markdown("#### 🛠️ Amenity Availability")

    amenities1 = comparison['city1']['amenity_availability']
    amenities2 = comparison['city2']['amenity_availability']

    for amenity in amenities1.keys():
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            st.write(f"**{amenity.title()}**")
        with col2:
            st.write(f"{amenities1[amenity]:.0f}%")
        with col3:
            st.write(f"{amenities2[amenity]:.0f}%")
