# Phase 3: Advanced Features - Implementation Guide

## Overview

Phase 3 adds advanced user-facing features including market analytics, export capabilities, saved searches, and enhanced visualizations. These features provide professional-grade functionality for real estate analysis and decision-making.

**Status**: ✅ Core modules implemented
**Version**: 1.0.0
**Date**: 2025-11-07

---

## 📦 New Modules

### 1. Market Insights (`analytics/market_insights.py`)

Comprehensive market analysis and trend detection system.

#### Features:
- **Overall Market Statistics**: Total properties, price ranges, averages, amenity distributions
- **Price Trend Analysis**: Directional trends with confidence levels
- **Location Insights**: City-by-city analysis with price comparisons
- **Property Type Analytics**: Breakdowns by apartment, house, studio, etc.
- **Value Analysis**: Best value properties based on multi-factor scoring
- **Amenity Impact**: How amenities affect property prices (% increase/decrease)
- **Location Comparisons**: Side-by-side city comparisons

#### Classes:

```python
from analytics import MarketInsights, PriceTrend, MarketStatistics

# Initialize with properties
insights = MarketInsights(property_collection)

# Get overall statistics
stats = insights.get_overall_statistics()
# Returns: MarketStatistics(total_properties, avg_price, median_price, ...)

# Analyze price trends
trend = insights.get_price_trend(city="Krakow")
# Returns: PriceTrend(direction, change_percent, confidence, ...)

# Location-specific insights
krakow_insights = insights.get_location_insights("Krakow")
# Returns: LocationInsights(city, avg_price, amenity_availability, ...)

# Property type analysis
apartment_insights = insights.get_property_type_insights("apartment")

# Best value properties
best_values = insights.get_best_value_properties(top_n=5)

# Compare two locations
comparison = insights.compare_locations("Warsaw", "Krakow")
```

#### Key Metrics:

| Metric | Description | Use Case |
|--------|-------------|----------|
| Average Price | Mean price across all properties | Market overview |
| Median Price | Middle value (less affected by outliers) | Typical property price |
| Price Trend | Direction and rate of change | Market momentum |
| Amenity Impact | % price increase per amenity | Feature valuation |
| Price/sqm | Cost per square meter | Value comparison |
| Best Value Score | Multi-factor value rating (0-1) | Purchase recommendations |

---

### 2. Property Exporter (`utils/exporters.py`)

Multi-format export system for property data.

#### Supported Formats:
- **CSV**: Simple spreadsheet format
- **Excel**: Multi-sheet workbooks with statistics
- **JSON**: Structured data format
- **Markdown**: Human-readable reports

#### Usage:

```python
from utils import PropertyExporter, ExportFormat

# Initialize exporter
exporter = PropertyExporter(property_collection)

# Export to CSV
csv_data = exporter.export_to_csv(columns=['city', 'price', 'rooms'])

# Export to Excel with statistics
excel_file = exporter.export_to_excel(
    include_summary=True,
    include_statistics=True
)

# Export to JSON
json_data = exporter.export_to_json(pretty=True, include_metadata=True)

# Export to Markdown report
markdown_report = exporter.export_to_markdown(
    include_summary=True,
    max_properties=10
)

# Generic export method
data = exporter.export(ExportFormat.EXCEL)
filename = exporter.get_filename(ExportFormat.EXCEL, prefix="properties")
```

#### Excel Export Sheets:

1. **Properties**: Full property listing with all fields
2. **Summary**: Key statistics and counts
3. **By City**: Aggregated stats grouped by city
4. **By Type**: Aggregated stats grouped by property type

#### Markdown Export Structure:

```markdown
# Property Listing Report

Generated: 2025-11-07 14:30:00
Total Properties: 25

## Summary Statistics
- Average Price: $950.00
- Median Price: $890.00
- Properties with Parking: 15 (60%)

### By City
- **Krakow**: 18 properties (avg: $875.00)
- **Warsaw**: 7 properties (avg: $1,200.00)

## Property Listings

### 1. Property in Krakow
- **Price**: $950/month
- **Type**: Apartment
- **Rooms**: 2 bedrooms, 1 bathrooms
- **Area**: 55 sqm
- **Amenities**: Parking, Balcony
```

---

### 3. Saved Searches (`utils/saved_searches.py`)

User preference and search management system.

#### Features:
- Save search criteria with custom names
- Track search usage and last used date
- Favorite properties with notes and tags
- User preferences (display, models, notifications)
- Automatic property matching against saved searches
- Convert saved searches to natural language queries

#### Classes:

```python
from utils import SavedSearchManager, SavedSearch, UserPreferences

# Initialize manager
manager = SavedSearchManager(storage_path=".user_data")

# Create saved search
search = SavedSearch(
    id="search_1",
    name="Affordable 2-bed in Krakow",
    city="Krakow",
    min_rooms=2,
    max_rooms=2,
    max_price=1000,
    must_have_parking=True
)

# Save search
manager.save_search(search)

# Get all saved searches
searches = manager.get_all_searches()

# Check if property matches
property_dict = property.dict()
if search.matches(property_dict):
    print("Property matches saved search!")

# Convert to query string
query = search.to_query_string()
# "Find properties in Krakow with 2 rooms priced under $1000 with parking"

# Manage favorites
manager.add_favorite(property_id="prop_123", notes="Great location!", tags=["favorite", "krakow"])
manager.remove_favorite("prop_123")
is_fav = manager.is_favorite("prop_123")

# User preferences
prefs = UserPreferences(
    default_sort="price_asc",
    results_per_page=10,
    preferred_model="gpt-4o-mini",
    max_budget=1500,
    preferred_cities=["Krakow", "Warsaw"]
)
manager.update_preferences(prefs)
```

#### Storage:

Files stored in `.user_data/` directory:
- `saved_searches.json`: All saved searches
- `preferences.json`: User preferences
- `favorites.json`: Favorited properties

---

### 4. Session Analytics (`analytics/session_tracker.py`)

Usage tracking and behavior analytics system.

#### Tracked Events:
- Queries (with intent and complexity)
- Property views
- Searches (with criteria)
- Exports (with format)
- Favorites (add/remove)
- Model changes
- Tool usage
- Errors

#### Usage:

```python
from analytics import SessionTracker, EventType
import uuid

# Initialize tracker
session_id = str(uuid.uuid4())
tracker = SessionTracker(session_id, storage_path=".analytics")

# Track events
tracker.track_query(
    query="Find 2-bed apartments in Krakow",
    intent="filtered_search",
    complexity="medium",
    processing_time_ms=250
)

tracker.track_property_view(
    property_id="prop_123",
    property_city="Krakow",
    property_price=950
)

tracker.track_export(format="excel", property_count=10)

tracker.track_tool_use(tool_name="mortgage_calculator", parameters={"price": 200000})

# Get session statistics
stats = tracker.get_session_stats()
# Returns: SessionStats(total_queries, total_property_views, tools_used, ...)

# Get popular queries
popular = tracker.get_popular_queries(top_n=5)

# Get average processing time
avg_time = tracker.get_avg_processing_time(EventType.QUERY)

# Finalize session (saves to disk)
tracker.finalize_session()

# Get aggregate stats across all sessions
aggregate = SessionTracker.get_aggregate_stats(storage_path=".analytics")
```

#### Analytics Storage:

Files stored in `.analytics/` directory:
- `session_{id}.json`: Individual session data
- `aggregate_stats.json`: Aggregated statistics across all sessions

#### Session Statistics:

```python
@dataclass
class SessionStats:
    session_id: str
    start_time: datetime
    end_time: Optional[datetime]
    total_queries: int
    total_property_views: int
    total_searches: int
    total_exports: int
    total_favorites: int
    unique_models_used: List[str]
    tools_used: List[str]
    errors_encountered: int
    total_duration_minutes: float
```

---

### 5. Enhanced Comparisons (`ui/comparison_viz.py`)

Rich property comparison visualizations.

#### Features:
- Side-by-side property comparisons (2-4 properties)
- Price comparison metrics
- Best value analysis with reasoning
- Amenity comparison matrix
- Chart data generation
- Streamlit UI components

#### Usage:

```python
from ui import PropertyComparison, create_comparison_chart, display_comparison_ui

# Create comparison
comparison = PropertyComparison(properties=[prop1, prop2, prop3])

# Get comparison table
table = comparison.get_comparison_table()
# Returns formatted DataFrame with all metrics

# Price comparison
price_comp = comparison.get_price_comparison()
# Returns: {cheapest, most_expensive, avg_price, price_range}

# Best value analysis
best_value = comparison.get_best_value()
# Returns: {property, city, price, value_score, reasoning}

# Amenity comparison
amenity_comp = comparison.get_amenity_comparison()

# Create chart data
chart_data = create_comparison_chart([prop1, prop2, prop3])

# Display in Streamlit
display_comparison_ui(properties=[prop1, prop2, prop3])
```

#### Comparison Table Columns:

- Property identifier
- City
- Price (formatted)
- Type
- Rooms / Bathrooms
- Area (sqm)
- Price per sqm
- Amenities (✓/✗ indicators)
- Amenity count

#### Value Scoring Algorithm:

```python
value_score = (
    price_score * 0.4 +      # 40% weight on competitive price
    room_score * 0.3 +        # 30% weight on spaciousness
    amenity_score * 0.3       # 30% weight on amenities
)
```

**Reasoning Examples:**
- "Best value due to competitive price, spacious, well-equipped"
- "Best value due to competitive price"
- "Best value due to balanced features"

---

## 📊 Integration Examples

### Complete Market Analysis Workflow

```python
from data.schemas import PropertyCollection
from analytics import MarketInsights
from utils import PropertyExporter, ExportFormat

# Load properties
properties = PropertyCollection(...)

# 1. Get market insights
insights = MarketInsights(properties)
stats = insights.get_overall_statistics()
trend = insights.get_price_trend()

print(f"Market Overview:")
print(f"Total Properties: {stats.total_properties}")
print(f"Average Price: ${stats.average_price:.2f}")
print(f"Price Trend: {trend.direction.value} ({trend.change_percent:+.1f}%)")

# 2. Compare locations
comparison = insights.compare_locations("Warsaw", "Krakow")
print(f"Price Difference: ${comparison['price_difference']:.2f}")
print(f"Cheaper City: {comparison['cheaper_city']}")

# 3. Find best values
best_properties = insights.get_best_value_properties(top_n=5)
for prop in best_properties:
    print(f"{prop['city']}: ${prop['price']}, Value Score: {prop['value_score']:.2f}")

# 4. Export report
exporter = PropertyExporter(properties)
markdown_report = exporter.export_to_markdown(include_summary=True)
with open("market_report.md", "w") as f:
    f.write(markdown_report)

excel_file = exporter.export_to_excel(include_statistics=True)
with open("properties.xlsx", "wb") as f:
    f.write(excel_file.getvalue())
```

### Saved Search Workflow

```python
from utils import SavedSearchManager, SavedSearch
from datetime import datetime
import uuid

# Initialize manager
manager = SavedSearchManager()

# Create saved search
search_id = str(uuid.uuid4())
search = SavedSearch(
    id=search_id,
    name="Budget Friendly 2-Bedroom",
    description="Affordable 2-bedroom apartments with parking",
    city="Krakow",
    min_rooms=2,
    max_rooms=2,
    max_price=1000,
    must_have_parking=True,
    notify_on_new=True
)

manager.save_search(search)

# Later: Find matching properties
matching_properties = []
for prop in all_properties:
    if search.matches(prop.dict()):
        matching_properties.append(prop)

print(f"Found {len(matching_properties)} matching properties")

# Track usage
manager.increment_search_usage(search_id)

# Get query string for display
query_str = search.to_query_string()
print(f"Searching for: {query_str}")
```

### Session Tracking Workflow

```python
from analytics import SessionTracker
import uuid
import time

# Start session
session_id = str(uuid.uuid4())
tracker = SessionTracker(session_id)

# User performs query
start_time = time.time()
# ... process query ...
processing_time = int((time.time() - start_time) * 1000)

tracker.track_query(
    query="Find apartments under $1000",
    intent="filtered_search",
    complexity="medium",
    processing_time_ms=processing_time
)

# User views properties
for property_id in viewed_properties:
    tracker.track_property_view(property_id)

# User exports data
tracker.track_export(format="excel", property_count=len(matching_properties))

# End session
stats = tracker.get_session_stats()
tracker.finalize_session()

print(f"Session Summary:")
print(f"Duration: {stats.total_duration_minutes:.1f} minutes")
print(f"Queries: {stats.total_queries}")
print(f"Property Views: {stats.total_property_views}")
print(f"Exports: {stats.total_exports}")
```

---

## 🎨 UI Integration Patterns

### Market Insights Dashboard

```python
import streamlit as st
from analytics import MarketInsights
from ui.comparison_viz import display_market_insights_ui

# Get insights
insights = MarketInsights(properties)
stats = insights.get_overall_statistics()
price_dist = insights.get_price_distribution(bins=10)
amenity_impact = insights.get_amenity_impact_on_price()

# Prepare data for UI
insights_data = {
    'overall_stats': stats.dict(),
    'price_distribution': price_dist,
    'amenity_impact': amenity_impact
}

# Display in Streamlit
display_market_insights_ui(insights_data)
```

### Export Functionality

```python
import streamlit as st
from utils import PropertyExporter, ExportFormat

# Create exporter
exporter = PropertyExporter(properties)

# UI controls
st.subheader("Export Properties")

format_choice = st.selectbox(
    "Select Format",
    options=[fmt.value for fmt in ExportFormat],
    format_func=lambda x: x.upper()
)

if st.button("Export"):
    if format_choice == ExportFormat.CSV.value:
        data = exporter.export_to_csv()
        st.download_button(
            "Download CSV",
            data=data,
            file_name=exporter.get_filename(ExportFormat.CSV),
            mime="text/csv"
        )

    elif format_choice == ExportFormat.EXCEL.value:
        data = exporter.export_to_excel()
        st.download_button(
            "Download Excel",
            data=data.getvalue(),
            file_name=exporter.get_filename(ExportFormat.EXCEL),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    elif format_choice == ExportFormat.JSON.value:
        data = exporter.export_to_json()
        st.download_button(
            "Download JSON",
            data=data,
            file_name=exporter.get_filename(ExportFormat.JSON),
            mime="application/json"
        )

    elif format_choice == ExportFormat.MARKDOWN.value:
        data = exporter.export_to_markdown()
        st.download_button(
            "Download Markdown",
            data=data,
            file_name=exporter.get_filename(ExportFormat.MARKDOWN),
            mime="text/markdown"
        )
```

### Saved Searches UI

```python
import streamlit as st
from utils import SavedSearchManager, SavedSearch
import uuid

# Initialize manager
if 'search_manager' not in st.session_state:
    st.session_state.search_manager = SavedSearchManager()

manager = st.session_state.search_manager

# Display saved searches
st.subheader("Saved Searches")

searches = manager.get_all_searches()

if searches:
    for search in searches:
        with st.expander(f"📌 {search.name}"):
            st.write(f"**Query**: {search.to_query_string()}")
            st.write(f"**Used**: {search.use_count} times")
            if search.last_used:
                st.write(f"**Last Used**: {search.last_used.strftime('%Y-%m-%d %H:%M')}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Use Search", key=f"use_{search.id}"):
                    # Apply search criteria
                    manager.increment_search_usage(search.id)
                    st.rerun()
            with col2:
                if st.button("Delete", key=f"del_{search.id}"):
                    manager.delete_search(search.id)
                    st.rerun()
else:
    st.info("No saved searches yet")

# Create new search
with st.form("new_search"):
    st.subheader("Create New Search")

    name = st.text_input("Search Name")
    city = st.text_input("City (optional)")

    col1, col2 = st.columns(2)
    with col1:
        min_price = st.number_input("Min Price", min_value=0)
    with col2:
        max_price = st.number_input("Max Price", min_value=0)

    min_rooms = st.number_input("Min Rooms", min_value=0)

    parking = st.checkbox("Must have parking")
    garden = st.checkbox("Must have garden")

    if st.form_submit_button("Save Search"):
        search = SavedSearch(
            id=str(uuid.uuid4()),
            name=name,
            city=city if city else None,
            min_price=min_price if min_price > 0 else None,
            max_price=max_price if max_price > 0 else None,
            min_rooms=min_rooms if min_rooms > 0 else None,
            must_have_parking=parking,
            must_have_garden=garden
        )
        manager.save_search(search)
        st.success(f"Saved search: {name}")
        st.rerun()
```

---

## 🔧 Configuration

### Dependencies

All required dependencies are already in `requirements.txt`:

```txt
pandas>=2.1.0
openpyxl>=3.1.0  # For Excel export
streamlit>=1.37.0
pydantic>=2.5.0
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### Storage Directories

The Phase 3 modules create the following directories:

- `.user_data/` - Saved searches, preferences, favorites
- `.analytics/` - Session tracking and aggregate statistics

These directories are created automatically and should be added to `.gitignore`:

```bash
echo ".user_data/" >> .gitignore
echo ".analytics/" >> .gitignore
```

---

## 📈 Performance Characteristics

### Market Insights

| Operation | Time Complexity | Space | Notes |
|-----------|----------------|-------|-------|
| Overall Statistics | O(n) | O(1) | Single pass through data |
| Price Trend | O(n) | O(1) | Simple arithmetic |
| Location Insights | O(n) | O(m) | m = unique cities |
| Best Value | O(n log n) | O(n) | Requires sorting |
| Amenity Impact | O(n) | O(1) | 6 amenity comparisons |

**Recommended**: Cache insights for large datasets (>1000 properties)

### Export Operations

| Format | Speed | File Size | Best For |
|--------|-------|-----------|----------|
| CSV | Fast | Small | Data import/export |
| Excel | Medium | Medium | Human-readable reports |
| JSON | Fast | Medium | API integration |
| Markdown | Fast | Small | Documentation |

### Session Tracking

- **Overhead per event**: ~0.1-0.5ms
- **Storage**: ~1KB per 100 events
- **Auto-save**: Every 10 events (configurable)

---

## 🧪 Testing

### Unit Test Coverage ✅

**Status**: All Phase 3 modules have comprehensive test coverage with **163 passing tests**

#### Test Statistics

| Module | Test File | Tests | Coverage |
|--------|-----------|-------|----------|
| Market Insights | `test_market_insights.py` | 26 tests | All public methods |
| Exporters | `test_exporters.py` | 32 tests | All 4 formats |
| Saved Searches | `test_saved_searches.py` | 36 tests | CRUD + persistence |
| Session Tracker | `test_session_tracker.py` | 38 tests | All event types |
| Comparison Viz | `test_comparison_viz.py` | 31 tests | All visualizations |
| **Total** | **5 test files** | **163 tests** | **100% passing** |

#### Running Tests

```bash
# Run all Phase 3 tests
./run_tests.sh phase3

# Run specific module tests
./run_tests.sh insights      # Market insights only
./run_tests.sh exporters     # Exporters only
./run_tests.sh searches      # Saved searches only
./run_tests.sh tracker       # Session tracker only
./run_tests.sh comparison    # Property comparison only

# Run with coverage report
./run_tests.sh coverage

# Quick validation (essential tests only)
./run_tests.sh quick
```

#### Test Coverage Details

**Market Insights (`test_market_insights.py` - 26 tests)**
- Overall statistics calculation
- Price trend analysis (all directions)
- Location insights with price comparisons
- Property type analytics
- Best value property identification
- Amenity impact analysis
- Location comparisons
- Price distribution
- Edge cases (empty datasets, insufficient data)

**Exporters (`test_exporters.py` - 32 tests)**
- CSV export (basic, no header, specific columns)
- Excel export (multi-sheet with summary and statistics)
- JSON export (pretty, compact, with/without metadata)
- Markdown export (with summary, max properties limit)
- Filename generation for all formats
- Empty collection handling
- Single property edge case
- Missing optional fields

**Saved Searches (`test_saved_searches.py` - 36 tests)**
- Search creation with all criteria
- Property matching algorithm (city, price, rooms, amenities, type)
- CRUD operations (create, read, update, delete)
- Persistence across manager instances
- Search usage tracking
- Query string generation
- User preferences management
- Favorite properties (add, remove, check)
- Storage file integrity
- Edge cases (empty manager, all criteria)

**Session Tracker (`test_session_tracker.py` - 38 tests)**
- All 8 event types (QUERY, PROPERTY_VIEW, SEARCH, EXPORT, FAVORITE, MODEL_CHANGE, TOOL_USE, ERROR)
- Session statistics calculation
- Popular queries tracking
- Average processing time
- Session persistence (JSON serialization)
- Aggregate statistics across sessions
- Large data payloads
- Special characters handling
- Edge cases (empty session, very long IDs, null values)

**Property Comparison (`test_comparison_viz.py` - 31 tests)**
- Comparison initialization (2-4 properties validation)
- Comparison table generation
- Price comparison metrics
- Best value analysis with reasoning
- Amenity comparison matrix
- Value scoring algorithm (40% price, 30% rooms, 30% amenities)
- Chart data generation
- Price per sqm calculation
- Edge cases (identical prices/rooms, no/all amenities)

### Integration Testing

Test complete workflows:

```python
# Test market insights workflow
def test_market_insights_workflow():
    properties = load_test_properties()
    insights = MarketInsights(properties)

    stats = insights.get_overall_statistics()
    assert stats.total_properties == len(properties)

    trend = insights.get_price_trend()
    assert trend.direction in [TrendDirection.INCREASING, TrendDirection.DECREASING, TrendDirection.STABLE]

# Test export workflow
def test_export_workflow():
    properties = load_test_properties()
    exporter = PropertyExporter(properties)

    csv = exporter.export_to_csv()
    assert len(csv) > 0

    excel = exporter.export_to_excel()
    assert excel.getbuffer().nbytes > 0  # Has content

# Test saved search workflow
def test_saved_search_workflow():
    manager = SavedSearchManager(storage_path=".test_data")

    search = SavedSearch(
        id="test_1",
        name="Test Search",
        max_price=1000
    )

    manager.save_search(search)
    loaded = manager.get_search("test_1")
    assert loaded.name == "Test Search"
```

### Test Quality Metrics

- **Code Coverage**: 95%+ for all Phase 3 modules
- **Edge Cases**: Comprehensive (empty data, single items, large datasets)
- **Persistence**: All storage operations tested with temporary directories
- **Error Handling**: Invalid inputs and error conditions covered
- **Performance**: Tests complete in ~2 seconds
- **Maintainability**: Clear test names, well-documented, organized by class

---

## 🚀 Next Steps

### Phase 3 Integration into app_modern.py

**Planned enhancements to `app_modern.py`:**

1. **New Tab: Market Insights**
   - Overall statistics dashboard
   - Price trend charts
   - Location comparisons
   - Best value properties

2. **New Tab: Analytics**
   - Session statistics
   - Usage patterns
   - Popular queries
   - Model usage breakdown

3. **Enhanced Export Menu**
   - Format selection (CSV/Excel/JSON/Markdown)
   - Download buttons
   - Export history

4. **Saved Searches Sidebar**
   - Quick search selection
   - Create new searches
   - Edit existing searches
   - Search usage stats

5. **Property Comparison Tool**
   - Select 2-4 properties
   - Visual comparison
   - Best value recommendation

6. **Session Tracking Integration**
   - Automatic event tracking
   - Real-time statistics
   - Usage analytics

### Future Enhancements

1. **Advanced Visualizations**
   - Interactive price trend charts (Plotly)
   - Geographic heat maps
   - 3D scatter plots

2. **Notification System**
   - Email alerts for saved searches
   - Price drop notifications
   - New property alerts

3. **Collaboration Features**
   - Share saved searches
   - Team favorites
   - Shared notes

4. **Advanced Analytics**
   - Predictive price modeling
   - Market forecast
   - Investment ROI calculator

---

## 📚 API Reference

### Market Insights API

```python
MarketInsights(properties: PropertyCollection)
├── get_overall_statistics() -> MarketStatistics
├── get_price_trend(city: Optional[str]) -> PriceTrend
├── get_location_insights(city: str) -> LocationInsights
├── get_property_type_insights(type: str) -> PropertyTypeInsights
├── get_price_distribution(bins: int) -> Dict
├── get_amenity_impact_on_price() -> Dict[str, float]
├── get_best_value_properties(top_n: int) -> List[Dict]
└── compare_locations(city1: str, city2: str) -> Dict
```

### Export API

```python
PropertyExporter(properties: PropertyCollection)
├── export_to_csv(columns: Optional[List], include_header: bool) -> str
├── export_to_excel(include_summary: bool, include_statistics: bool) -> BytesIO
├── export_to_json(pretty: bool, include_metadata: bool) -> str
├── export_to_markdown(include_summary: bool, max_properties: Optional[int]) -> str
├── export(format: ExportFormat, **kwargs) -> str | BytesIO
└── get_filename(format: ExportFormat, prefix: str) -> str
```

### Saved Searches API

```python
SavedSearchManager(storage_path: str)
├── save_search(search: SavedSearch) -> SavedSearch
├── get_search(search_id: str) -> Optional[SavedSearch]
├── get_all_searches() -> List[SavedSearch]
├── delete_search(search_id: str) -> bool
├── increment_search_usage(search_id: str) -> None
├── add_favorite(property_id: str, notes: Optional[str], tags: Optional[List]) -> FavoriteProperty
├── remove_favorite(property_id: str) -> bool
├── get_favorites() -> List[FavoriteProperty]
└── is_favorite(property_id: str) -> bool
```

### Session Tracking API

```python
SessionTracker(session_id: str, storage_path: str)
├── track_event(event_type: EventType, data: Dict, duration_ms: Optional[int]) -> None
├── track_query(query: str, intent: str, complexity: str, processing_time_ms: int) -> None
├── track_property_view(property_id: str, property_city: str, property_price: float) -> None
├── track_search(search_criteria: Dict, results_count: int) -> None
├── track_export(format: str, property_count: int) -> None
├── track_favorite(property_id: str, action: str) -> None
├── track_model_change(old_model: str, new_model: str) -> None
├── track_tool_use(tool_name: str, parameters: Dict) -> None
├── track_error(error_type: str, error_message: str) -> None
├── get_session_stats() -> SessionStats
├── get_popular_queries(top_n: int) -> List[Dict]
├── get_avg_processing_time(event_type: EventType) -> Optional[float]
├── finalize_session() -> None
└── get_aggregate_stats(storage_path: str) -> Dict [classmethod]
```

### Comparison Viz API

```python
PropertyComparison(properties: List[Property])
├── get_comparison_table() -> pd.DataFrame
├── get_price_comparison() -> Dict
├── get_best_value() -> Dict
└── get_amenity_comparison() -> pd.DataFrame

# Utility functions
create_comparison_chart(properties: List[Property]) -> Dict
create_price_trend_chart(prices: List[float], labels: List[str]) -> Dict
display_comparison_ui(properties: List[Property]) -> None
display_market_insights_ui(insights_data: Dict) -> None
```

---

## 📝 Change Log

### Version 1.0.0 (2025-11-07)

**New Features:**
- ✅ Market insights with comprehensive analytics
- ✅ Multi-format export (CSV, Excel, JSON, Markdown)
- ✅ Saved searches and user preferences
- ✅ Session tracking and analytics
- ✅ Enhanced property comparison visualizations

**Files Added:**
- `analytics/market_insights.py` (550+ lines)
- `analytics/session_tracker.py` (450+ lines)
- `utils/exporters.py` (400+ lines)
- `utils/saved_searches.py` (500+ lines)
- `ui/comparison_viz.py` (450+ lines)

**Dependencies Added:**
- `openpyxl ^3.1.0` (Excel export support)

**Total Lines of Code**: ~2,350 lines

---

## 🤝 Contributing

When extending Phase 3 features:

1. **Follow existing patterns**: Match the code style and architecture
2. **Add tests**: Unit tests for all new functionality
3. **Update documentation**: Keep this README in sync
4. **Performance**: Profile new features with large datasets
5. **Storage**: Use consistent storage patterns (.user_data, .analytics)

---

## 📧 Support

For questions or issues with Phase 3 features:
1. Check this documentation
2. Review code examples above
3. Examine unit tests for usage patterns
4. Refer to API reference section

---

**Phase 3 Status**: ✅ Core modules complete, ready for integration
**Next Step**: Integrate into app_modern.py with new UI tabs
