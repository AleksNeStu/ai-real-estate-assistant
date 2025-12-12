"""
Radar charts for multi-dimensional property comparisons.

Provides interactive radar (spider) charts to visualize and compare
properties across multiple dimensions simultaneously.
"""

from typing import List, Optional, Dict
import plotly.graph_objects as go
from data.schemas import Property


# Color palette for multi-property comparison
COMPARISON_COLORS = [
    '#1f77b4',  # Blue
    '#ff7f0e',  # Orange
    '#2ca02c',  # Green
    '#d62728',  # Red
    '#9467bd',  # Purple
    '#8c564b',  # Brown
]


def create_property_radar_chart(
    properties: List[Property],
    dimensions: Optional[List[str]] = None,
    title: str = "Property Comparison"
) -> go.Figure:
    """
    Create a radar chart comparing multiple properties.

    Args:
        properties: List of 2-6 Property objects to compare
        dimensions: List of dimensions to compare (default: all available)
        title: Chart title

    Returns:
        Plotly Figure object

    Raises:
        ValueError: If fewer than 2 or more than 6 properties provided
    """
    if len(properties) < 2:
        raise ValueError("At least 2 properties required for comparison")
    if len(properties) > 6:
        raise ValueError("Maximum 6 properties can be compared at once")

    # Default dimensions
    if dimensions is None:
        dimensions = ['price', 'rooms', 'area', 'amenities', 'location']

    # Prepare data for each property
    property_data = []
    for prop in properties:
        data = _extract_property_dimensions(prop, dimensions)
        property_data.append(data)

    # Normalize values to 0-1 scale for fair comparison
    normalized_data = _normalize_dimensions(property_data, dimensions)

    # Create radar chart
    fig = go.Figure()

    for i, (prop, norm_values) in enumerate(zip(properties, normalized_data)):
        # Property label
        label = f"{prop.city} - ${prop.price}"

        # Add trace for this property
        fig.add_trace(go.Scatterpolar(
            r=norm_values + [norm_values[0]],  # Close the polygon
            theta=dimensions + [dimensions[0]],  # Close the polygon
            fill='toself',
            name=label,
            line_color=COMPARISON_COLORS[i % len(COMPARISON_COLORS)],
            opacity=0.6,
            hovertemplate='<b>%{fullData.name}</b><br>%{theta}: %{customdata}<extra></extra>',
            customdata=property_data[i] + [property_data[i][0]]  # Original values for hover
        ))

    # Update layout
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                showticklabels=False
            )
        ),
        showlegend=True,
        title=title,
        template='plotly_white',
        height=500
    )

    return fig


def create_amenity_radar_chart(
    properties: List[Property],
    title: str = "Amenity Comparison"
) -> go.Figure:
    """
    Create a radar chart specifically for amenity comparison.

    Args:
        properties: List of Property objects
        title: Chart title

    Returns:
        Plotly Figure object
    """
    if len(properties) < 2 or len(properties) > 6:
        raise ValueError("Need 2-6 properties for comparison")

    # Amenity dimensions
    amenities = ['parking', 'garden', 'pool', 'furnished', 'balcony', 'elevator']

    fig = go.Figure()

    for i, prop in enumerate(properties):
        # Extract amenity values (1 if has, 0 if not)
        values = [
            1 if prop.has_parking else 0,
            1 if prop.has_garden else 0,
            1 if prop.has_pool else 0,
            1 if prop.is_furnished else 0,
            1 if prop.has_balcony else 0,
            1 if prop.has_elevator else 0,
        ]

        label = f"{prop.city} - ${prop.price}"

        # Add trace
        fig.add_trace(go.Scatterpolar(
            r=values + [values[0]],
            theta=amenities + [amenities[0]],
            fill='toself',
            name=label,
            line_color=COMPARISON_COLORS[i % len(COMPARISON_COLORS)],
            opacity=0.5
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                tickvals=[0, 1],
                ticktext=['No', 'Yes']
            )
        ),
        showlegend=True,
        title=title,
        template='plotly_white',
        height=500
    )

    return fig


def create_value_radar_chart(
    properties: List[Property],
    weights: Optional[Dict[str, float]] = None,
    title: str = "Value Assessment Radar"
) -> go.Figure:
    """
    Create a radar chart showing value factors with weighted scoring.

    Args:
        properties: List of Property objects
        weights: Optional weights for each dimension (default: equal weights)
        title: Chart title

    Returns:
        Plotly Figure object
    """
    if len(properties) < 2 or len(properties) > 6:
        raise ValueError("Need 2-6 properties for comparison")

    # Default weights (equal)
    if weights is None:
        weights = {
            'price_value': 1.0,
            'space': 1.0,
            'amenities': 1.0,
            'condition': 1.0
        }

    dimensions = list(weights.keys())

    # Extract and normalize data
    property_data = []
    for prop in properties:
        data = {
            'price_value': _calculate_price_value_score(prop),
            'space': _calculate_space_score(prop),
            'amenities': _calculate_amenity_score(prop),
            'condition': 0.8  # Placeholder - would need actual condition data
        }
        property_data.append([data[d] for d in dimensions])

    # Create chart
    fig = go.Figure()

    for i, (prop, values) in enumerate(zip(properties, property_data)):
        # Apply weights
        weighted_values = [v * weights[d] for v, d in zip(values, dimensions)]

        # Normalize to 0-1
        max_weight = max(weights.values())
        weighted_values = [v / max_weight for v in weighted_values]

        label = f"{prop.city} - ${prop.price}"

        fig.add_trace(go.Scatterpolar(
            r=weighted_values + [weighted_values[0]],
            theta=dimensions + [dimensions[0]],
            fill='toself',
            name=label,
            line_color=COMPARISON_COLORS[i % len(COMPARISON_COLORS)],
            opacity=0.6
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )
        ),
        showlegend=True,
        title=title,
        template='plotly_white',
        height=500
    )

    return fig


def _extract_property_dimensions(prop: Property, dimensions: List[str]) -> List[float]:
    """Extract dimension values from a property."""
    values = []

    for dim in dimensions:
        if dim == 'price':
            values.append(prop.price)
        elif dim == 'rooms':
            values.append(prop.rooms)
        elif dim == 'area':
            values.append(prop.area_sqm if prop.area_sqm else 0)
        elif dim == 'amenities':
            # Count amenities
            count = sum([
                prop.has_parking,
                prop.has_garden,
                prop.has_pool,
                prop.is_furnished,
                prop.has_balcony,
                prop.has_elevator
            ])
            values.append(count)
        elif dim == 'location':
            # Placeholder location score (would need actual location data)
            values.append(0.7)
        elif dim == 'bathrooms':
            values.append(prop.bathrooms)
        else:
            values.append(0)

    return values


def _normalize_dimensions(
    property_data: List[List[float]],
    dimensions: List[str]
) -> List[List[float]]:
    """Normalize all property data to 0-1 scale for each dimension."""
    num_properties = len(property_data)
    num_dimensions = len(dimensions)

    # Transpose to get values by dimension
    dimension_values = [[property_data[i][j] for i in range(num_properties)]
                        for j in range(num_dimensions)]

    # Normalize each dimension
    normalized = []
    for prop_idx in range(num_properties):
        prop_normalized = []
        for dim_idx, dim_name in enumerate(dimensions):
            values = dimension_values[dim_idx]
            min_val = min(values)
            max_val = max(values)

            current_val = property_data[prop_idx][dim_idx]

            # Normalize based on dimension type
            if dim_name == 'price':
                # For price, lower is better, so invert
                if max_val != min_val:
                    norm_val = 1 - (current_val - min_val) / (max_val - min_val)
                else:
                    norm_val = 1.0
            else:
                # For other dimensions, higher is better
                if max_val != min_val:
                    norm_val = (current_val - min_val) / (max_val - min_val)
                else:
                    norm_val = 1.0

            prop_normalized.append(norm_val)

        normalized.append(prop_normalized)

    return normalized


def _calculate_price_value_score(prop: Property) -> float:
    """Calculate price value score (inverse of price, normalized)."""
    # Lower price = higher score
    # This is a placeholder - would be better with market comparison
    if prop.price <= 800:
        return 1.0
    elif prop.price <= 1200:
        return 0.7
    elif prop.price <= 1600:
        return 0.4
    else:
        return 0.2


def _calculate_space_score(prop: Property) -> float:
    """Calculate space score based on rooms and area."""
    room_score = min(prop.rooms / 5.0, 1.0)  # Normalize to 5 rooms max

    if prop.area_sqm:
        area_score = min(prop.area_sqm / 100.0, 1.0)  # Normalize to 100 sqm max
        return (room_score + area_score) / 2
    else:
        return room_score


def _calculate_amenity_score(prop: Property) -> float:
    """Calculate amenity score as percentage of available amenities."""
    total_amenities = 6  # Total possible amenities
    has_amenities = sum([
        prop.has_parking,
        prop.has_garden,
        prop.has_pool,
        prop.is_furnished,
        prop.has_balcony,
        prop.has_elevator
    ])

    return has_amenities / total_amenities
