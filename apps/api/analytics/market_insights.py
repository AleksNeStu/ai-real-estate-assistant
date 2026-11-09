"""
Market insights and analytics for real estate data.

This module provides comprehensive market analysis including:
- Price trends and statistics
- Location-based insights
- Property type analysis
- Amenity correlation analysis
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from data.schemas import PropertyCollection


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


@dataclass
class HistoricalPricePoint:
    """Price point for a specific time period."""

    period: str  # e.g., "2023-01" or "2023-Q1"
    start_date: datetime
    end_date: datetime
    average_price: float
    median_price: float
    volume: int
    avg_price_per_sqm: Optional[float] = None
    # The currency the listings of this period are priced in.
    currency: Optional[str] = None


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
    # The currency the prices are in - the currency of the listings themselves.
    currency: Optional[str] = None


def _dominant_currency(city_df: pd.DataFrame) -> Optional[str]:
    """The currency most of the listings of a place are priced in.

    An average of prices in two currencies is a number without a meaning, so
    the currency is reported next to it — and the one most listings carry
    wins, because that is the one the reader can act on.
    """
    if "currency" not in city_df.columns:
        return None

    currencies = city_df["currency"].dropna()
    if len(currencies) == 0:
        return None

    counts = currencies.value_counts()
    return str(counts.index[0])


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
            data.append(
                {
                    "id": getattr(prop, "id", None),
                    "country": getattr(prop, "country", None),
                    "region": getattr(prop, "region", None),
                    "city": prop.city,
                    "district": getattr(prop, "district", None),
                    "neighborhood": getattr(prop, "neighborhood", None),
                    "price": prop.price,
                    "currency": getattr(prop, "currency", None),
                    "listing_type": (
                        prop.listing_type.value
                        if hasattr(prop.listing_type, "value")
                        else str(prop.listing_type)
                    ),
                    "rooms": prop.rooms,
                    "bathrooms": prop.bathrooms,
                    "area_sqm": prop.area_sqm,
                    "price_per_sqm": getattr(prop, "price_per_sqm", None),
                    "property_type": (
                        prop.property_type.value
                        if hasattr(prop.property_type, "value")
                        else str(prop.property_type)
                    ),
                    "has_parking": prop.has_parking,
                    "has_garden": prop.has_garden,
                    "has_pool": prop.has_pool,
                    "is_furnished": prop.is_furnished,
                    "has_balcony": prop.has_balcony,
                    "has_elevator": prop.has_elevator,
                    "lat": getattr(prop, "latitude", None),
                    "lon": getattr(prop, "longitude", None),
                    "year_built": getattr(prop, "year_built", None),
                    "energy_rating": getattr(prop, "energy_rating", None),
                    "scraped_at": getattr(prop, "scraped_at", None),
                    "last_updated": getattr(prop, "last_updated", None),
                }
            )
        df = pd.DataFrame(data)

        # Ensure datetime columns are properly typed
        if "scraped_at" in df.columns:
            df["scraped_at"] = pd.to_datetime(df["scraped_at"])
        if "last_updated" in df.columns:
            df["last_updated"] = pd.to_datetime(df["last_updated"])

        return df

    def _calculate_statistics(self, df: pd.DataFrame) -> MarketStatistics:
        """Calculate market statistics for a given DataFrame."""
        if len(df) == 0:
            return MarketStatistics(
                total_properties=0,
                average_price=0,
                median_price=0,
                min_price=0,
                max_price=0,
                std_dev=0,
                avg_rooms=0,
                avg_area=None,
                parking_percentage=0,
                garden_percentage=0,
                furnished_percentage=0,
                avg_price_per_sqm=None,
            )

        # Calculate price per sqm where area is available
        price_per_sqm = None
        if df["area_sqm"].notna().any():
            valid_area = df[df["area_sqm"].notna()]
            price_per_sqm = (valid_area["price"] / valid_area["area_sqm"]).mean()

        # Average area
        avg_area = df["area_sqm"].mean() if df["area_sqm"].notna().any() else None

        return MarketStatistics(
            total_properties=len(df),
            average_price=float(df["price"].mean()),
            median_price=float(df["price"].median()),
            min_price=float(df["price"].min()),
            max_price=float(df["price"].max()),
            std_dev=float(df["price"].std()),
            avg_rooms=float(df["rooms"].mean()),
            avg_area=float(avg_area) if avg_area is not None and not np.isnan(avg_area) else None,
            parking_percentage=float(df["has_parking"].mean() * 100),
            garden_percentage=float(df["has_garden"].mean() * 100),
            furnished_percentage=float(df["is_furnished"].mean() * 100),
            cities=df["city"].value_counts().to_dict(),
            property_types=df["property_type"].value_counts().to_dict(),
            avg_price_per_sqm=(
                float(price_per_sqm)
                if price_per_sqm is not None and not np.isnan(price_per_sqm)
                else None
            ),
        )

    def get_overall_statistics(self) -> MarketStatistics:
        """
        Calculate comprehensive market statistics.

        Returns:
            MarketStatistics with overall market metrics
        """
        return self._calculate_statistics(self.df)

    def get_country_statistics(self, country: str) -> MarketStatistics:
        """Get statistics for a specific country."""
        df = self.df[self.df["country"].str.lower() == country.lower()]
        return self._calculate_statistics(df)

    def get_region_statistics(self, region: str) -> MarketStatistics:
        """Get statistics for a specific region."""
        df = self.df[self.df["region"].str.lower() == region.lower()]
        return self._calculate_statistics(df)

    def get_price_trend(
        self,
        city: Optional[str] = None,
        region: Optional[str] = None,
        country: Optional[str] = None,
    ) -> PriceTrend:
        """
        Analyze price trends for overall market, specific city, region or country.

        Args:
            city: Optional city name to filter by
            region: Optional region name to filter by
            country: Optional country name to filter by

        Returns:
            PriceTrend with trend analysis
        """
        df = self.df
        if city:
            df = df[df["city"] == city]
        elif region:
            df = df[df["region"].str.lower() == region.lower()]
        elif country:
            df = df[df["country"].str.lower() == country.lower()]

        if len(df) < 5:
            return PriceTrend(
                direction=TrendDirection.INSUFFICIENT_DATA,
                change_percent=0.0,
                average_price=float(df["price"].mean()) if len(df) > 0 else 0.0,
                median_price=float(df["price"].median()) if len(df) > 0 else 0.0,
                price_range=(
                    (float(df["price"].min()), float(df["price"].max()))
                    if len(df) > 0
                    else (0.0, 0.0)
                ),
                sample_size=len(df),
                confidence="low",
            )

        # Calculate basic statistics
        avg_price = float(df["price"].mean())
        median_price = float(df["price"].median())

        # Simple trend detection (comparing first half vs second half)
        mid_point = len(df) // 2
        first_half_avg = float(df.iloc[:mid_point]["price"].mean())
        second_half_avg = float(df.iloc[mid_point:]["price"].mean())

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
            price_range=(float(df["price"].min()), float(df["price"].max())),
            sample_size=len(df),
            confidence=confidence,
        )

    def get_location_insights(self, city: str) -> Optional[LocationInsights]:
        """
        Get detailed insights for a specific location.

        Args:
            city: City name to analyze

        Returns:
            LocationInsights or None if city not found
        """
        city_df = self.df[self.df["city"] == city]

        if len(city_df) == 0:
            return None

        # Calculate price per sqm
        price_per_sqm = None
        if city_df["area_sqm"].notna().any():
            valid_area = city_df[city_df["area_sqm"].notna()]
            price_per_sqm = float((valid_area["price"] / valid_area["area_sqm"]).mean())

        # Most common room count
        most_common_rooms = None
        if len(city_df["rooms"]) > 0:
            most_common_rooms = (
                float(city_df["rooms"].mode().iloc[0]) if len(city_df["rooms"].mode()) > 0 else None
            )

        # Amenity availability
        amenity_availability = {
            "parking": float(city_df["has_parking"].mean() * 100),
            "garden": float(city_df["has_garden"].mean() * 100),
            "pool": float(city_df["has_pool"].mean() * 100),
            "furnished": float(city_df["is_furnished"].mean() * 100),
            "balcony": float(city_df["has_balcony"].mean() * 100),
            "elevator": float(city_df["has_elevator"].mean() * 100),
        }

        # Price comparison to overall market
        overall_avg = float(self.df["price"].mean())
        city_avg = float(city_df["price"].mean())

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
            median_price=float(city_df["price"].median()),
            avg_price_per_sqm=price_per_sqm,
            most_common_room_count=most_common_rooms,
            amenity_availability=amenity_availability,
            price_comparison=price_comparison,
            currency=_dominant_currency(city_df),
        )

    def get_city_price_indices(self, cities: Optional[List[str]] = None) -> pd.DataFrame:
        """Compute basic price indices per city."""
        df = self.df.copy()
        if cities:
            df = df[df["city"].isin(cities)]
        group = df.groupby("city")
        res = group.agg(
            avg_price=("price", "mean"), median_price=("price", "median"), count=("price", "count")
        ).reset_index()
        if df["area_sqm"].notna().any():
            res["avg_price_per_sqm"] = group.apply(
                lambda g: (g["price"] / g["area_sqm"]).dropna().mean()
            ).values
        else:
            res["avg_price_per_sqm"] = np.nan
        return res

    def get_historical_price_trends(
        self,
        interval: str = "month",  # "month", "quarter", "year"
        city: Optional[str] = None,
        months_back: int = 12,
    ) -> List[HistoricalPricePoint]:
        """
        Get historical price trends grouped by time interval.

        Args:
            interval: Grouping interval ("month", "quarter", "year")
            city: Optional city to filter by
            months_back: Number of months to look back

        Returns:
            List of HistoricalPricePoint objects sorted by date
        """
        df = self.df.copy()

        # Filter by city
        if city:
            df = df[df["city"] == city]

        # Ensure we have dates
        if "scraped_at" not in df.columns or df["scraped_at"].isnull().all():
            # Fallback to last_updated if scraped_at is missing
            if "last_updated" in df.columns and not df["last_updated"].isnull().all():
                df["date"] = df["last_updated"]
            else:
                return []
        else:
            df["date"] = df["scraped_at"].fillna(df["last_updated"])

        # Filter by date range
        start_date = datetime.now() - timedelta(days=months_back * 30)
        df = df[df["date"] >= start_date]

        if len(df) == 0:
            return []

        # Group by interval
        if interval == "month":
            df["period"] = df["date"].dt.to_period("M")
        elif interval == "quarter":
            df["period"] = df["date"].dt.to_period("Q")
        elif interval == "year":
            df["period"] = df["date"].dt.to_period("Y")
        else:
            raise ValueError(f"Unsupported interval: {interval}")

        # Aggregate
        results = []
        grouped = df.groupby("period")

        for period, group in grouped:
            avg_price = float(group["price"].mean())
            median_price = float(group["price"].median())

            avg_sqm_price = None
            if group["area_sqm"].notna().any():
                valid_area = group[group["area_sqm"].notna()]
                if not valid_area.empty:
                    avg_sqm_price = float((valid_area["price"] / valid_area["area_sqm"]).mean())

            # The currency of this period - the interface quotes the prices
            # in it, so the chart does not show dollars for zloty.
            period_currency = None
            if "currency" in group.columns:
                currencies = group["currency"].dropna()
                if not currencies.empty:
                    period_currency = str(currencies.mode().iloc[0])

            # Calculate start/end dates for the period
            p_start = period.start_time
            p_end = period.end_time

            results.append(
                HistoricalPricePoint(
                    period=str(period),
                    start_date=p_start,
                    end_date=p_end,
                    average_price=avg_price,
                    median_price=median_price,
                    volume=len(group),
                    avg_price_per_sqm=avg_sqm_price,
                    currency=period_currency,
                )
            )

        return sorted(results, key=lambda x: x.start_date)

    def filter_by_geo_radius(
        self, center_lat: float, center_lon: float, radius_km: float
    ) -> pd.DataFrame:
        """Filter properties within radius from a center point."""
        df = self.df.copy()
        if df[["lat", "lon"]].isnull().any().any():
            df = df.dropna(subset=["lat", "lon"])
        if len(df) == 0:
            return df
        lat1 = np.radians(center_lat)
        lon1 = np.radians(center_lon)
        lat2 = np.radians(df["lat"].astype(float))
        lon2 = np.radians(df["lon"].astype(float))
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        earth_radius_km = 6371.0
        dist = earth_radius_km * c
        return df[dist <= radius_km]

    def filter_properties(
        self,
        *,
        center_lat: Optional[float] = None,
        center_lon: Optional[float] = None,
        radius_km: Optional[float] = None,
        listing_type: Optional[str] = None,
        property_types: Optional[List[str]] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_price_per_sqm: Optional[float] = None,
        max_price_per_sqm: Optional[float] = None,
        min_rooms: Optional[float] = None,
        max_rooms: Optional[float] = None,
        must_have_parking: bool = False,
        must_have_elevator: bool = False,
        must_have_balcony: bool = False,
        must_be_furnished: bool = False,
        year_built_min: Optional[int] = None,
        year_built_max: Optional[int] = None,
        energy_ratings: Optional[List[str]] = None,
        require_coords: bool = True,
    ) -> pd.DataFrame:
        """Filter the insights DataFrame using geo and attribute constraints.

        Args:
            center_lat: Optional latitude for radius filtering.
            center_lon: Optional longitude for radius filtering.
            radius_km: Optional radius (km) for geo filtering.
            listing_type: Optional listing type filter ("rent" or "sale").
            property_types: Optional allowed property types (case-insensitive).
            min_price: Optional minimum price (inclusive).
            max_price: Optional maximum price (inclusive).
            min_price_per_sqm: Optional minimum price per sqm (inclusive).
            max_price_per_sqm: Optional maximum price per sqm (inclusive).
            min_rooms: Optional minimum rooms (inclusive).
            max_rooms: Optional maximum rooms (inclusive).
            must_have_parking: If True, keep only properties with parking.
            must_have_elevator: If True, keep only properties with elevator.
            must_have_balcony: If True, keep only properties with balcony.
            must_be_furnished: If True, keep only furnished properties.
            year_built_min: Optional minimum year built (inclusive).
            year_built_max: Optional maximum year built (inclusive).
            energy_ratings: Optional allowed energy ratings (case-insensitive).
            require_coords: If True, drop rows missing lat/lon before filtering.

        Returns:
            Filtered DataFrame (may be empty).
        """
        df = self.df.copy()

        if require_coords and len(df) > 0:
            df = df.dropna(subset=["lat", "lon"])

        if (
            center_lat is not None
            and center_lon is not None
            and radius_km is not None
            and len(df) > 0
        ):
            df = self.filter_by_geo_radius(float(center_lat), float(center_lon), float(radius_km))

        if len(df) == 0:
            return df

        if listing_type is not None:
            lt = listing_type.strip().lower()
            if lt and lt != "any" and "listing_type" in df.columns:
                df = df[df["listing_type"].astype(str).str.lower() == lt]

        if property_types:
            allow = {str(x).strip().lower() for x in property_types if str(x).strip()}
            if allow and "property_type" in df.columns:
                df = df[df["property_type"].astype(str).str.lower().isin(allow)]

        if "price" in df.columns:
            df["price"] = pd.to_numeric(df["price"], errors="coerce")
            if min_price is not None:
                df = df[df["price"].notna() & (df["price"] >= float(min_price))]
            if max_price is not None:
                df = df[df["price"].notna() & (df["price"] <= float(max_price))]

        if "rooms" in df.columns:
            df["rooms"] = pd.to_numeric(df["rooms"], errors="coerce")
            if min_rooms is not None:
                df = df[df["rooms"].notna() & (df["rooms"] >= float(min_rooms))]
            if max_rooms is not None:
                df = df[df["rooms"].notna() & (df["rooms"] <= float(max_rooms))]

        if "price_per_sqm" not in df.columns:
            df["price_per_sqm"] = np.nan

        if df["price_per_sqm"].isna().any() and "area_sqm" in df.columns and "price" in df.columns:
            area = pd.to_numeric(df["area_sqm"], errors="coerce")
            price = pd.to_numeric(df["price"], errors="coerce")
            computed = price / area
            computed = computed.replace([np.inf, -np.inf], np.nan)
            df.loc[df["price_per_sqm"].isna(), "price_per_sqm"] = computed.loc[
                df["price_per_sqm"].isna()
            ]

        df["price_per_sqm"] = pd.to_numeric(df["price_per_sqm"], errors="coerce")
        if min_price_per_sqm is not None:
            df = df[df["price_per_sqm"].notna() & (df["price_per_sqm"] >= float(min_price_per_sqm))]
        if max_price_per_sqm is not None:
            df = df[df["price_per_sqm"].notna() & (df["price_per_sqm"] <= float(max_price_per_sqm))]

        if must_have_parking and "has_parking" in df.columns:
            df = df[df["has_parking"].fillna(False).astype(bool)]
        if must_have_elevator and "has_elevator" in df.columns:
            df = df[df["has_elevator"].fillna(False).astype(bool)]
        if must_have_balcony and "has_balcony" in df.columns:
            df = df[df["has_balcony"].fillna(False).astype(bool)]
        if must_be_furnished and "is_furnished" in df.columns:
            df = df[df["is_furnished"].fillna(False).astype(bool)]

        if year_built_min is not None or year_built_max is not None:
            if "year_built" in df.columns:
                df["year_built"] = pd.to_numeric(df["year_built"], errors="coerce")
                if year_built_min is not None:
                    df = df[df["year_built"].notna() & (df["year_built"] >= int(year_built_min))]
                if year_built_max is not None:
                    df = df[df["year_built"].notna() & (df["year_built"] <= int(year_built_max))]

        if energy_ratings:
            allowed_ratings = {str(x).upper() for x in energy_ratings}
            if "energy_rating" in df.columns:
                df = df[df["energy_rating"].astype(str).str.upper().isin(allowed_ratings)]

        return df

    def get_monthly_price_index(
        self,
        city: Optional[str] = None,
        window: int = 3,
        detect_anomalies: bool = False,
        z_threshold: float = 2.0,
    ) -> pd.DataFrame:
        """Compute monthly average/median price, moving average and YoY change.

        Args:
            city: Optional city to filter.
            window: Moving average window (months).
            detect_anomalies: If True, compute z-score anomalies on avg_price.
            z_threshold: Absolute z-score threshold to mark anomalies.
        """
        df = self.df.copy()
        # Attach timestamps from original properties if missing in df
        if "scraped_at" not in df.columns:
            # Rebuild from properties list
            scraped = []
            for p in self.properties.properties:
                scraped.append(getattr(p, "scraped_at", None))
            # pad to length of df
            while len(scraped) < len(df):
                scraped.append(None)
            df["scraped_at"] = scraped[: len(df)]
        if "scraped_at" in df.columns and df["scraped_at"].isnull().all():
            # fallback to last_updated
            if "last_updated" in df.columns:
                df["scraped_at"] = df["last_updated"]
        # Drop rows without timestamps
        df = df.dropna(subset=["scraped_at"])
        # Convert to pandas datetime
        df["dt"] = pd.to_datetime(df["scraped_at"])
        if city:
            df = df[df["city"] == city]
        if len(df) == 0:
            return pd.DataFrame(columns=["month", "avg_price", "median_price", "count", "yoy_pct"])
        df["month"] = df["dt"].dt.to_period("M").dt.to_timestamp()
        grouped = (
            df.groupby("month", sort=True)
            .agg(
                avg_price=("price", "mean"),
                median_price=("price", "median"),
                count=("price", "count"),
            )
            .reset_index()
        )
        # YoY percent: compare same month last year using row-wise shift
        grouped = grouped.sort_values("month")
        prev = grouped["avg_price"].shift(12)
        with np.errstate(divide="ignore", invalid="ignore"):
            grouped["yoy_pct"] = ((grouped["avg_price"] - prev) / prev) * 100
        # Moving average
        grouped["avg_price_ma"] = grouped["avg_price"].rolling(window=window, min_periods=1).mean()
        # Anomalies via z-score
        if detect_anomalies and len(grouped) > 0:
            mu = float(np.nanmean(grouped["avg_price"]))
            sd = float(np.nanstd(grouped["avg_price"])) or 1.0
            grouped["zscore"] = (grouped["avg_price"] - mu) / sd
            grouped["anomaly"] = grouped["zscore"].abs() >= z_threshold
        return grouped

    def get_property_type_insights(self, property_type: str) -> Optional[PropertyTypeInsights]:
        """
        Get insights for a specific property type.

        Args:
            property_type: Property type to analyze

        Returns:
            PropertyTypeInsights or None if type not found
        """
        type_df = self.df[self.df["property_type"] == property_type]

        if len(type_df) == 0:
            return None

        # Average area
        avg_area = None
        if type_df["area_sqm"].notna().any():
            avg_area = float(type_df["area_sqm"].mean())

        # Popular locations (top 3)
        popular_locations = type_df["city"].value_counts().head(3).index.tolist()

        return PropertyTypeInsights(
            property_type=property_type,
            count=len(type_df),
            avg_price=float(type_df["price"].mean()),
            median_price=float(type_df["price"].median()),
            avg_rooms=float(type_df["rooms"].mean()),
            avg_area=avg_area,
            popular_locations=popular_locations,
        )

    def get_price_distribution(self, bins: int = 10) -> Dict[str, Any]:
        """
        Get price distribution histogram data.

        Args:
            bins: Number of bins for histogram

        Returns:
            Dictionary with histogram data
        """
        hist, bin_edges = np.histogram(self.df["price"], bins=bins)

        return {
            "counts": hist.tolist(),
            "bin_edges": bin_edges.tolist(),
            "bins": [
                f"${bin_edges[i]:.0f}-${bin_edges[i + 1]:.0f}" for i in range(len(bin_edges) - 1)
            ],
        }

    def get_amenity_impact_on_price(self) -> Dict[str, float]:
        """
        Analyze how amenities affect property prices.

        Returns:
            Dictionary mapping amenity to average price difference (%)
        """
        amenities = [
            "has_parking",
            "has_garden",
            "has_pool",
            "is_furnished",
            "has_balcony",
            "has_elevator",
        ]
        impact = {}

        for amenity in amenities:
            mask = self.df[amenity].fillna(False).astype(bool)
            with_amenity = self.df[mask]["price"].mean()
            without_amenity = self.df[~mask]["price"].mean()

            if pd.notna(with_amenity) and pd.notna(without_amenity) and without_amenity > 0:
                percent_diff = float(((with_amenity - without_amenity) / without_amenity) * 100)
                impact[amenity.replace("has_", "").replace("is_", "")] = percent_diff

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
        price_norm = (
            (df_with_score["price"].max() - df_with_score["price"])
            / (df_with_score["price"].max() - df_with_score["price"].min())
            if df_with_score["price"].max() != df_with_score["price"].min()
            else 0.5
        )

        # Normalize rooms (higher is better)
        rooms_norm = (
            (df_with_score["rooms"] - df_with_score["rooms"].min())
            / (df_with_score["rooms"].max() - df_with_score["rooms"].min())
            if df_with_score["rooms"].max() != df_with_score["rooms"].min()
            else 0.5
        )

        # Count amenities
        amenity_cols = [
            "has_parking",
            "has_garden",
            "has_pool",
            "is_furnished",
            "has_balcony",
            "has_elevator",
        ]
        df_with_score["amenity_count"] = df_with_score[amenity_cols].sum(axis=1)
        amenity_norm = df_with_score["amenity_count"] / 6  # 6 total amenities

        # Calculate value score (weighted combination)
        df_with_score["value_score"] = (
            price_norm * 0.4  # 40% weight on low price
            + rooms_norm * 0.3  # 30% weight on rooms
            + amenity_norm * 0.3  # 30% weight on amenities
        )

        # Get top properties
        top_properties = df_with_score.nlargest(top_n, "value_score")

        records = top_properties[
            ["city", "price", "rooms", "property_type", "amenity_count", "value_score"]
        ].to_dict("records")
        if isinstance(records, list):
            return [r for r in records if isinstance(r, dict)]
        return []

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
            return {"error": "One or both cities not found", "city1": city1, "city2": city2}

        return {
            "city1": insights1.dict(),
            "city2": insights2.dict(),
            "price_difference": insights1.avg_price - insights2.avg_price,
            "price_difference_percent": (
                (insights1.avg_price - insights2.avg_price) / insights2.avg_price
            )
            * 100,
            "cheaper_city": city1 if insights1.avg_price < insights2.avg_price else city2,
            "more_properties": (
                city1 if insights1.property_count > insights2.property_count else city2
            ),
        }

    def get_cities_yoy(self, cities: Optional[List[str]] = None) -> pd.DataFrame:
        df = self.df.copy()
        if cities:
            df = df[df["city"].isin(cities)]
        if "scraped_at" not in df.columns:
            scraped = []
            for p in self.properties.properties:
                scraped.append(getattr(p, "scraped_at", None))
            while len(scraped) < len(df):
                scraped.append(None)
            df["scraped_at"] = scraped[: len(df)]
        df = df.dropna(subset=["scraped_at"])
        if len(df) == 0:
            return pd.DataFrame(columns=["city", "month", "avg_price", "yoy_pct", "count"])
        df["dt"] = pd.to_datetime(df["scraped_at"])
        df["month"] = df["dt"].dt.to_period("M").dt.to_timestamp()
        grouped = (
            df.groupby(["city", "month"])
            .agg(avg_price=("price", "mean"), count=("price", "count"))
            .reset_index()
            .sort_values(["city", "month"])
        )
        grouped["yoy_pct"] = None
        try:
            grouped["yoy_pct"] = grouped.groupby("city")["avg_price"].transform(
                lambda s: (s - s.shift(12)) / s.shift(12) * 100
            )
        except Exception:
            pass
        latest = grouped.groupby("city").tail(1)
        return latest[["city", "month", "avg_price", "yoy_pct", "count"]]

    def get_country_indices(self, countries: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Get monthly price indices and YoY change for countries.

        Args:
            countries: Optional list of countries to filter/include.

        Returns:
            DataFrame with country, month, avg_price, yoy_pct, count.
        """
        df = self.df.copy()
        if countries:
            countries_lower = [c.lower() for c in countries]
            df = df[df["country"].str.lower().isin(countries_lower)]

        if "scraped_at" not in df.columns:
            scraped = []
            for p in self.properties.properties:
                scraped.append(getattr(p, "scraped_at", None))
            while len(scraped) < len(df):
                scraped.append(None)
            df["scraped_at"] = scraped[: len(df)]

        df = df.dropna(subset=["scraped_at"])
        if len(df) == 0:
            return pd.DataFrame(columns=["country", "month", "avg_price", "yoy_pct", "count"])

        df["dt"] = pd.to_datetime(df["scraped_at"])
        df["month"] = df["dt"].dt.to_period("M").dt.to_timestamp()

        grouped = (
            df.groupby(["country", "month"])
            .agg(avg_price=("price", "mean"), count=("price", "count"))
            .reset_index()
            .sort_values(["country", "month"])
        )

        grouped["yoy_pct"] = None
        try:
            grouped["yoy_pct"] = grouped.groupby("country")["avg_price"].transform(
                lambda s: (s - s.shift(12)) / s.shift(12) * 100
            )
        except Exception:
            pass

        latest = grouped.groupby("country").tail(1)
        return latest[["country", "month", "avg_price", "yoy_pct", "count"]]
