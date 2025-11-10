"""
Enhanced property comparison dashboard.

Provides comprehensive side-by-side property comparisons with:
- Property cards with key details
- Radar chart comparisons
- Feature matrix tables
- Price comparison visualizations
- Recommendations and best value analysis
- Export functionality
"""

from typing import List, Optional
import streamlit as st
from data.schemas import Property
from ui.comparison_viz import PropertyComparison
from ui.radar_charts import create_property_radar_chart, create_amenity_radar_chart
from ui.price_charts import create_price_comparison_chart
from ui.metrics import display_metric_card


def display_comparison_dashboard(
    properties: List[Property],
    show_radar: bool = True,
    show_recommendations: bool = True,
    show_export: bool = False
):
    """
    Display a comprehensive property comparison dashboard.

    Args:
        properties: List of 2-6 properties to compare
        show_radar: Whether to show radar chart comparison
        show_recommendations: Whether to show best value recommendations
        show_export: Whether to show export functionality
    """
    if not properties:
        st.warning("No properties selected for comparison")
        return

    if len(properties) < 2:
        st.warning("Please select at least 2 properties to compare")
        return

    if len(properties) > 6:
        st.warning("Maximum 6 properties can be compared at once")
        properties = properties[:6]

    # Title
    st.markdown(f"### 🔄 Comparing {len(properties)} Properties")

    # === PROPERTY CARDS ===
    st.markdown("#### Property Overview")

    # Display cards in columns
    cols = st.columns(len(properties))

    for i, (prop, col) in enumerate(zip(properties, cols)):
        with col:
            _display_property_card(prop, index=i+1)

    st.divider()

    # === PRICE COMPARISON ===
    st.markdown("#### 💰 Price Comparison")

    # Create comparison object
    comparison = PropertyComparison(properties)
    price_comp = comparison.get_price_comparison()

    # Display price metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Cheapest",
            f"${price_comp['cheapest']['price']:,.0f}",
            help=f"{price_comp['cheapest']['city']}"
        )

    with col2:
        st.metric(
            "Most Expensive",
            f"${price_comp['most_expensive']['price']:,.0f}",
            help=f"{price_comp['most_expensive']['city']}"
        )

    with col3:
        st.metric(
            "Price Range",
            f"${price_comp['price_range']:,.0f}",
            help="Difference between min and max"
        )

    # Price comparison chart
    fig = create_price_comparison_chart(properties)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # === COMPARISON TABLE ===
    st.markdown("#### 📊 Detailed Comparison")

    table = comparison.get_comparison_table()
    st.dataframe(table, use_container_width=True, hide_index=True)

    st.divider()

    # === RADAR CHARTS ===
    if show_radar:
        st.markdown("#### 🎯 Multi-Dimensional Comparison")

        tab1, tab2 = st.tabs(["Overall Comparison", "Amenities Only"])

        with tab1:
            try:
                fig_radar = create_property_radar_chart(properties)
                st.plotly_chart(fig_radar, use_container_width=True)
                st.caption("📌 Values are normalized for fair comparison. Larger area = better value.")
            except ValueError as e:
                st.error(str(e))

        with tab2:
            try:
                fig_amenity = create_amenity_radar_chart(properties)
                st.plotly_chart(fig_amenity, use_container_width=True)
                st.caption("📌 Shows which properties have which amenities.")
            except ValueError as e:
                st.error(str(e))

        st.divider()

    # === AMENITY COMPARISON ===
    st.markdown("#### 🛠️ Amenity Comparison")

    amenity_comp = comparison.get_amenity_comparison()
    st.dataframe(amenity_comp, use_container_width=True)

    st.divider()

    # === BEST VALUE ANALYSIS ===
    if show_recommendations:
        st.markdown("#### ⭐ Best Value Analysis")

        best_value = comparison.get_best_value()

        # Display best value prominently
        st.success(f"**🏆 Best Value: {best_value['city']}** (Score: {best_value['value_score']:.2f}/1.0)")

        st.markdown(f"**Why?** {best_value['reasoning']}")

        # Show all scores
        st.markdown("**All Properties Ranked:**")

        # Create a sorted list
        prop_scores = []
        for prop in properties:
            # Calculate value score for each
            comp_temp = PropertyComparison([prop])
            # We need to get the score somehow - let's recalculate
            price_norm = (max(p.price for p in properties) - prop.price) / (max(p.price for p in properties) - min(p.price for p in properties)) if len(properties) > 1 else 0.5
            rooms_norm = (prop.rooms - min(p.rooms for p in properties)) / (max(p.rooms for p in properties) - min(p.rooms for p in properties)) if len(properties) > 1 and max(p.rooms for p in properties) != min(p.rooms for p in properties) else 0.5

            amenity_count = sum([
                prop.has_parking, prop.has_garden, prop.has_pool,
                prop.is_furnished, prop.has_balcony, prop.has_elevator
            ])
            amenity_norm = amenity_count / 6

            score = price_norm * 0.4 + rooms_norm * 0.3 + amenity_norm * 0.3

            prop_scores.append({
                'property': f"{prop.city} - ${prop.price}",
                'score': score
            })

        # Sort by score
        prop_scores.sort(key=lambda x: x['score'], reverse=True)

        # Display as a simple table
        for i, item in enumerate(prop_scores, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            st.write(f"{medal} {item['property']} - Score: {item['score']:.3f}")

        st.divider()

    # === PROS/CONS ANALYSIS ===
    st.markdown("#### ✅ Pros & Cons")

    cols = st.columns(len(properties))

    for prop, col in zip(properties, cols):
        with col:
            st.markdown(f"**{prop.city}**")

            # Pros
            pros = _get_property_pros(prop, properties)
            if pros:
                st.markdown("**Pros:**")
                for pro in pros:
                    st.markdown(f"✅ {pro}")

            # Cons
            cons = _get_property_cons(prop, properties)
            if cons:
                st.markdown("**Cons:**")
                for con in cons:
                    st.markdown(f"❌ {con}")

    # === EXPORT OPTIONS ===
    if show_export:
        st.divider()
        st.markdown("#### 💾 Export Comparison")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("📄 Export as Markdown"):
                markdown = _export_comparison_markdown(properties, comparison)
                st.download_button(
                    "Download Markdown",
                    data=markdown,
                    file_name="property_comparison.md",
                    mime="text/markdown"
                )

        with col2:
            if st.button("📊 Export as CSV"):
                csv_data = table.to_csv(index=False)
                st.download_button(
                    "Download CSV",
                    data=csv_data,
                    file_name="property_comparison.csv",
                    mime="text/csv"
                )


def display_compact_comparison(properties: List[Property]):
    """
    Display a compact comparison view.

    Args:
        properties: List of properties to compare
    """
    if len(properties) < 2:
        st.info("Select at least 2 properties to compare")
        return

    comparison = PropertyComparison(properties)

    # Price comparison
    price_comp = comparison.get_price_comparison()

    cols = st.columns(len(properties))

    for prop, col in zip(properties, cols):
        with col:
            st.markdown(f"**{prop.city}**")
            st.metric("Price", f"${prop.price}")
            st.write(f"{prop.rooms} bed, {prop.bathrooms} bath")

            # Amenity count
            amenity_count = sum([
                prop.has_parking, prop.has_garden, prop.has_pool,
                prop.is_furnished, prop.has_balcony, prop.has_elevator
            ])
            st.write(f"✨ {amenity_count}/6 amenities")

    # Best value
    best_value = comparison.get_best_value()
    st.success(f"🏆 Best Value: {best_value['city']}")


def _display_property_card(prop: Property, index: int):
    """Display a single property card."""
    # Color based on index
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    color = colors[(index - 1) % len(colors)]

    # Card HTML
    html = f"""
    <div style="
        border: 2px solid {color};
        border-radius: 10px;
        padding: 15px;
        background-color: {color}10;
        margin-bottom: 10px;
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <h4 style="margin: 0; color: {color};">#{index}</h4>
            <span style="font-size: 24px; font-weight: bold; color: {color};">${prop.price}</span>
        </div>
        <div style="margin-bottom: 8px;">
            <strong>📍 {prop.city}</strong>
        </div>
        <div style="font-size: 14px; color: var(--text-secondary);">
            🏠 {prop.property_type}<br>
            🛏️ {prop.rooms} bed | 🚿 {prop.bathrooms} bath<br>
            {f'📐 {prop.area_sqm} sqm' if prop.area_sqm else ''}
        </div>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)

    # Amenities as badges
    amenities = []
    if prop.has_parking:
        amenities.append("🚗")
    if prop.has_garden:
        amenities.append("🌳")
    if prop.has_pool:
        amenities.append("🏊")
    if prop.is_furnished:
        amenities.append("🛋️")
    if prop.has_balcony:
        amenities.append("🏖️")
    if prop.has_elevator:
        amenities.append("🛗")

    if amenities:
        st.markdown(" ".join(amenities))
    else:
        st.caption("No amenities")


def _get_property_pros(prop: Property, all_properties: List[Property]) -> List[str]:
    """Get list of pros for a property."""
    pros = []

    # Price comparison
    avg_price = sum(p.price for p in all_properties) / len(all_properties)
    if prop.price < avg_price * 0.9:
        pros.append(f"Below average price (${avg_price:.0f})")

    # Rooms
    max_rooms = max(p.rooms for p in all_properties)
    if prop.rooms == max_rooms:
        pros.append(f"Most rooms ({prop.rooms})")

    # Amenities
    amenity_count = sum([
        prop.has_parking, prop.has_garden, prop.has_pool,
        prop.is_furnished, prop.has_balcony, prop.has_elevator
    ])

    max_amenities = max(
        sum([p.has_parking, p.has_garden, p.has_pool, p.is_furnished, p.has_balcony, p.has_elevator])
        for p in all_properties
    )

    if amenity_count == max_amenities and amenity_count > 0:
        pros.append(f"Most amenities ({amenity_count})")

    # Specific amenities
    if prop.has_pool and not all(p.has_pool for p in all_properties):
        pros.append("Has swimming pool")

    if prop.has_garden:
        pros.append("Has garden")

    # Area
    if prop.area_sqm:
        max_area = max((p.area_sqm for p in all_properties if p.area_sqm), default=0)
        if prop.area_sqm == max_area:
            pros.append(f"Largest area ({prop.area_sqm} sqm)")

    return pros


def _get_property_cons(prop: Property, all_properties: List[Property]) -> List[str]:
    """Get list of cons for a property."""
    cons = []

    # Price comparison
    avg_price = sum(p.price for p in all_properties) / len(all_properties)
    if prop.price > avg_price * 1.1:
        cons.append(f"Above average price (${avg_price:.0f})")

    # Rooms
    min_rooms = min(p.rooms for p in all_properties)
    if prop.rooms == min_rooms and len(all_properties) > 1:
        cons.append(f"Fewest rooms ({prop.rooms})")

    # Amenities
    amenity_count = sum([
        prop.has_parking, prop.has_garden, prop.has_pool,
        prop.is_furnished, prop.has_balcony, prop.has_elevator
    ])

    if amenity_count == 0:
        cons.append("No amenities")
    elif amenity_count < 2:
        cons.append("Limited amenities")

    # Specific missing amenities
    if not prop.has_parking and any(p.has_parking for p in all_properties):
        cons.append("No parking")

    if not prop.is_furnished and any(p.is_furnished for p in all_properties):
        cons.append("Not furnished")

    return cons


def _export_comparison_markdown(properties: List[Property], comparison: PropertyComparison) -> str:
    """Export comparison as Markdown."""
    md = f"# Property Comparison Report\n\n"
    md += f"Comparing {len(properties)} properties\n\n"

    # Price comparison
    price_comp = comparison.get_price_comparison()
    md += f"## Price Overview\n\n"
    md += f"- **Cheapest**: {price_comp['cheapest']['city']} - ${price_comp['cheapest']['price']:,.0f}\n"
    md += f"- **Most Expensive**: {price_comp['most_expensive']['city']} - ${price_comp['most_expensive']['price']:,.0f}\n"
    md += f"- **Average**: ${price_comp['avg_price']:,.0f}\n"
    md += f"- **Range**: ${price_comp['price_range']:,.0f}\n\n"

    # Best value
    best_value = comparison.get_best_value()
    md += f"## Best Value\n\n"
    md += f"**{best_value['city']}** (Score: {best_value['value_score']:.2f})\n\n"
    md += f"{best_value['reasoning']}\n\n"

    # Individual properties
    md += f"## Property Details\n\n"
    for i, prop in enumerate(properties, 1):
        md += f"### {i}. {prop.city}\n\n"
        md += f"- **Price**: ${prop.price:,.0f}/month\n"
        md += f"- **Type**: {prop.property_type}\n"
        md += f"- **Rooms**: {prop.rooms} bed, {prop.bathrooms} bath\n"
        if prop.area_sqm:
            md += f"- **Area**: {prop.area_sqm} sqm (${prop.price/prop.area_sqm:.2f}/sqm)\n"

        md += f"- **Amenities**: "
        amenities = []
        if prop.has_parking:
            amenities.append("Parking")
        if prop.has_garden:
            amenities.append("Garden")
        if prop.has_pool:
            amenities.append("Pool")
        if prop.is_furnished:
            amenities.append("Furnished")
        if prop.has_balcony:
            amenities.append("Balcony")
        if prop.has_elevator:
            amenities.append("Elevator")

        md += ", ".join(amenities) if amenities else "None"
        md += "\n\n"

    return md
