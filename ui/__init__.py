"""
UI components for enhanced visualizations.
"""

# Phase 3: Basic comparisons
from .comparison_viz import PropertyComparison, create_comparison_chart, create_price_trend_chart

# Phase 4: Advanced visualizations
from .price_charts import (
    create_price_distribution_chart,
    create_price_by_location_chart,
    create_price_amenity_scatter,
    create_price_per_sqm_chart,
    create_price_trend_line_chart,
    create_price_comparison_chart
)

from .radar_charts import (
    create_property_radar_chart,
    create_amenity_radar_chart,
    create_value_radar_chart
)

from .metrics import (
    display_metric_card,
    display_metrics_row,
    display_kpi_grid,
    display_stat_box,
    display_progress_metric,
    format_number,
    format_delta
)

from .market_dashboard import (
    display_market_dashboard,
    display_compact_dashboard,
    display_location_comparison_dashboard
)

from .geo_viz import (
    create_property_map,
    create_price_heatmap,
    create_city_overview_map,
    create_location_comparison_map
)

from .comparison_dashboard import (
    display_comparison_dashboard,
    display_compact_comparison
)

__all__ = [
    # Phase 3
    'PropertyComparison',
    'create_comparison_chart',
    'create_price_trend_chart',
    # Phase 4 - Price Charts
    'create_price_distribution_chart',
    'create_price_by_location_chart',
    'create_price_amenity_scatter',
    'create_price_per_sqm_chart',
    'create_price_trend_line_chart',
    'create_price_comparison_chart',
    # Phase 4 - Radar Charts
    'create_property_radar_chart',
    'create_amenity_radar_chart',
    'create_value_radar_chart',
    # Phase 4 - Metrics
    'display_metric_card',
    'display_metrics_row',
    'display_kpi_grid',
    'display_stat_box',
    'display_progress_metric',
    'format_number',
    'format_delta',
    # Phase 4 - Dashboards
    'display_market_dashboard',
    'display_compact_dashboard',
    'display_location_comparison_dashboard',
    'display_comparison_dashboard',
    'display_compact_comparison',
    # Phase 4 - Geographic
    'create_property_map',
    'create_price_heatmap',
    'create_city_overview_map',
    'create_location_comparison_map',
]
