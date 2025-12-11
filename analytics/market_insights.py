"""
Market insights and analytics for real estate data.

This module provides comprehensive market analysis including:
- Price trends and statistics
- Location-based insights
- Property type analysis
- Amenity correlation analysis
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field

from data.schemas import Property, PropertyCollection, PropertyType


class TrendDirection(str, Enum):
    """Trend direction indicators."""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class PriceTrend:
    """Price trend analysis result."""
    direction: TrendDirection
    change_percent: float
    average_price: float
    median_price: float
    price_range: tuple[float, float]
    sample_size: int
    confidence: str  # "high", "medium", "low"


class MarketStatistics(BaseModel):
    """Comprehensive market statistics."""
    total_properties: int = Field(description="Total number of properties")
    average_price: float = Field(description="Average property price")
    median_price: float = Field(description="Median property price")
    min_price: float = Field(description="Minimum price")
    max_price: float = Field(description="Maximum price")
    std_dev: float = Field(description="Standard deviation of prices")

    # Room statistics
    avg_rooms: float = Field(description="Average number of rooms")
    avg_area: Optional[float] = Field(None, description="Average area in sqm")

    # Amenity statistics
    parking_percentage: float = Field(description="Percentage with parking")
    garden_percentage: float = Field(description="Percentage with garden")
    furnished_percentage: float = Field(description="Percentage furnished")

    # Location breakdown
    cities: Dict[str, int] = Field(default_factory=dict, description="Properties by city")
    property_types: Dict[str, int] = Field(default_factory=dict, description="Properties by type")

    # Price per sqm
    avg_price_per_sqm: Optional[float] = Field(None, description="Average price per square meter")


class LocationInsights(BaseModel):
    """Insights for a specific location."""
    city: str
    property_count: int
    avg_price: float
    median_price: float
    avg_price_per_sqm: Optional[float] = None
    most_common_room_count: Optional[float] = None
    amenity_availability: Dict[str, float] = Field(default_factory=dict)
    price_comparison: Optional[str] = None  # "above_average", "below_average", "average"


class PropertyTypeInsights(BaseModel):
    """Insights for a specific property type."""
    property_type: str
    count: int
    avg_price: float
    median_price: float
    avg_rooms: float
    avg_area: Optional[float] = None
    popular_locations: List[str] = Field(default_factory=list)


class MarketInsights:
    """
    Analyzer for real estate market insights and trends.

    Provides comprehensive market analysis including price trends,
    location comparisons, and property type analytics.
    """

    def __init__(self, properties: PropertyCollection):
        """
        Initialize market insights with property data.

        Args:
            properties: Collection of properties to analyze
        """
        self.properties = properties
        self.df = self._to_dataframe()

    def _to_dataframe(self) -> pd.DataFrame:
        """Convert properties to pandas DataFrame for analysis."""
        data = []
        for prop in self.properties.properties:
            data.append({
                'country': getattr(prop, 'country', None),
                'region': getattr(prop, 'region', None),
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
                'lat': getattr(prop, 'latitude', None),
                'lon': getattr(prop, 'longitude', None),
                'currency': getattr(prop, 'currency', None),
            })
        return pd.DataFrame(data)

    def get_overall_statistics(self) -> MarketStatistics:
        """
        Calculate comprehensive market statistics.

        Returns:
            MarketStatistics with overall market metrics
        """
        if len(self.df) == 0:
            return MarketStatistics(
                total_properties=0,
                average_price=0,
                median_price=0,
                min_price=0,
                max_price=0,
                std_dev=0,
                avg_rooms=0,
                parking_percentage=0,
                garden_percentage=0,
                furnished_percentage=0
            )

        # Calculate price per sqm where area is available
        price_per_sqm = None
        if self.df['area_sqm'].notna().any():
            valid_area = self.df[self.df['area_sqm'].notna()]
            price_per_sqm = (valid_area['price'] / valid_area['area_sqm']).mean()

        # Average area
        avg_area = self.df['area_sqm'].mean() if self.df['area_sqm'].notna().any() else None

        return MarketStatistics(
            total_properties=len(self.df),
            average_price=float(self.df['price'].mean()),
            median_price=float(self.df['price'].median()),
            min_price=float(self.df['price'].min()),
            max_price=float(self.df['price'].max()),
            std_dev=float(self.df['price'].std()),
            avg_rooms=float(self.df['rooms'].mean()),
            avg_area=float(avg_area) if avg_area is not None and not np.isnan(avg_area) else None,
            parking_percentage=float(self.df['has_parking'].mean() * 100),
            garden_percentage=float(self.df['has_garden'].mean() * 100),
            furnished_percentage=float(self.df['is_furnished'].mean() * 100),
            cities=self.df['city'].value_counts().to_dict(),
            property_types=self.df['property_type'].value_counts().to_dict(),
            avg_price_per_sqm=float(price_per_sqm) if price_per_sqm is not None and not np.isnan(price_per_sqm) else None
        )

    def get_price_trend(self, city: Optional[str] = None) -> PriceTrend:
        """
        Analyze price trends for overall market or specific city.

        Args:
            city: Optional city name to filter by

        Returns:
            PriceTrend with trend analysis
        """
        df = self.df if city is None else self.df[self.df['city'] == city]

        if len(df) < 5:
            return PriceTrend(
                direction=TrendDirection.INSUFFICIENT_DATA,
                change_percent=0.0,
                average_price=float(df['price'].mean()) if len(df) > 0 else 0.0,
                median_price=float(df['price'].median()) if len(df) > 0 else 0.0,
                price_range=(float(df['price'].min()), float(df['price'].max())) if len(df) > 0 else (0.0, 0.0),
                sample_size=len(df),
                confidence="low"
            )

        # Calculate basic statistics
        avg_price = float(df['price'].mean())
        median_price = float(df['price'].median())
        std_dev = float(df['price'].std())

        # Simple trend detection (comparing first half vs second half)
        mid_point = len(df) // 2
        first_half_avg = float(df.iloc[:mid_point]['price'].mean())
        second_half_avg = float(df.iloc[mid_point:]['price'].mean())

        change_percent = ((second_half_avg - first_half_avg) / first_half_avg) * 100

        # Determine trend direction
        if abs(change_percent) < 2:
            direction = TrendDirection.STABLE
        elif change_percent > 0:
            direction = TrendDirection.INCREASING
        else:
            direction = TrendDirection.DECREASING

        # Determine confidence based on sample size and consistency
        if len(df) >= 20:
            confidence = "high"
        elif len(df) >= 10:
            confidence = "medium"
        else:
            confidence = "low"

        return PriceTrend(
            direction=direction,
            change_percent=change_percent,
            average_price=avg_price,
            median_price=median_price,
            price_range=(float(df['price'].min()), float(df['price'].max())),
            sample_size=len(df),
            confidence=confidence
        )

    def get_location_insights(self, city: str) -> Optional[LocationInsights]:
        """
        Get detailed insights for a specific location.

        Args:
            city: City name to analyze

        Returns:
            LocationInsights or None if city not found
        """
        city_df = self.df[self.df['city'] == city]

        if len(city_df) == 0:
            return None

        # Calculate price per sqm
        price_per_sqm = None
        if city_df['area_sqm'].notna().any():
            valid_area = city_df[city_df['area_sqm'].notna()]
            price_per_sqm = float((valid_area['price'] / valid_area['area_sqm']).mean())

        # Most common room count
        most_common_rooms = None
        if len(city_df['rooms']) > 0:
            most_common_rooms = float(city_df['rooms'].mode().iloc[0]) if len(city_df['rooms'].mode()) > 0 else None

        # Amenity availability
        amenity_availability = {
            'parking': float(city_df['has_parking'].mean() * 100),
            'garden': float(city_df['has_garden'].mean() * 100),
            'pool': float(city_df['has_pool'].mean() * 100),
            'furnished': float(city_df['is_furnished'].mean() * 100),
            'balcony': float(city_df['has_balcony'].mean() * 100),
            'elevator': float(city_df['has_elevator'].mean() * 100),
        }

        # Price comparison to overall market
        overall_avg = float(self.df['price'].mean())
        city_avg = float(city_df['price'].mean())

        if city_avg > overall_avg * 1.1:
            price_comparison = "above_average"
        elif city_avg < overall_avg * 0.9:
            price_comparison = "below_average"
        else:
            price_comparison = "average"

        return LocationInsights(
            city=city,
            property_count=len(city_df),
            avg_price=city_avg,
            median_price=float(city_df['price'].median()),
            avg_price_per_sqm=price_per_sqm,
            most_common_room_count=most_common_rooms,
            amenity_availability=amenity_availability,
            price_comparison=price_comparison
        )

    def get_city_price_indices(self, cities: Optional[List[str]] = None) -> pd.DataFrame:
        """Compute basic price indices per city."""
        df = self.df.copy()
        if cities:
            df = df[df['city'].isin(cities)]
        group = df.groupby('city')
        res = group.agg(
            avg_price=('price', 'mean'),
            median_price=('price', 'median'),
            count=('price', 'count')
        ).reset_index()
        if df['area_sqm'].notna().any():
            res['avg_price_per_sqm'] = group.apply(lambda g: (g['price'] / g['area_sqm']).dropna().mean()).values
        else:
            res['avg_price_per_sqm'] = np.nan
        return res

    def filter_by_geo_radius(self, center_lat: float, center_lon: float, radius_km: float) -> pd.DataFrame:
        """Filter properties within radius from a center point."""
        df = self.df.copy()
        if df[['lat','lon']].isnull().any().any():
            df = df.dropna(subset=['lat','lon'])
        if len(df) == 0:
            return df
        lat1 = np.radians(center_lat)
        lon1 = np.radians(center_lon)
        lat2 = np.radians(df['lat'].astype(float))
        lon2 = np.radians(df['lon'].astype(float))
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        earth_radius_km = 6371.0
        dist = earth_radius_km * c
        return df[dist <= radius_km]

    def get_monthly_price_index(self, city: Optional[str] = None) -> pd.DataFrame:
        """Compute monthly average/median price and YoY change.

        Uses `scraped_at` timestamps where available; falls back to `last_updated` if needed.
        """
        df = self.df.copy()
        # Attach timestamps from original properties if missing in df
        if 'scraped_at' not in df.columns:
            # Rebuild from properties list
            scraped = []
            for p in self.properties.properties:
                scraped.append(getattr(p, 'scraped_at', None))
            # pad to length of df
            while len(scraped) < len(df):
                scraped.append(None)
            df['scraped_at'] = scraped[:len(df)]
        if 'scraped_at' in df.columns and df['scraped_at'].isnull().all():
            # fallback to last_updated
            if 'last_updated' in df.columns:
                df['scraped_at'] = df['last_updated']
        # Drop rows without timestamps
        df = df.dropna(subset=['scraped_at'])
        # Convert to pandas datetime
        df['dt'] = pd.to_datetime(df['scraped_at'])
        if city:
            df = df[df['city'] == city]
        if len(df) == 0:
            return pd.DataFrame(columns=['month', 'avg_price', 'median_price', 'count', 'yoy_pct'])
        df['month'] = df['dt'].dt.to_period('M').dt.to_timestamp()
        grouped = df.groupby('month').agg(
            avg_price=('price', 'mean'),
            median_price=('price', 'median'),
            count=('price', 'count')
        ).reset_index()
        # YoY percent: compare same month last year
        grouped['yoy_pct'] = None
        try:
            grouped = grouped.sort_values('month')
            # Build lookup of last year values
            prev = grouped.set_index('month')['avg_price'].shift(12)
            grouped['yoy_pct'] = ((grouped['avg_price'] - prev) / prev) * 100
        except Exception:
            pass
        return grouped

    def get_property_type_insights(self, property_type: str) -> Optional[PropertyTypeInsights]:
        """
        Get insights for a specific property type.

        Args:
            property_type: Property type to analyze

        Returns:
            PropertyTypeInsights or None if type not found
        """
        type_df = self.df[self.df['property_type'] == property_type]

        if len(type_df) == 0:
            return None

        # Average area
        avg_area = None
        if type_df['area_sqm'].notna().any():
            avg_area = float(type_df['area_sqm'].mean())

        # Popular locations (top 3)
        popular_locations = type_df['city'].value_counts().head(3).index.tolist()

        return PropertyTypeInsights(
            property_type=property_type,
            count=len(type_df),
            avg_price=float(type_df['price'].mean()),
            median_price=float(type_df['price'].median()),
            avg_rooms=float(type_df['rooms'].mean()),
            avg_area=avg_area,
            popular_locations=popular_locations
        )

    def get_price_distribution(self, bins: int = 10) -> Dict[str, Any]:
        """
        Get price distribution histogram data.

        Args:
            bins: Number of bins for histogram

        Returns:
            Dictionary with histogram data
        """
        hist, bin_edges = np.histogram(self.df['price'], bins=bins)

        return {
            'counts': hist.tolist(),
            'bin_edges': bin_edges.tolist(),
            'bins': [
                f"${bin_edges[i]:.0f}-${bin_edges[i+1]:.0f}"
                for i in range(len(bin_edges)-1)
            ]
        }

    def get_amenity_impact_on_price(self) -> Dict[str, float]:
        """
        Analyze how amenities affect property prices.

        Returns:
            Dictionary mapping amenity to average price difference (%)
        """
        amenities = ['has_parking', 'has_garden', 'has_pool', 'is_furnished', 'has_balcony', 'has_elevator']
        impact = {}

        overall_avg = float(self.df['price'].mean())

        for amenity in amenities:
            with_amenity = self.df[self.df[amenity] == True]['price'].mean()
            without_amenity = self.df[self.df[amenity] == False]['price'].mean()

            if pd.notna(with_amenity) and pd.notna(without_amenity) and without_amenity > 0:
                percent_diff = float(((with_amenity - without_amenity) / without_amenity) * 100)
                impact[amenity.replace('has_', '').replace('is_', '')] = percent_diff

        return impact

    def get_best_value_properties(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Identify properties with best value for money.

        Args:
            top_n: Number of top properties to return

        Returns:
            List of property dictionaries sorted by value score
        """
        if len(self.df) == 0:
            return []

        # Calculate value score
        df_with_score = self.df.copy()

        # Normalize price (lower is better)
        price_norm = (df_with_score['price'].max() - df_with_score['price']) / (df_with_score['price'].max() - df_with_score['price'].min()) if df_with_score['price'].max() != df_with_score['price'].min() else 0.5

        # Normalize rooms (higher is better)
        rooms_norm = (df_with_score['rooms'] - df_with_score['rooms'].min()) / (df_with_score['rooms'].max() - df_with_score['rooms'].min()) if df_with_score['rooms'].max() != df_with_score['rooms'].min() else 0.5

        # Count amenities
        amenity_cols = ['has_parking', 'has_garden', 'has_pool', 'is_furnished', 'has_balcony', 'has_elevator']
        df_with_score['amenity_count'] = df_with_score[amenity_cols].sum(axis=1)
        amenity_norm = df_with_score['amenity_count'] / 6  # 6 total amenities

        # Calculate value score (weighted combination)
        df_with_score['value_score'] = (
            price_norm * 0.4 +  # 40% weight on low price
            rooms_norm * 0.3 +  # 30% weight on rooms
            amenity_norm * 0.3  # 30% weight on amenities
        )

        # Get top properties
        top_properties = df_with_score.nlargest(top_n, 'value_score')

        return top_properties[['city', 'price', 'rooms', 'property_type', 'amenity_count', 'value_score']].to_dict('records')

    def compare_locations(self, city1: str, city2: str) -> Dict[str, Any]:
        """
        Compare two locations side by side.

        Args:
            city1: First city name
            city2: Second city name

        Returns:
            Dictionary with comparison metrics
        """
        insights1 = self.get_location_insights(city1)
        insights2 = self.get_location_insights(city2)

        if insights1 is None or insights2 is None:
            return {
                'error': 'One or both cities not found',
                'city1': city1,
                'city2': city2
            }

        return {
            'city1': insights1.dict(),
            'city2': insights2.dict(),
            'price_difference': insights1.avg_price - insights2.avg_price,
            'price_difference_percent': ((insights1.avg_price - insights2.avg_price) / insights2.avg_price) * 100,
            'cheaper_city': city1 if insights1.avg_price < insights2.avg_price else city2,
            'more_properties': city1 if insights1.property_count > insights2.property_count else city2
        }
