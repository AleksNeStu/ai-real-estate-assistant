"""
Geographic visualizations for property locations and price distributions.

Provides interactive maps using Folium with:
- Property location markers
- Price-based color coding
- Cluster groups for high-density areas
- Popup details for each property
- Price heatmaps
- Location filtering
"""

from typing import List, Optional, Tuple, Dict, Any
import folium
from folium import plugins
from data.schemas import Property, PropertyCollection
import pandas as pd


# Default map center (Poland)
DEFAULT_CENTER = [52.0, 19.0]
DEFAULT_ZOOM = 6

# City coordinates (approximate centers)
CITY_COORDINATES = {
    'warsaw': [52.2297, 21.0122],
    'krakow': [50.0647, 19.9450],
    'wroclaw': [51.1079, 17.0385],
    'poznan': [52.4064, 16.9252],
    'gdansk': [54.3520, 18.6466],
    'szczecin': [53.4285, 14.5528],
    'lublin': [51.2465, 22.5684],
    'katowice': [50.2649, 19.0238],
    'bydgoszcz': [53.1235, 18.0084],
    'lodz': [51.7592, 19.4560]
}

# Price range colors
PRICE_COLORS = {
    'low': '#2ca02c',          # Green (< $800)
    'medium': '#ffbb00',       # Yellow ($800-$1200)
    'high': '#ff7f0e',         # Orange ($1200-$1600)
    'very_high': '#d62728'     # Red (> $1600)
}


def _get_price_color(price: float) -> str:
    """Get color based on price range."""
    if price < 800:
        return PRICE_COLORS['low']
    elif price < 1200:
        return PRICE_COLORS['medium']
    elif price < 1600:
        return PRICE_COLORS['high']
    else:
        return PRICE_COLORS['very_high']


def _get_city_coordinates(city: str) -> Tuple[float, float]:
    """
    Get coordinates for a city.

    Args:
        city: City name

    Returns:
        Tuple of (latitude, longitude)
    """
    city_lower = city.lower().strip()

    if city_lower in CITY_COORDINATES:
        return CITY_COORDINATES[city_lower]

    # Default to Poland center if city not found
    return DEFAULT_CENTER


def create_property_map(
    properties: PropertyCollection,
    center_city: Optional[str] = None,
    zoom_start: int = 7,
    add_clusters: bool = True,
    show_legend: bool = True
) -> folium.Map:
    """
    Create an interactive map with property markers.

    Args:
        properties: Collection of properties
        center_city: Optional city to center the map on
        zoom_start: Initial zoom level
        add_clusters: Whether to cluster nearby markers
        show_legend: Whether to show price range legend

    Returns:
        Folium Map object
    """
    # Determine map center
    if center_city:
        center = _get_city_coordinates(center_city)
    else:
        # Calculate center from all properties
        cities = list(set(p.city for p in properties.properties))
        if cities:
            coords = [_get_city_coordinates(city) for city in cities]
            center = [
                sum(lat for lat, _ in coords) / len(coords),
                sum(lon for _, lon in coords) / len(coords)
            ]
        else:
            center = DEFAULT_CENTER

    # Create base map
    m = folium.Map(
        location=center,
        zoom_start=zoom_start,
        tiles='OpenStreetMap'
    )

    # Create marker cluster if requested
    if add_clusters:
        marker_cluster = plugins.MarkerCluster(name="Properties").add_to(m)
        marker_group = marker_cluster
    else:
        marker_group = m

    # Add markers for each property
    for prop in properties.properties:
        coords = _get_city_coordinates(prop.city)

        # Add small random offset to prevent exact overlaps
        import random
        coords = [
            coords[0] + random.uniform(-0.01, 0.01),
            coords[1] + random.uniform(-0.01, 0.01)
        ]

        # Create popup content
        popup_html = _create_property_popup(prop)

        # Get marker color based on price
        color = _get_price_color(prop.price)

        # Create marker
        folium.CircleMarker(
            location=coords,
            radius=8,
            popup=folium.Popup(popup_html, max_width=300),
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.7,
            weight=2
        ).add_to(marker_group)

    # Add legend
    if show_legend:
        legend_html = _create_legend_html()
        m.get_root().html.add_child(folium.Element(legend_html))

    # Add layer control
    folium.LayerControl().add_to(m)

    return m


def create_price_heatmap(
    properties: PropertyCollection,
    center_city: Optional[str] = None,
    zoom_start: int = 7,
    radius: int = 15,
    blur: int = 25
) -> folium.Map:
    """
    Create a heatmap showing price distribution.

    Args:
        properties: Collection of properties
        center_city: Optional city to center the map on
        zoom_start: Initial zoom level
        radius: Heatmap point radius
        blur: Heatmap blur amount

    Returns:
        Folium Map object with heatmap
    """
    # Determine map center
    if center_city:
        center = _get_city_coordinates(center_city)
    else:
        cities = list(set(p.city for p in properties.properties))
        if cities:
            coords = [_get_city_coordinates(city) for city in cities]
            center = [
                sum(lat for lat, _ in coords) / len(coords),
                sum(lon for _, lon in coords) / len(coords)
            ]
        else:
            center = DEFAULT_CENTER

    # Create base map
    m = folium.Map(
        location=center,
        zoom_start=zoom_start,
        tiles='OpenStreetMap'
    )

    # Prepare heatmap data
    heat_data = []
    for prop in properties.properties:
        coords = _get_city_coordinates(prop.city)

        # Add small random offset
        import random
        coords = [
            coords[0] + random.uniform(-0.01, 0.01),
            coords[1] + random.uniform(-0.01, 0.01)
        ]

        # Weight by price (normalized)
        weight = prop.price / 2000  # Normalize to reasonable range

        heat_data.append([coords[0], coords[1], weight])

    # Add heatmap layer
    if heat_data:
        plugins.HeatMap(
            heat_data,
            radius=radius,
            blur=blur,
            max_zoom=13,
            name='Price Heatmap'
        ).add_to(m)

    # Add layer control
    folium.LayerControl().add_to(m)

    return m


def create_city_overview_map(
    properties: PropertyCollection,
    show_statistics: bool = True
) -> folium.Map:
    """
    Create a map with city markers showing aggregate statistics.

    Args:
        properties: Collection of properties
        show_statistics: Whether to show statistics in popups

    Returns:
        Folium Map object
    """
    # Calculate statistics by city
    df = pd.DataFrame([{
        'city': p.city,
        'price': p.price,
        'rooms': p.rooms
    } for p in properties.properties])

    city_stats = df.groupby('city').agg({
        'price': ['mean', 'median', 'count'],
        'rooms': 'mean'
    }).reset_index()

    city_stats.columns = ['city', 'avg_price', 'median_price', 'count', 'avg_rooms']

    # Calculate center
    if len(city_stats) > 0:
        coords = [_get_city_coordinates(city) for city in city_stats['city']]
        center = [
            sum(lat for lat, _ in coords) / len(coords),
            sum(lon for _, lon in coords) / len(coords)
        ]
    else:
        center = DEFAULT_CENTER

    # Create map
    m = folium.Map(
        location=center,
        zoom_start=6,
        tiles='OpenStreetMap'
    )

    # Add markers for each city
    for _, row in city_stats.iterrows():
        coords = _get_city_coordinates(row['city'])

        # Create popup content
        popup_html = f"""
        <div style="font-family: Arial; width: 200px;">
            <h4 style="margin: 0 0 10px 0;">{row['city']}</h4>
            <table style="width: 100%; font-size: 12px;">
                <tr>
                    <td><b>Properties:</b></td>
                    <td>{int(row['count'])}</td>
                </tr>
                <tr>
                    <td><b>Avg Price:</b></td>
                    <td>${row['avg_price']:.0f}</td>
                </tr>
                <tr>
                    <td><b>Median Price:</b></td>
                    <td>${row['median_price']:.0f}</td>
                </tr>
                <tr>
                    <td><b>Avg Rooms:</b></td>
                    <td>{row['avg_rooms']:.1f}</td>
                </tr>
            </table>
        </div>
        """

        # Size based on count
        radius = min(10 + (row['count'] / 2), 30)

        # Color based on average price
        color = _get_price_color(row['avg_price'])

        # Create marker
        folium.CircleMarker(
            location=coords,
            radius=radius,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"{row['city']}: {int(row['count'])} properties",
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.6,
            weight=3
        ).add_to(m)

    return m


def _create_property_popup(prop: Property) -> str:
    """Create HTML content for property popup."""
    # Amenities list
    amenities = []
    if prop.has_parking:
        amenities.append("🚗 Parking")
    if prop.has_garden:
        amenities.append("🌳 Garden")
    if prop.has_pool:
        amenities.append("🏊 Pool")
    if prop.is_furnished:
        amenities.append("🛋️ Furnished")
    if prop.has_balcony:
        amenities.append("🏖️ Balcony")
    if prop.has_elevator:
        amenities.append("🛗 Elevator")

    amenities_html = "<br>".join(amenities) if amenities else "None"

    html = f"""
    <div style="font-family: Arial; width: 250px;">
        <h4 style="margin: 0 0 10px 0; color: #1f77b4;">{prop.city}</h4>
        <table style="width: 100%; font-size: 12px;">
            <tr>
                <td><b>Price:</b></td>
                <td style="color: #d62728; font-weight: bold;">${prop.price}/month</td>
            </tr>
            <tr>
                <td><b>Type:</b></td>
                <td>{prop.property_type}</td>
            </tr>
            <tr>
                <td><b>Rooms:</b></td>
                <td>{prop.rooms} bed, {prop.bathrooms} bath</td>
            </tr>
            {f'<tr><td><b>Area:</b></td><td>{prop.area_sqm} sqm</td></tr>' if prop.area_sqm else ''}
            {f'<tr><td><b>Price/sqm:</b></td><td>${(prop.price/prop.area_sqm):.2f}</td></tr>' if prop.area_sqm else ''}
        </table>
        <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #ccc;">
            <b>Amenities:</b><br>
            <div style="margin-top: 5px; font-size: 11px;">
                {amenities_html}
            </div>
        </div>
    </div>
    """

    return html


def _create_legend_html() -> str:
    """Create HTML for price range legend."""
    html = """
    <div style="
        position: fixed;
        bottom: 50px;
        left: 50px;
        width: 180px;
        background-color: white;
        border: 2px solid #ccc;
        border-radius: 5px;
        padding: 10px;
        font-family: Arial;
        font-size: 12px;
        z-index: 1000;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    ">
        <h4 style="margin: 0 0 10px 0; font-size: 14px;">Price Range</h4>
        <div style="margin-bottom: 5px;">
            <span style="display: inline-block; width: 15px; height: 15px; background-color: #2ca02c; margin-right: 5px; border-radius: 50%;"></span>
            < $800/mo
        </div>
        <div style="margin-bottom: 5px;">
            <span style="display: inline-block; width: 15px; height: 15px; background-color: #ffbb00; margin-right: 5px; border-radius: 50%;"></span>
            $800-$1200/mo
        </div>
        <div style="margin-bottom: 5px;">
            <span style="display: inline-block; width: 15px; height: 15px; background-color: #ff7f0e; margin-right: 5px; border-radius: 50%;"></span>
            $1200-$1600/mo
        </div>
        <div>
            <span style="display: inline-block; width: 15px; height: 15px; background-color: #d62728; margin-right: 5px; border-radius: 50%;"></span>
            > $1600/mo
        </div>
    </div>
    """

    return html


def create_location_comparison_map(
    properties: PropertyCollection,
    city1: str,
    city2: str
) -> folium.Map:
    """
    Create a map comparing two cities.

    Args:
        properties: Collection of properties
        city1: First city
        city2: Second city

    Returns:
        Folium Map object
    """
    # Filter properties
    city1_props = [p for p in properties.properties if p.city.lower() == city1.lower()]
    city2_props = [p for p in properties.properties if p.city.lower() == city2.lower()]

    # Get coordinates
    coords1 = _get_city_coordinates(city1)
    coords2 = _get_city_coordinates(city2)

    # Calculate center between the two cities
    center = [
        (coords1[0] + coords2[0]) / 2,
        (coords1[1] + coords2[1]) / 2
    ]

    # Create map
    m = folium.Map(
        location=center,
        zoom_start=7,
        tiles='OpenStreetMap'
    )

    # Add feature groups for each city
    fg1 = folium.FeatureGroup(name=city1).add_to(m)
    fg2 = folium.FeatureGroup(name=city2).add_to(m)

    # Add markers for city 1
    for prop in city1_props:
        coords = _get_city_coordinates(prop.city)
        import random
        coords = [
            coords[0] + random.uniform(-0.01, 0.01),
            coords[1] + random.uniform(-0.01, 0.01)
        ]

        popup_html = _create_property_popup(prop)

        folium.CircleMarker(
            location=coords,
            radius=7,
            popup=folium.Popup(popup_html, max_width=300),
            color='#1f77b4',
            fill=True,
            fillColor='#1f77b4',
            fillOpacity=0.6,
            weight=2
        ).add_to(fg1)

    # Add markers for city 2
    for prop in city2_props:
        coords = _get_city_coordinates(prop.city)
        import random
        coords = [
            coords[0] + random.uniform(-0.01, 0.01),
            coords[1] + random.uniform(-0.01, 0.01)
        ]

        popup_html = _create_property_popup(prop)

        folium.CircleMarker(
            location=coords,
            radius=7,
            popup=folium.Popup(popup_html, max_width=300),
            color='#ff7f0e',
            fill=True,
            fillColor='#ff7f0e',
            fillOpacity=0.6,
            weight=2
        ).add_to(fg2)

    # Add layer control
    folium.LayerControl().add_to(m)

    return m
