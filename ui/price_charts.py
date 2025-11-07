"""
Interactive price visualization charts using Plotly.

Provides various chart types for analyzing property prices:
- Price distribution histograms
- Price trend line charts
- Price by location comparisons
- Price vs amenities scatter plots
- Price per square meter analysis
"""

from typing import List, Optional, Dict, Any
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from data.schemas import Property, PropertyCollection


# Color palette
COLORS = {
    'primary': '#1f77b4',      # Blue
    'secondary': '#ff7f0e',    # Orange
    'success': '#2ca02c',      # Green
    'warning': '#ffbb00',      # Yellow
    'danger': '#d62728',       # Red
    'info': '#17becf',         # Cyan
    'neutral': '#7f7f7f'       # Gray
}

PRICE_RANGE_COLORS = {
    'low': '#2ca02c',          # Green ($0-$800)
    'medium': '#ffbb00',       # Yellow ($800-$1200)
    'high': '#ff7f0e',         # Orange ($1200-$1600)
    'very_high': '#d62728'     # Red ($1600+)
}


def _properties_to_dataframe(properties: PropertyCollection) -> pd.DataFrame:
    """Convert PropertyCollection to pandas DataFrame."""
    data = []
    for prop in properties.properties:
        data.append({
            'city': prop.city,
            'price': prop.price,
            'rooms': prop.rooms,
            'bathrooms': prop.bathrooms,
            'area_sqm': prop.area_sqm,
            'property_type': prop.property_type.value if hasattr(prop.property_type, 'value') else str(prop.property_type),
            'has_parking': prop.has_parking,
            'has_garden': prop.has_garden,
            'has_pool': prop.has_pool,
            'is_furnished': prop.is_furnished,
            'has_balcony': prop.has_balcony,
            'has_elevator': prop.has_elevator,
        })
    return pd.DataFrame(data)


def _get_price_range_color(price: float) -> str:
    """Get color based on price range."""
    if price < 800:
        return PRICE_RANGE_COLORS['low']
    elif price < 1200:
        return PRICE_RANGE_COLORS['medium']
    elif price < 1600:
        return PRICE_RANGE_COLORS['high']
    else:
        return PRICE_RANGE_COLORS['very_high']


def create_price_distribution_chart(
    properties: PropertyCollection,
    bins: int = 20,
    show_stats: bool = True,
    title: str = "Price Distribution"
) -> go.Figure:
    """
    Create an interactive price distribution histogram.

    Args:
        properties: Collection of properties
        bins: Number of bins for histogram
        show_stats: Whether to show mean/median lines
        title: Chart title

    Returns:
        Plotly Figure object
    """
    df = _properties_to_dataframe(properties)

    if len(df) == 0:
        # Empty state
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=20, color=COLORS['neutral'])
        )
        return fig

    # Create histogram
    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=df['price'],
        nbinsx=bins,
        name='Properties',
        marker_color=COLORS['primary'],
        opacity=0.7,
        hovertemplate='<b>Price Range:</b> $%{x}<br><b>Count:</b> %{y}<extra></extra>'
    ))

    if show_stats and len(df) > 0:
        mean_price = df['price'].mean()
        median_price = df['price'].median()

        # Add mean line
        fig.add_vline(
            x=mean_price,
            line_dash="dash",
            line_color=COLORS['danger'],
            annotation_text=f"Mean: ${mean_price:.0f}",
            annotation_position="top"
        )

        # Add median line
        fig.add_vline(
            x=median_price,
            line_dash="dot",
            line_color=COLORS['success'],
            annotation_text=f"Median: ${median_price:.0f}",
            annotation_position="top"
        )

    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title="Price ($/month)",
        yaxis_title="Number of Properties",
        hovermode='x unified',
        template='plotly_white',
        showlegend=False,
        height=400
    )

    return fig


def create_price_by_location_chart(
    properties: PropertyCollection,
    sort_by: str = "median",  # 'median', 'mean', 'count'
    orientation: str = "v",    # 'v' for vertical, 'h' for horizontal
    title: str = "Price by Location"
) -> go.Figure:
    """
    Create a bar chart comparing prices across locations.

    Args:
        properties: Collection of properties
        sort_by: Sort criterion ('median', 'mean', 'count')
        orientation: Bar orientation ('v' or 'h')
        title: Chart title

    Returns:
        Plotly Figure object
    """
    df = _properties_to_dataframe(properties)

    if len(df) == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=20, color=COLORS['neutral'])
        )
        return fig

    # Calculate statistics by city
    city_stats = df.groupby('city').agg({
        'price': ['mean', 'median', 'count', 'min', 'max']
    }).reset_index()
    city_stats.columns = ['city', 'mean', 'median', 'count', 'min', 'max']

    # Sort
    if sort_by == 'median':
        city_stats = city_stats.sort_values('median', ascending=True)
    elif sort_by == 'mean':
        city_stats = city_stats.sort_values('mean', ascending=True)
    else:  # count
        city_stats = city_stats.sort_values('count', ascending=True)

    # Create bar chart
    if orientation == 'h':
        fig = go.Figure(go.Bar(
            y=city_stats['city'],
            x=city_stats['median'],
            orientation='h',
            marker_color=COLORS['primary'],
            text=[f"${v:.0f}" for v in city_stats['median']],
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>Median: $%{x:.0f}<br>Count: %{customdata[0]}<extra></extra>',
            customdata=city_stats[['count']].values
        ))
        fig.update_layout(
            xaxis_title="Median Price ($/month)",
            yaxis_title="City"
        )
    else:
        fig = go.Figure(go.Bar(
            x=city_stats['city'],
            y=city_stats['median'],
            marker_color=[_get_price_range_color(p) for p in city_stats['median']],
            text=[f"${v:.0f}" for v in city_stats['median']],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Median: $%{y:.0f}<br>Count: %{customdata[0]}<extra></extra>',
            customdata=city_stats[['count']].values
        ))
        fig.update_layout(
            xaxis_title="City",
            yaxis_title="Median Price ($/month)"
        )

    fig.update_layout(
        title=title,
        template='plotly_white',
        showlegend=False,
        height=400
    )

    return fig


def create_price_amenity_scatter(
    properties: PropertyCollection,
    title: str = "Price vs Amenities"
) -> go.Figure:
    """
    Create a scatter plot of price vs number of amenities.

    Args:
        properties: Collection of properties
        title: Chart title

    Returns:
        Plotly Figure object
    """
    df = _properties_to_dataframe(properties)

    if len(df) == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=20, color=COLORS['neutral'])
        )
        return fig

    # Count amenities
    amenity_cols = ['has_parking', 'has_garden', 'has_pool', 'is_furnished', 'has_balcony', 'has_elevator']
    df['amenity_count'] = df[amenity_cols].sum(axis=1)

    # Create scatter plot
    fig = px.scatter(
        df,
        x='amenity_count',
        y='price',
        color='city',
        size='rooms',
        hover_data=['city', 'rooms', 'property_type'],
        title=title,
        labels={
            'amenity_count': 'Number of Amenities',
            'price': 'Price ($/month)',
            'city': 'City',
            'rooms': 'Rooms'
        }
    )

    # Add trend line
    if len(df) > 1:
        z = np.polyfit(df['amenity_count'], df['price'], 1)
        p = np.poly1d(z)
        x_trend = np.linspace(df['amenity_count'].min(), df['amenity_count'].max(), 100)
        y_trend = p(x_trend)

        fig.add_trace(go.Scatter(
            x=x_trend,
            y=y_trend,
            mode='lines',
            name='Trend',
            line=dict(dash='dash', color=COLORS['neutral']),
            hoverinfo='skip'
        ))

    fig.update_layout(
        template='plotly_white',
        height=500
    )

    return fig


def create_price_per_sqm_chart(
    properties: PropertyCollection,
    title: str = "Price per Square Meter by Location"
) -> go.Figure:
    """
    Create a box plot of price per sqm by location.

    Args:
        properties: Collection of properties
        title: Chart title

    Returns:
        Plotly Figure object
    """
    df = _properties_to_dataframe(properties)

    # Filter properties with area data
    df_with_area = df[df['area_sqm'].notna()].copy()

    if len(df_with_area) == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No area data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=20, color=COLORS['neutral'])
        )
        return fig

    # Calculate price per sqm
    df_with_area['price_per_sqm'] = df_with_area['price'] / df_with_area['area_sqm']

    # Create box plot
    fig = go.Figure()

    for city in df_with_area['city'].unique():
        city_data = df_with_area[df_with_area['city'] == city]

        fig.add_trace(go.Box(
            y=city_data['price_per_sqm'],
            name=city,
            boxmean='sd',  # Show mean and standard deviation
            hovertemplate='<b>%{fullData.name}</b><br>Price/sqm: $%{y:.2f}<extra></extra>'
        ))

    fig.update_layout(
        title=title,
        yaxis_title="Price per Square Meter ($/sqm)",
        xaxis_title="City",
        template='plotly_white',
        showlegend=False,
        height=450
    )

    return fig


def create_price_trend_line_chart(
    properties: PropertyCollection,
    city: Optional[str] = None,
    title: Optional[str] = None
) -> go.Figure:
    """
    Create a line chart showing price trends.

    Note: Since properties don't have timestamps, this creates
    a sorted view by price to show distribution.

    Args:
        properties: Collection of properties
        city: Optional city filter
        title: Chart title

    Returns:
        Plotly Figure object
    """
    df = _properties_to_dataframe(properties)

    if city:
        df = df[df['city'] == city]
        if not title:
            title = f"Price Trend in {city}"
    else:
        if not title:
            title = "Overall Price Trend"

    if len(df) == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=20, color=COLORS['neutral'])
        )
        return fig

    # Sort by price and create index
    df_sorted = df.sort_values('price').reset_index(drop=True)
    df_sorted['index'] = range(len(df_sorted))

    # Calculate rolling average
    window = min(5, len(df_sorted))
    df_sorted['rolling_avg'] = df_sorted['price'].rolling(window=window, center=True).mean()

    fig = go.Figure()

    # Add individual points
    fig.add_trace(go.Scatter(
        x=df_sorted['index'],
        y=df_sorted['price'],
        mode='markers',
        name='Properties',
        marker=dict(size=6, color=COLORS['primary'], opacity=0.5),
        hovertemplate='<b>Property</b><br>Price: $%{y:.0f}<br>City: %{customdata[0]}<extra></extra>',
        customdata=df_sorted[['city']].values
    ))

    # Add rolling average line
    fig.add_trace(go.Scatter(
        x=df_sorted['index'],
        y=df_sorted['rolling_avg'],
        mode='lines',
        name='Trend (Rolling Avg)',
        line=dict(width=3, color=COLORS['danger']),
        hovertemplate='<b>Trend</b><br>Avg Price: $%{y:.0f}<extra></extra>'
    ))

    # Add quartile bands
    q1 = df_sorted['price'].quantile(0.25)
    q3 = df_sorted['price'].quantile(0.75)

    fig.add_hrect(
        y0=q1, y1=q3,
        fillcolor=COLORS['info'],
        opacity=0.1,
        line_width=0,
        annotation_text="Middle 50%",
        annotation_position="right"
    )

    fig.update_layout(
        title=title,
        xaxis_title="Property Index (sorted by price)",
        yaxis_title="Price ($/month)",
        template='plotly_white',
        hovermode='closest',
        height=450
    )

    return fig


def create_price_comparison_chart(
    properties: List[Property],
    title: str = "Property Price Comparison"
) -> go.Figure:
    """
    Create a bar chart comparing specific properties.

    Args:
        properties: List of Property objects to compare
        title: Chart title

    Returns:
        Plotly Figure object
    """
    if not properties:
        fig = go.Figure()
        fig.add_annotation(
            text="No properties to compare",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=20, color=COLORS['neutral'])
        )
        return fig

    # Extract data
    labels = [f"{p.city} - {p.property_type}" for p in properties]
    prices = [p.price for p in properties]
    colors = [_get_price_range_color(p) for p in prices]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=labels,
        y=prices,
        marker_color=colors,
        text=[f"${p:.0f}" for p in prices],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Price: $%{y:.0f}<extra></extra>'
    ))

    # Add average line
    avg_price = sum(prices) / len(prices)
    fig.add_hline(
        y=avg_price,
        line_dash="dash",
        line_color=COLORS['neutral'],
        annotation_text=f"Average: ${avg_price:.0f}",
        annotation_position="right"
    )

    fig.update_layout(
        title=title,
        xaxis_title="Property",
        yaxis_title="Price ($/month)",
        template='plotly_white',
        showlegend=False,
        height=400
    )

    return fig
