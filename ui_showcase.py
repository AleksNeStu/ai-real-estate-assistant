"""
UI Component Showcase
Demonstrates all available UI components for the AI Real Estate Assistant
"""

import streamlit as st
from utils import (
    load_and_inject_styles,
    inject_enhanced_form_styles,
    inject_tailwind_cdn,
    display_hero_section,
    display_feature_highlight,
    display_stats_row,
    display_gold_divider,
    display_luxury_card,
    display_property_card,
    display_property_simple,
    create_price_badge,
    create_status_badge
)
from data.schemas import Property, PropertyType

# Page config
st.set_page_config(
    page_title="UI Component Showcase",
    page_icon="🎨",
    layout="wide"
)

# Load styles
load_and_inject_styles()
inject_enhanced_form_styles()
inject_tailwind_cdn()

# Hero Section
display_hero_section(
    title="🎨 Real Estate UI Components",
    subtitle="Modern, Professional Design for Property Listings"
)

st.markdown("---")

# Stats Row
st.header("Statistics Display")
display_stats_row([
    {"value": "1,868", "label": "Total Properties"},
    {"value": "$425K", "label": "Average Price"},
    {"value": "12", "label": "Cities Covered"},
    {"value": "4.8★", "label": "User Rating"}
])

display_gold_divider()

# Feature Highlights
st.header("Feature Highlights")
col1, col2, col3 = st.columns(3)

with col1:
    display_feature_highlight(
        icon="🤖",
        title="AI-Powered Search",
        description="Advanced AI understands your preferences and finds perfect properties for you."
    )

with col2:
    display_feature_highlight(
        icon="📊",
        title="Market Analytics",
        description="Real-time market insights and price comparisons to make informed decisions."
    )

with col3:
    display_feature_highlight(
        icon="🔔",
        title="Smart Alerts",
        description="Get notified instantly when properties matching your criteria become available."
    )

display_gold_divider()

# Property Cards
st.header("Property Cards")

# Create sample properties
sample_properties = [
    Property(
        city="Warsaw",
        price=450000,
        rooms=3,
        bathrooms=2,
        area_sqm=85,
        property_type=PropertyType.APARTMENT,
        has_parking=True,
        has_balcony=True,
        is_furnished=True,
        has_elevator=True
    ),
    Property(
        city="Krakow",
        price=380000,
        rooms=4,
        bathrooms=2,
        area_sqm=110,
        property_type=PropertyType.HOUSE,
        has_parking=True,
        has_garden=True,
        is_furnished=False,
        has_balcony=False
    ),
    Property(
        city="Gdansk",
        price=520000,
        rooms=2,
        bathrooms=1,
        area_sqm=65,
        property_type=PropertyType.APARTMENT,
        has_parking=False,
        has_balcony=True,
        has_pool=True,
        is_furnished=True,
        has_elevator=True
    )
]

st.subheader("Enhanced Property Cards")
st.caption("Hover over cards to see the lift effect")

col1, col2, col3 = st.columns(3)

with col1:
    display_property_card(sample_properties[0], show_amenities=True)

with col2:
    display_property_card(sample_properties[1], show_amenities=True)

with col3:
    display_property_card(sample_properties[2], show_amenities=True)

st.markdown("<br>", unsafe_allow_html=True)

st.subheader("Simple Property Cards")
st.caption("Compact format for search results")

for prop in sample_properties:
    display_property_simple(prop)

display_gold_divider()

# Badges
st.header("Badges & Indicators")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Price Comparison Badges")
    st.markdown(create_price_badge(350000, 400000), unsafe_allow_html=True)
    st.caption("Below Market Average")
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(create_price_badge(420000, 400000), unsafe_allow_html=True)
    st.caption("Market Average")
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(create_price_badge(500000, 400000), unsafe_allow_html=True)
    st.caption("Above Market Average")

with col2:
    st.subheader("Property Status Badges")
    st.markdown(create_status_badge("available"), unsafe_allow_html=True)
    st.caption("Available for purchase")
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(create_status_badge("pending"), unsafe_allow_html=True)
    st.caption("Sale pending")
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(create_status_badge("sold"), unsafe_allow_html=True)
    st.caption("Already sold")

display_gold_divider()

# Luxury Card
st.header("Luxury Card")
st.caption("Premium gold-bordered card for special content")

luxury_content = """
<h3 style="color: var(--primary-blue); margin-top: 0;">🏆 Premium Listing</h3>
<p style="color: var(--text-dark); font-size: 1.125rem; font-weight: 600; margin: 1rem 0;">
    Exclusive penthouse in the heart of Warsaw
</p>
<p style="color: var(--text-medium); line-height: 1.6;">
    This exceptional property features panoramic city views,
    state-of-the-art amenities, and unparalleled luxury finishes.
    Available only to pre-qualified buyers.
</p>
<div style="margin-top: 1.5rem;">
    <span class="property-price" style="margin: 0;">$1,250,000</span>
</div>
"""

display_luxury_card(luxury_content)

display_gold_divider()

# Custom CSS Classes
st.header("Custom CSS Classes")

st.subheader("Location Badge")
st.markdown('<span class="location-badge">📍 Warsaw City Center</span>', unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)

st.subheader("Property Type Badge")
st.markdown('<span class="property-type-badge">Luxury Apartment</span>', unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)

st.subheader("Property Features")
features_html = """
<div class="property-features">
    <span class="property-feature">🅿️ Parking</span>
    <span class="property-feature">🌅 Balcony</span>
    <span class="property-feature">🌳 Garden</span>
    <span class="property-feature">🏊 Pool</span>
    <span class="property-feature">🛋️ Furnished</span>
    <span class="property-feature">🛗 Elevator</span>
</div>
"""
st.markdown(features_html, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

st.subheader("Amenity Icons")
amenity_html = """
<div style="display: flex; gap: 1rem; flex-wrap: wrap;">
    <span class="amenity-icon">🅿️</span>
    <span class="amenity-icon">🌅</span>
    <span class="amenity-icon">🌳</span>
    <span class="amenity-icon">🏊</span>
    <span class="amenity-icon">🛋️</span>
    <span class="amenity-icon">🛗</span>
</div>
"""
st.markdown(amenity_html, unsafe_allow_html=True)

display_gold_divider()

# Color Palette
st.header("Color Palette")

colors = [
    ("Primary Blue", "#0066cc", "#ffffff"),
    ("Accent Gold", "#d4af37", "#ffffff"),
    ("Accent Teal", "#00a99d", "#ffffff"),
    ("Background Light", "#f8f9fa", "#1a1a1a"),
    ("Text Dark", "#1a1a1a", "#ffffff"),
    ("Success Green", "#10b981", "#ffffff"),
    ("Warning Orange", "#f59e0b", "#ffffff"),
    ("Error Red", "#ef4444", "#ffffff"),
]

color_cols = st.columns(4)
for i, (name, color, text_color) in enumerate(colors):
    with color_cols[i % 4]:
        st.markdown(
            f"""
            <div style="
                background-color: {color};
                color: {text_color};
                padding: 1.5rem;
                border-radius: 0.5rem;
                text-align: center;
                margin-bottom: 1rem;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            ">
                <div style="font-weight: 600; margin-bottom: 0.5rem;">{name}</div>
                <div style="font-family: monospace; font-size: 0.875rem;">{color}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

display_gold_divider()

# Typography
st.header("Typography")

st.markdown(
    """
    <h1>Heading 1 - Main Page Titles</h1>
    <h2>Heading 2 - Section Headers</h2>
    <h3>Heading 3 - Subsections</h3>
    <h4>Heading 4 - Card Titles</h4>
    <p style="font-size: 1.125rem; font-weight: 600;">Large Body Text - Important Information</p>
    <p>Regular Body Text - Standard content with good readability and proper line height for comfortable reading.</p>
    <p style="font-size: 0.875rem; color: var(--text-medium);">Small Text - Captions and supplementary information</p>
    """,
    unsafe_allow_html=True
)

display_gold_divider()

# Footer
st.markdown(
    """
    <div style="text-align: center; padding: 2rem; color: var(--text-medium);">
        <p style="font-size: 0.938rem; margin-bottom: 0.5rem;">
            <strong>AI Real Estate Assistant V3</strong>
        </p>
        <p style="font-size: 0.875rem;">
            Modern UI • Professional Design • Real Estate Focused
        </p>
    </div>
    """,
    unsafe_allow_html=True
)
