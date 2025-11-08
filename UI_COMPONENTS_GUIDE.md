# Real Estate UI Components Guide

This guide demonstrates how to use the modern, professional UI components designed specifically for the AI Real Estate Assistant.

## Overview

The V3 UI modernization includes:
- **Professional Light Theme** with trust blue (#0066cc) and luxury gold (#d4af37) accents
- **Real Estate-Specific Components** for property display
- **Responsive Design** that works on all screen sizes
- **Enhanced User Experience** with smooth transitions and hover effects

## Getting Started

First, ensure you have the styles loaded in your app:

```python
from utils import load_and_inject_styles, inject_enhanced_form_styles, inject_tailwind_cdn

# In your main app file (typically at the top, after st.set_page_config)
load_and_inject_styles()
inject_enhanced_form_styles()
inject_tailwind_cdn()
```

## Property Display Components

### 1. Enhanced Property Card

Display a property in a beautiful card with image placeholder, amenities, and pricing:

```python
from utils import display_property_card
from data.schemas import Property

# Assuming you have a Property object
property = Property(
    city="Warsaw",
    price=450000,
    rooms=3,
    bathrooms=2,
    area_sqm=85,
    property_type="apartment",
    has_parking=True,
    has_balcony=True,
    is_furnished=True
)

display_property_card(property, show_amenities=True)
```

**Features:**
- Gradient image placeholder with house icon
- Property type and location badges
- Price highlighting with price per sqm
- Amenity icons (parking, balcony, garden, pool, etc.)
- Hover effects with lift and shadow

### 2. Simple Property Card

For search results or compact listings:

```python
from utils import display_property_simple

display_property_simple(property)
```

**Features:**
- Compact layout with essential info
- Gold accent border on the left
- Price prominently displayed
- Hover effect with horizontal slide

### 3. Property Grid

Display multiple properties in a responsive grid:

```python
from utils import display_property_grid

properties = [property1, property2, property3, property4]

# Display all properties
display_property_grid(properties)

# Or limit to first 6
display_property_grid(properties, max_display=6)
```

**Features:**
- Responsive 3-column grid (adapts to screen size)
- Automatic wrapping
- Consistent spacing

## Page Layout Components

### 4. Hero Section

Create impactful page headers:

```python
from utils import display_hero_section

display_hero_section(
    title="Find Your Dream Home",
    subtitle="Explore thousands of properties with AI-powered search"
)
```

**Features:**
- Blue gradient background
- Large, bold typography
- Perfect for landing pages or section headers

### 5. Feature Highlights

Showcase key features or benefits:

```python
from utils import display_feature_highlight

display_feature_highlight(
    icon="🏠",
    title="AI-Powered Search",
    description="Our advanced AI understands your preferences and finds the perfect properties for you."
)
```

**Features:**
- Large icon display
- Blue border highlight
- Clean, readable layout

### 6. Stats Row

Display impressive statistics:

```python
from utils import display_stats_row

display_stats_row([
    {"value": "1,868", "label": "Total Properties"},
    {"value": "$425K", "label": "Average Price"},
    {"value": "12", "label": "Cities"},
    {"value": "4.8★", "label": "User Rating"}
])
```

**Features:**
- Responsive flex layout
- Hover effects
- Large, bold numbers

## Utility Components

### 7. Gold Divider

Add elegant visual separation:

```python
from utils import display_gold_divider

display_gold_divider()
```

### 8. Luxury Card

Wrap content in a premium gold-bordered card:

```python
from utils import display_luxury_card

content = """
<h3 style="color: var(--primary-blue); margin-top: 0;">Premium Listing</h3>
<p style="color: var(--text-medium);">This is an exclusive property available only to verified buyers.</p>
"""

display_luxury_card(content)
```

### 9. Price Comparison Badge

Show how a property compares to market average:

```python
from utils import create_price_badge

property_price = 450000
market_average = 500000

badge_html = create_price_badge(property_price, market_average)
st.markdown(badge_html, unsafe_allow_html=True)
```

**Generates:**
- 📉 Below Market (green) if < 90% of average
- 📊 Market Average (blue) if within 90-110%
- 📈 Above Market (red) if > 110% of average

### 10. Status Badge

Display property availability status:

```python
from utils import create_status_badge

status_html = create_status_badge("available")  # or "pending", "sold"
st.markdown(status_html, unsafe_allow_html=True)
```

## CSS Classes Reference

You can also use the CSS classes directly in your HTML:

### Property Cards
- `.property-card` - Basic property card
- `.property-card-enhanced` - Enhanced card with image area
- `.search-result-card` - Compact search result card
- `.luxury-card` - Premium gold-bordered card

### Badges
- `.badge-primary` - Blue badge
- `.badge-success` - Green badge
- `.badge-warning` - Orange badge
- `.badge-gold` - Gold gradient badge
- `.location-badge` - Teal location badge
- `.property-type-badge` - Teal property type badge

### Status Indicators
- `.status-available` - Green availability indicator
- `.status-pending` - Orange pending indicator
- `.status-sold` - Red sold indicator

### Layout
- `.property-grid` - CSS Grid layout for properties
- `.stats-container` - Flexbox container for stats
- `.property-features` - Flexbox container for amenities

### Typography
- `.property-price` - Large gold price display
- `.property-price-per-sqm` - Price per square meter
- `.hero-title` - Large hero section title
- `.hero-subtitle` - Hero section subtitle

## Color Palette

The light theme uses these carefully selected colors:

```css
/* Primary Colors - Trust & Professionalism */
--primary-blue: #0066cc
--primary-blue-hover: #0052a3
--primary-blue-light: #e6f2ff

/* Secondary Colors - Real Estate Accents */
--accent-gold: #d4af37
--accent-gold-hover: #b8992d
--accent-teal: #00a99d

/* Backgrounds - Clean & Spacious */
--bg-white: #ffffff
--bg-light: #f8f9fa
--bg-lighter: #f1f3f5

/* Text - Readable & Accessible */
--text-dark: #1a1a1a
--text-medium: #4a5568
--text-light: #718096

/* Borders & Dividers */
--border-light: #e2e8f0
--border-medium: #cbd5e0
```

## Spacing System

Use consistent spacing throughout:

```css
--space-xs: 0.25rem  /* 4px */
--space-sm: 0.5rem   /* 8px */
--space-md: 1rem     /* 16px */
--space-lg: 1.5rem   /* 24px */
--space-xl: 2rem     /* 32px */
--space-2xl: 3rem    /* 48px */
```

## Shadow System

Create depth with shadows:

```css
--shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.05)
--shadow-sm: 0 2px 4px rgba(0, 0, 0, 0.08)
--shadow-md: 0 4px 8px rgba(0, 0, 0, 0.1)
--shadow-lg: 0 8px 16px rgba(0, 0, 0, 0.12)
--shadow-xl: 0 12px 24px rgba(0, 0, 0, 0.15)
```

## Border Radius System

Consistent rounded corners:

```css
--radius-sm: 0.25rem   /* 4px */
--radius-md: 0.5rem    /* 8px */
--radius-lg: 0.75rem   /* 12px */
--radius-xl: 1rem      /* 16px */
--radius-full: 9999px  /* Fully rounded */
```

## Best Practices

1. **Consistency**: Use the provided components and CSS classes for consistent styling
2. **Accessibility**: All components meet WCAG 2.1 AA contrast requirements
3. **Performance**: Components use CSS transforms and opacity for smooth animations
4. **Responsiveness**: All components work on mobile, tablet, and desktop
5. **Hierarchy**: Use larger components (hero, cards) before smaller ones (badges)

## Example: Complete Property Listing Page

```python
import streamlit as st
from utils import (
    load_and_inject_styles,
    display_hero_section,
    display_stats_row,
    display_gold_divider,
    display_property_grid
)

# Load styles
load_and_inject_styles()

# Hero section
display_hero_section(
    title="Warsaw Properties",
    subtitle="Discover your perfect home in Poland's capital"
)

# Statistics
display_stats_row([
    {"value": "234", "label": "Properties"},
    {"value": "$485K", "label": "Avg Price"},
    {"value": "95%", "label": "Satisfaction"}
])

# Divider
display_gold_divider()

# Property grid
display_property_grid(properties, max_display=9)
```

## Support

For issues or questions about the UI components, please refer to:
- `assets/css/dark_mode.css` - Full CSS implementation
- `utils/property_display.py` - Component implementation
- `utils/ui_helpers.py` - Helper functions

---

**Note**: Despite the filename `dark_mode.css`, this file now contains **only the modern light theme**. The dark theme has been removed as requested.
