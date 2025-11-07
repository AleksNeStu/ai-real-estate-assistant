"""
Reusable metric card components for dashboards.

Provides styled metric displays with:
- KPI cards with icons and values
- Delta indicators (up/down percentage changes)
- Color-coded values
- Responsive layouts
"""

from typing import Optional, List, Dict, Any, Literal
import streamlit as st


def display_metric_card(
    title: str,
    value: Any,
    delta: Optional[str] = None,
    delta_color: Literal["normal", "inverse", "off"] = "normal",
    help_text: Optional[str] = None,
    icon: Optional[str] = None
):
    """
    Display a single metric card.

    Args:
        title: Metric title/label
        value: Metric value (will be formatted)
        delta: Optional delta/change indicator (e.g., "+5.2%", "-3 properties")
        delta_color: Color scheme for delta ("normal", "inverse", "off")
        help_text: Optional help text (shows on hover)
        icon: Optional emoji icon to display
    """
    # Format title with icon
    display_title = f"{icon} {title}" if icon else title

    # Display metric using Streamlit's native component
    st.metric(
        label=display_title,
        value=value,
        delta=delta,
        delta_color=delta_color,
        help=help_text
    )


def display_metrics_row(
    metrics: List[Dict[str, Any]],
    columns: Optional[int] = None
):
    """
    Display a row of metrics.

    Args:
        metrics: List of metric dictionaries with keys:
                 - title: str
                 - value: Any
                 - delta: Optional[str]
                 - delta_color: Optional[str]
                 - help_text: Optional[str]
                 - icon: Optional[str]
        columns: Number of columns (default: len(metrics))
    """
    if not metrics:
        return

    # Create columns
    num_cols = columns if columns else len(metrics)
    cols = st.columns(num_cols)

    # Display metrics
    for i, metric in enumerate(metrics):
        col_idx = i % num_cols
        with cols[col_idx]:
            display_metric_card(
                title=metric.get('title', 'Metric'),
                value=metric.get('value', 0),
                delta=metric.get('delta'),
                delta_color=metric.get('delta_color', 'normal'),
                help_text=metric.get('help_text'),
                icon=metric.get('icon')
            )


def display_kpi_grid(
    kpis: Dict[str, Dict[str, Any]],
    columns: int = 4
):
    """
    Display a grid of KPIs (Key Performance Indicators).

    Args:
        kpis: Dictionary of KPIs where key is the KPI name and value is a dict with:
              - value: The KPI value
              - delta: Optional change indicator
              - icon: Optional emoji icon
              - help: Optional help text
        columns: Number of columns in the grid
    """
    if not kpis:
        st.info("No KPIs to display")
        return

    # Convert dict to list of metrics
    metrics = []
    for key, data in kpis.items():
        metrics.append({
            'title': key,
            'value': data.get('value', 0),
            'delta': data.get('delta'),
            'delta_color': data.get('delta_color', 'normal'),
            'help_text': data.get('help'),
            'icon': data.get('icon')
        })

    # Display in rows
    for i in range(0, len(metrics), columns):
        row_metrics = metrics[i:i+columns]
        display_metrics_row(row_metrics, columns=columns)


def display_stat_box(
    title: str,
    value: Any,
    subtitle: Optional[str] = None,
    icon: Optional[str] = None,
    color: str = "#1f77b4"
):
    """
    Display a colored stat box with custom styling.

    Args:
        title: Box title
        value: Main value to display
        subtitle: Optional subtitle/description
        icon: Optional emoji icon
        color: Background color (hex code)
    """
    # Create styled HTML
    icon_html = f"<span style='font-size: 2em;'>{icon}</span>" if icon else ""

    html = f"""
    <div style='
        background-color: {color}15;
        border-left: 4px solid {color};
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    '>
        {icon_html}
        <div style='margin-top: 0.5rem;'>
            <div style='font-size: 0.875rem; color: #666; font-weight: 500;'>
                {title}
            </div>
            <div style='font-size: 2rem; font-weight: 700; color: #222; margin-top: 0.25rem;'>
                {value}
            </div>
            {f"<div style='font-size: 0.875rem; color: #666; margin-top: 0.25rem;'>{subtitle}</div>" if subtitle else ""}
        </div>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)


def display_progress_metric(
    title: str,
    current: float,
    target: float,
    unit: str = "",
    show_percentage: bool = True
):
    """
    Display a metric with a progress bar.

    Args:
        title: Metric title
        current: Current value
        target: Target/goal value
        unit: Unit to display (e.g., "$", "properties")
        show_percentage: Whether to show percentage completion
    """
    # Calculate percentage
    percentage = (current / target * 100) if target > 0 else 0
    percentage = min(percentage, 100)  # Cap at 100%

    # Display title and values
    st.markdown(f"**{title}**")

    col1, col2 = st.columns([3, 1])

    with col1:
        # Progress bar
        st.progress(percentage / 100)

    with col2:
        # Values
        if show_percentage:
            st.markdown(f"**{percentage:.1f}%**")
        else:
            st.markdown(f"**{current:,.0f} / {target:,.0f}** {unit}")


def display_comparison_metrics(
    metric_pairs: List[tuple[str, Any, Any]],
    labels: tuple[str, str] = ("Before", "After")
):
    """
    Display side-by-side comparison metrics.

    Args:
        metric_pairs: List of tuples (metric_name, value1, value2)
        labels: Labels for the two columns
    """
    # Create header
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.markdown("**Metric**")
    with col2:
        st.markdown(f"**{labels[0]}**")
    with col3:
        st.markdown(f"**{labels[1]}**")

    st.divider()

    # Display metrics
    for metric_name, value1, value2 in metric_pairs:
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            st.markdown(metric_name)
        with col2:
            st.markdown(f"{value1}")
        with col3:
            # Calculate change
            try:
                change = ((value2 - value1) / value1 * 100) if value1 != 0 else 0
                color = "🟢" if change > 0 else "🔴" if change < 0 else "⚪"
                st.markdown(f"{value2} {color}")
            except (TypeError, ValueError):
                st.markdown(f"{value2}")


def display_metric_summary(
    title: str,
    metrics: Dict[str, Any],
    columns: int = 2
):
    """
    Display a summary card with multiple metrics.

    Args:
        title: Summary title
        metrics: Dictionary of metric_name: value pairs
        columns: Number of columns for layout
    """
    st.subheader(title)

    # Create grid layout
    metric_items = list(metrics.items())

    for i in range(0, len(metric_items), columns):
        cols = st.columns(columns)
        for j, col in enumerate(cols):
            idx = i + j
            if idx < len(metric_items):
                metric_name, metric_value = metric_items[idx]
                with col:
                    st.markdown(f"**{metric_name}**")
                    st.markdown(f"<h3 style='margin: 0;'>{metric_value}</h3>", unsafe_allow_html=True)


def format_number(value: float, format_type: str = "default") -> str:
    """
    Format a number for display.

    Args:
        value: Number to format
        format_type: Format type - "default", "currency", "percentage", "compact"

    Returns:
        Formatted string
    """
    if format_type == "currency":
        return f"${value:,.2f}"
    elif format_type == "percentage":
        return f"{value:.1f}%"
    elif format_type == "compact":
        # Compact notation (K, M, B)
        if abs(value) >= 1_000_000_000:
            return f"{value / 1_000_000_000:.1f}B"
        elif abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.1f}M"
        elif abs(value) >= 1_000:
            return f"{value / 1_000:.1f}K"
        else:
            return f"{value:.0f}"
    else:  # default
        return f"{value:,.0f}"


def format_delta(old_value: float, new_value: float, format_type: str = "percentage") -> str:
    """
    Calculate and format delta between two values.

    Args:
        old_value: Previous value
        new_value: Current value
        format_type: Format type - "percentage", "absolute", "both"

    Returns:
        Formatted delta string with +/- prefix
    """
    if old_value == 0:
        return "+∞" if new_value > 0 else "0"

    abs_change = new_value - old_value
    pct_change = (abs_change / old_value) * 100

    if format_type == "percentage":
        return f"{pct_change:+.1f}%"
    elif format_type == "absolute":
        return f"{abs_change:+,.0f}"
    else:  # both
        return f"{abs_change:+,.0f} ({pct_change:+.1f}%)"
