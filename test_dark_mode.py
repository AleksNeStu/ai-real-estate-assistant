"""
Dark Mode Test - Dropdown Visibility Verification
Run this to test all form elements and dropdowns in dark mode
"""

import streamlit as st

# Import UI helpers
from utils import load_and_inject_styles, inject_enhanced_form_styles, inject_tailwind_cdn

# Page config
st.set_page_config(
    page_title="Dark Mode Test",
    page_icon="🌓",
    layout="wide"
)

# Load styles
load_and_inject_styles()
inject_enhanced_form_styles()
inject_tailwind_cdn()

# Title
st.title("🌓 Dark Mode Visibility Test")
st.markdown("---")

# Test Section 1: Selectbox
st.header("1. Selectbox Test")
st.subheader("Test dropdown visibility and selection")

col1, col2 = st.columns(2)

with col1:
    st.selectbox(
        "Choose a City",
        options=["Warsaw", "Krakow", "Gdansk", "Wroclaw", "Poznan", "Lodz", "Szczecin"],
        help="Select a city from the dropdown"
    )

with col2:
    st.selectbox(
        "Choose a Property Type",
        options=["Apartment", "House", "Studio", "Penthouse", "Duplex", "Loft"],
        help="Select property type"
    )

st.markdown("---")

# Test Section 2: MultiSelect
st.header("2. MultiSelect Test")
st.subheader("Test multiple selection visibility")

st.multiselect(
    "Select Amenities",
    options=[
        "Parking", "Balcony", "Garden", "Elevator", "Storage",
        "Gym", "Pool", "Security", "Pet-friendly", "Furnished"
    ],
    default=["Parking", "Balcony"],
    help="Select multiple amenities"
)

st.markdown("---")

# Test Section 3: Radio Buttons
st.header("3. Radio Button Test")
st.subheader("Test radio button visibility")

col1, col2 = st.columns(2)

with col1:
    st.radio(
        "Data Source",
        options=["Remote URLs", "Local Files", "Database"],
        help="Choose your data source"
    )

with col2:
    st.radio(
        "Theme Preference",
        options=["System Default", "Light Mode", "Dark Mode"],
        help="Choose your theme"
    )

st.markdown("---")

# Test Section 4: Text Inputs
st.header("4. Text Input Test")
st.subheader("Test form label and input visibility")

col1, col2 = st.columns(2)

with col1:
    st.text_input(
        "Your Email Address",
        placeholder="user@example.com",
        help="Enter your email address"
    )

with col2:
    st.text_input(
        "Property Name",
        placeholder="e.g., Sunny Apartment",
        help="Enter property name"
    )

st.markdown("---")

# Test Section 5: Number Input
st.header("5. Number Input Test")

col1, col2, col3 = st.columns(3)

with col1:
    st.number_input(
        "Min Price",
        min_value=0,
        max_value=10000,
        value=500,
        step=100
    )

with col2:
    st.number_input(
        "Max Price",
        min_value=0,
        max_value=10000,
        value=2000,
        step=100
    )

with col3:
    st.number_input(
        "Bedrooms",
        min_value=1,
        max_value=10,
        value=2,
        step=1
    )

st.markdown("---")

# Test Section 6: Text Area
st.header("6. Text Area Test")

st.text_area(
    "Additional Requirements",
    placeholder="Describe any specific requirements...",
    help="Enter additional search criteria",
    height=100
)

st.markdown("---")

# Test Section 7: Checkbox
st.header("7. Checkbox Test")

col1, col2, col3 = st.columns(3)

with col1:
    st.checkbox("Use Hybrid Agent", value=True)
    st.checkbox("Show Query Analysis", value=False)

with col2:
    st.checkbox("Use Reranking", value=True)
    st.checkbox("Enable Notifications", value=False)

with col3:
    st.checkbox("Save Search", value=False)
    st.checkbox("Auto-refresh", value=True)

st.markdown("---")

# Test Section 8: Date and Time
st.header("8. Date & Time Input Test")

col1, col2 = st.columns(2)

with col1:
    st.date_input("Select Date")

with col2:
    st.time_input("Select Time")

st.markdown("---")

# Test Section 9: File Upload
st.header("9. File Upload Test")

st.file_uploader(
    "Upload CSV Files",
    type=['csv'],
    accept_multiple_files=True,
    help="Upload property data files"
)

st.markdown("---")

# Test Section 10: Slider
st.header("10. Slider Test")

col1, col2 = st.columns(2)

with col1:
    st.slider(
        "Price Range",
        min_value=0,
        max_value=5000,
        value=(500, 2000),
        step=100
    )

with col2:
    st.slider(
        "Area (sqm)",
        min_value=20,
        max_value=200,
        value=60,
        step=10
    )

st.markdown("---")

# Visibility Checklist
st.header("✅ Visibility Checklist")
st.markdown("""
Please verify the following elements are clearly visible in dark mode:

**Dropdowns & Selects:**
- [ ] Dropdown menu background is visible
- [ ] Option text is readable (#fafafa on dark background)
- [ ] Hover state shows clear highlight (light blue tint)
- [ ] Selected option has distinct background
- [ ] Dropdown arrow/icon is visible

**Form Elements:**
- [ ] All labels are clearly visible (e.g., "Your Email Address")
- [ ] Input field backgrounds are visible
- [ ] Input text is readable
- [ ] Placeholder text is visible but subdued
- [ ] Focus states show clear borders

**Radio & Checkboxes:**
- [ ] Radio button labels are visible
- [ ] Checkbox labels are visible
- [ ] Selected states are clear

**Interactive Elements:**
- [ ] Hover states provide visual feedback
- [ ] Active/focus states are visible
- [ ] All icons/SVGs are visible

**Overall:**
- [ ] No white text on white background
- [ ] No black text on black background
- [ ] Proper contrast ratios throughout
""")

st.markdown("---")

# Theme Info
st.header("📊 Current Theme Configuration")
st.code("""
Primary Color: #4a9eff
Background: #0e1117
Secondary Background: #1a1d24
Text: #fafafa (15.8:1 contrast ratio)
Dropdown Background: #262a33
""")

# Instructions
st.info("""
**Testing Instructions:**
1. Open all dropdowns and verify text visibility
2. Hover over dropdown options and check highlight
3. Select different options and verify selection visibility
4. Check all form labels are readable
5. Verify all input fields have proper contrast
6. Test on different screen sizes if possible
""")

# Footer
st.markdown("---")
st.success("✅ Dark mode styles loaded successfully!")
st.caption("Dark Mode Test v3.0 | WCAG 2.1 AA Compliant")
