"""
Property Display Utilities for Real Estate UI

Provides reusable functions to display properties with modern,
professional styling using custom CSS classes.
"""

import streamlit as st
from typing import Optional, List
from data.schemas import Property


def display_property_card(property: Property, show_amenities: bool = True):
    """
    Display a property in an enhanced card format with image placeholder.

    Args:
        property: Property object to display
        show_amenities: Whether to show amenity icons
    """
    # Get property type as string
    prop_type = property.property_type.value if hasattr(property.property_type, 'value') else str(property.property_type)

    card_html = f"""
    <div class="property-card-enhanced">
        <div class="property-card-image">
            🏠
        </div>
        <div class="property-card-body">
            <div style="margin-bottom: 1rem;">
                <span class="property-type-badge">{prop_type}</span>
                <span class="location-badge" style="margin-left: 0.5rem;">📍 {property.city}</span>
            </div>

            <h3 class="property-card-title">{property.city} {prop_type.title()}</h3>
            <p class="property-card-subtitle">
                {property.rooms} rooms • {property.bathrooms} bathrooms
                {f" • {property.area_sqm} sqm" if property.area_sqm else ""}
            </p>

            <div class="property-price">
                ${property.price:,.0f}
                {f'<span class="property-price-per-sqm">${property.price / property.area_sqm:.2f}/sqm</span>' if property.area_sqm else ''}
            </div>
    """

    if show_amenities:
        amenities = []
        if property.has_parking:
            amenities.append("🅿️ Parking")
        if property.has_balcony:
            amenities.append("🌅 Balcony")
        if property.has_garden:
            amenities.append("🌳 Garden")
        if property.has_pool:
            amenities.append("🏊 Pool")
        if property.is_furnished:
            amenities.append("🛋️ Furnished")
        if property.has_elevator:
            amenities.append("🛗 Elevator")

        if amenities:
            card_html += """
            <div class="property-features">
            """
            for amenity in amenities:
                card_html += f'<span class="property-feature">{amenity}</span>'
            card_html += """
            </div>
            """

    card_html += """
        </div>
    </div>
    """

    st.markdown(card_html, unsafe_allow_html=True)


def display_property_simple(property: Property):
    """
    Display a property in a simple search result card format.

    Args:
        property: Property object to display
    """
    prop_type = property.property_type.value if hasattr(property.property_type, 'value') else str(property.property_type)

    card_html = f"""
    <div class="search-result-card">
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.75rem;">
            <div>
                <h4 style="margin: 0 0 0.5rem 0; color: var(--text-dark); font-size: 1.25rem; font-weight: 700;">
                    {property.city} {prop_type.title()}
                </h4>
                <p style="margin: 0; color: var(--text-medium); font-size: 0.938rem;">
                    {property.rooms} rooms • {property.bathrooms} bathrooms
                    {f" • {property.area_sqm} sqm" if property.area_sqm else ""}
                </p>
            </div>
            <div class="property-price" style="margin: 0;">
                ${property.price:,.0f}
            </div>
        </div>

        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
            <span class="location-badge">📍 {property.city}</span>
            <span class="property-type-badge">{prop_type}</span>
        </div>
    </div>
    """

    st.markdown(card_html, unsafe_allow_html=True)


def display_property_grid(properties: List[Property], max_display: Optional[int] = None):
    """
    Display multiple properties in a responsive grid layout.

    Args:
        properties: List of Property objects to display
        max_display: Maximum number of properties to display (None for all)
    """
    display_props = properties[:max_display] if max_display else properties

    # Use Streamlit columns for grid layout
    cols_per_row = 3
    rows = [display_props[i:i + cols_per_row] for i in range(0, len(display_props), cols_per_row)]

    for row in rows:
        cols = st.columns(len(row))
        for col, prop in zip(cols, row):
            with col:
                display_property_card(prop)


def display_hero_section(title: str, subtitle: str):
    """
    Display a hero section for page headers.

    Args:
        title: Main title text
        subtitle: Subtitle text
    """
    hero_html = f"""
    <div class="hero-section">
        <h1 class="hero-title">{title}</h1>
        <p class="hero-subtitle">{subtitle}</p>
    </div>
    """
    st.markdown(hero_html, unsafe_allow_html=True)


def display_feature_highlight(icon: str, title: str, description: str):
    """
    Display a feature highlight box.

    Args:
        icon: Emoji or icon for the feature
        title: Feature title
        description: Feature description
    """
    feature_html = f"""
    <div class="feature-highlight">
        <div class="feature-highlight-icon">{icon}</div>
        <h3 class="feature-highlight-title">{title}</h3>
        <p class="feature-highlight-text">{description}</p>
    </div>
    """
    st.markdown(feature_html, unsafe_allow_html=True)


def display_stats_row(stats: List[dict]):
    """
    Display a row of statistics boxes.

    Args:
        stats: List of dicts with 'value' and 'label' keys

    Example:
        display_stats_row([
            {"value": "1,234", "label": "Total Properties"},
            {"value": "$450K", "label": "Avg Price"},
            {"value": "89", "label": "Cities"}
        ])
    """
    stats_html = '<div class="stats-container">'

    for stat in stats:
        stats_html += f"""
        <div class="stat-box">
            <div class="stat-value">{stat['value']}</div>
            <div class="stat-label">{stat['label']}</div>
        </div>
        """

    stats_html += '</div>'
    st.markdown(stats_html, unsafe_allow_html=True)


def display_gold_divider():
    """Display a decorative gold divider line."""
    st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)


def display_luxury_card(content: str):
    """
    Display content in a luxury card with gold border.

    Args:
        content: HTML content to display in the card
    """
    card_html = f"""
    <div class="luxury-card">
        {content}
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def create_price_badge(price: float, average_price: float) -> str:
    """
    Create a price comparison badge HTML.

    Args:
        price: Property price
        average_price: Average market price

    Returns:
        HTML string for the badge
    """
    if price < average_price * 0.9:
        badge_class = "price-below-average"
        text = "Below Market"
        icon = "📉"
    elif price > average_price * 1.1:
        badge_class = "price-above-average"
        text = "Above Market"
        icon = "📈"
    else:
        badge_class = "price-average"
        text = "Market Average"
        icon = "📊"

    return f'<span class="price-comparison {badge_class}">{icon} {text}</span>'


def create_status_badge(status: str) -> str:
    """
    Create a property status badge HTML.

    Args:
        status: Property status ("available", "pending", or "sold")

    Returns:
        HTML string for the badge
    """
    status_map = {
        "available": ("status-available", "✅ Available"),
        "pending": ("status-pending", "⏳ Pending"),
        "sold": ("status-sold", "❌ Sold")
    }

    badge_class, text = status_map.get(status.lower(), ("status-available", "Available"))

    return f'<span class="badge {badge_class}" style="padding: 0.5rem 1rem; display: inline-block; border-radius: 999px; font-weight: 600;">{text}</span>'
