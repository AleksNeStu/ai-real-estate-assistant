"""
Pydantic data models for property data validation and type safety.

This module provides comprehensive schemas for property listings with validation,
ensuring data quality and consistency across the application.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator, field_validator
import pandas as pd


class PropertyType(str, Enum):
    """Enumeration of property types."""
    APARTMENT = "apartment"
    HOUSE = "house"
    STUDIO = "studio"
    LOFT = "loft"
    TOWNHOUSE = "townhouse"
    OTHER = "other"


class NegotiationRate(str, Enum):
    """Enumeration of negotiation rates."""
    HIGH = "high"
    MIDDLE = "middle"
    LOW = "low"


class Property(BaseModel):
    """
    Comprehensive property data model with validation.

    This model represents a real estate property with all relevant details
    for search, filtering, and display in the application.
    """

    # Core Identification
    id: Optional[str] = Field(None, description="Unique property identifier")
    title: Optional[str] = Field(None, min_length=5, description="Property title")
    description: Optional[str] = Field(None, description="Detailed property description")

    # Location Information
    city: str = Field(..., description="City where property is located")
    neighborhood: Optional[str] = Field(None, description="Neighborhood or district")
    address: Optional[str] = Field(None, description="Full street address")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude coordinate")

    # Property Classification
    property_type: PropertyType = Field(
        default=PropertyType.APARTMENT,
        description="Type of property"
    )

    # Physical Characteristics
    rooms: float = Field(..., ge=0, le=50, description="Number of rooms")
    bathrooms: float = Field(default=1.0, ge=0, le=20, description="Number of bathrooms")
    area_sqm: Optional[float] = Field(None, gt=0, description="Area in square meters")
    floor: Optional[float] = Field(None, description="Floor number")
    total_floors: Optional[float] = Field(None, description="Total floors in building")

    # Financial Information
    price: float = Field(..., gt=0, description="Monthly rental price")
    price_media: Optional[float] = Field(None, ge=0, description="Estimated utility costs")
    price_delta: Optional[float] = Field(None, description="Price variation/negotiation room")
    deposit: Optional[float] = Field(None, ge=0, description="Security deposit amount")
    negotiation_rate: Optional[NegotiationRate] = Field(
        None,
        description="Level of price negotiability"
    )

    # Amenities (Boolean Features)
    has_parking: bool = Field(default=False, description="Has parking space")
    has_garden: bool = Field(default=False, description="Has garden or yard")
    has_pool: bool = Field(default=False, description="Has swimming pool")
    has_garage: bool = Field(default=False, description="Has garage")
    has_bike_room: bool = Field(default=False, description="Has bike storage room")
    is_furnished: bool = Field(default=False, description="Is furnished")
    pets_allowed: bool = Field(default=False, description="Pets are allowed")
    has_balcony: bool = Field(default=False, description="Has balcony or terrace")
    has_elevator: bool = Field(default=False, description="Building has elevator")

    # Proximity Information (in meters)
    distance_to_school: Optional[float] = Field(None, ge=0, description="Distance to nearest school (m)")
    distance_to_clinic: Optional[float] = Field(None, ge=0, description="Distance to nearest clinic (m)")
    distance_to_restaurant: Optional[float] = Field(None, ge=0, description="Distance to nearest restaurant (m)")
    distance_to_transport: Optional[float] = Field(None, ge=0, description="Distance to public transport (m)")
    distance_to_shopping: Optional[float] = Field(None, ge=0, description="Distance to shopping center (m)")

    # Owner/Contact Information
    owner_name: Optional[str] = Field(None, description="Property owner name")
    owner_phone: Optional[str] = Field(None, description="Owner contact phone")
    owner_email: Optional[str] = Field(None, description="Owner contact email")

    # Metadata
    source_url: Optional[str] = Field(None, description="Source URL of the listing")
    source_platform: Optional[str] = Field(None, description="Platform where listing originated")
    scraped_at: Optional[datetime] = Field(
        default_factory=datetime.now,
        description="When data was scraped"
    )
    last_updated: Optional[datetime] = Field(
        default_factory=datetime.now,
        description="Last update timestamp"
    )

    # Computed/Derived Fields
    price_per_sqm: Optional[float] = Field(None, description="Price per square meter")
    total_monthly_cost: Optional[float] = Field(None, description="Total monthly cost (rent + utilities)")

    class Config:
        """Pydantic model configuration."""
        use_enum_values = True
        validate_assignment = True
        extra = "allow"  # Allow additional fields for flexibility

    @field_validator('rooms', 'bathrooms')
    @classmethod
    def validate_positive(cls, v: float, info) -> float:
        """Ensure rooms and bathrooms are positive."""
        if v < 0:
            raise ValueError(f"{info.field_name} must be positive")
        return v

    @field_validator('price')
    @classmethod
    def validate_price_reasonable(cls, v: float) -> float:
        """Ensure price is within reasonable bounds."""
        if v > 100000:
            raise ValueError("Price suspiciously high (>100,000)")
        if v < 50:
            raise ValueError("Price suspiciously low (<50)")
        return v

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization processing to compute derived fields."""
        # Calculate price per square meter
        if self.area_sqm and self.area_sqm > 0:
            self.price_per_sqm = round(self.price / self.area_sqm, 2)

        # Calculate total monthly cost
        if self.price_media:
            self.total_monthly_cost = round(self.price + self.price_media, 2)
        else:
            self.total_monthly_cost = self.price

    def to_dict(self) -> Dict[str, Any]:
        """Convert property to dictionary representation."""
        return self.model_dump(exclude_none=True)

    def to_search_text(self) -> str:
        """
        Convert property to text representation for semantic search.

        Returns:
            Comprehensive text description for vector embedding.
        """
        amenities = []
        if self.has_parking:
            amenities.append("parking")
        if self.has_garden:
            amenities.append("garden")
        if self.has_pool:
            amenities.append("pool")
        if self.has_garage:
            amenities.append("garage")
        if self.has_bike_room:
            amenities.append("bike room")
        if self.is_furnished:
            amenities.append("furnished")
        if self.pets_allowed:
            amenities.append("pets allowed")
        if self.has_balcony:
            amenities.append("balcony")
        if self.has_elevator:
            amenities.append("elevator")

        amenities_str = ", ".join(amenities) if amenities else "no special amenities"

        proximity_info = []
        if self.distance_to_school:
            proximity_info.append(f"school within {int(self.distance_to_school)}m")
        if self.distance_to_clinic:
            proximity_info.append(f"clinic within {int(self.distance_to_clinic)}m")
        if self.distance_to_transport:
            proximity_info.append(f"public transport within {int(self.distance_to_transport)}m")

        proximity_str = ", ".join(proximity_info) if proximity_info else "proximity information not available"

        text_parts = [
            f"Property in {self.city}",
        ]

        if self.neighborhood:
            text_parts.append(f", {self.neighborhood} neighborhood")

        # Handle property_type as either enum or string (Pydantic might convert to string)
        prop_type_str = self.property_type.value if hasattr(self.property_type, 'value') else str(self.property_type)

        rooms_str = str(int(self.rooms)) if (self.rooms is not None and not pd.isna(self.rooms)) else "unknown"
        baths_str = str(int(self.bathrooms)) if (self.bathrooms is not None and not pd.isna(self.bathrooms)) else "unknown"

        text_parts.extend([
            f". {prop_type_str.title()} with {rooms_str} rooms and {baths_str} bathrooms",
            f". Monthly rent: ${self.price}"
        ])

        if self.area_sqm:
            text_parts.append(f", area: {self.area_sqm} square meters")

        if self.floor is not None and not pd.isna(self.floor):
            floor_str = str(int(self.floor))
            tf = self.total_floors if (self.total_floors is not None and not pd.isna(self.total_floors)) else None
            if tf is not None:
                text_parts.append(f", floor {floor_str} of {int(tf)}")
            else:
                text_parts.append(f", floor {floor_str}")

        text_parts.extend([
            f". Amenities: {amenities_str}",
            f". {proximity_str}",
        ])

        if self.description:
            text_parts.append(f". Description: {self.description}")

        return "".join(text_parts)


class PropertyCollection(BaseModel):
    """Collection of properties with metadata."""
    properties: List[Property]
    total_count: int
    source: Optional[str] = None
    loaded_at: datetime = Field(default_factory=datetime.now)

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, source: Optional[str] = None) -> "PropertyCollection":
        """
        Create PropertyCollection from pandas DataFrame.

        Args:
            df: DataFrame containing property data
            source: Optional source identifier

        Returns:
            PropertyCollection instance with validated properties
        """
        properties = []

        for idx, row in df.iterrows():
            try:
                # Convert row to dict and create Property
                row_dict = row.to_dict()

                # Add ID if not present
                if 'id' not in row_dict or pd.isna(row_dict.get('id')):
                    row_dict['id'] = f"prop_{idx}"

                # Create Property instance (will validate automatically)
                prop = Property(**row_dict)
                properties.append(prop)

            except Exception as e:
                print(f"Warning: Skipping row {idx} due to validation error: {e}")
                continue

        return cls(
            properties=properties,
            total_count=len(properties),
            source=source
        )

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert PropertyCollection to pandas DataFrame.

        Returns:
            DataFrame representation of properties
        """
        return pd.DataFrame([prop.to_dict() for prop in self.properties])

    def filter_by_criteria(
        self,
        city: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rooms: Optional[float] = None,
        max_rooms: Optional[float] = None,
        has_parking: Optional[bool] = None,
        has_garden: Optional[bool] = None,
        property_type: Optional[PropertyType] = None
    ) -> "PropertyCollection":
        """
        Filter properties by various criteria.

        Args:
            city: Filter by city name
            min_price: Minimum price
            max_price: Maximum price
            min_rooms: Minimum number of rooms
            max_rooms: Maximum number of rooms
            has_parking: Filter by parking availability
            has_garden: Filter by garden availability
            property_type: Filter by property type

        Returns:
            Filtered PropertyCollection
        """
        filtered = self.properties

        if city:
            filtered = [p for p in filtered if p.city.lower() == city.lower()]

        if min_price is not None:
            filtered = [p for p in filtered if p.price >= min_price]

        if max_price is not None:
            filtered = [p for p in filtered if p.price <= max_price]

        if min_rooms is not None:
            filtered = [p for p in filtered if p.rooms >= min_rooms]

        if max_rooms is not None:
            filtered = [p for p in filtered if p.rooms <= max_rooms]

        if has_parking is not None:
            filtered = [p for p in filtered if p.has_parking == has_parking]

        if has_garden is not None:
            filtered = [p for p in filtered if p.has_garden == has_garden]

        if property_type is not None:
            filtered = [p for p in filtered if p.property_type == property_type]

        return PropertyCollection(
            properties=filtered,
            total_count=len(filtered),
            source=self.source
        )


class SearchCriteria(BaseModel):
    """User search criteria for property search."""
    query: str = Field(..., description="Natural language search query")
    city: Optional[str] = None
    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)
    min_rooms: Optional[float] = Field(None, ge=0)
    max_rooms: Optional[float] = Field(None, ge=0)
    property_type: Optional[PropertyType] = None
    required_amenities: List[str] = Field(default_factory=list)
    max_results: int = Field(default=10, ge=1, le=100)

    @field_validator('max_price')
    @classmethod
    def validate_price_range(cls, v: Optional[float], info) -> Optional[float]:
        """Ensure max_price is greater than min_price if both are set."""
        min_price = info.data.get('min_price')
        if v is not None and min_price is not None and v < min_price:
            raise ValueError("max_price must be greater than min_price")
        return v


class UserPreferences(BaseModel):
    """Stored user preferences for personalized recommendations."""
    user_id: str
    preferred_cities: List[str] = Field(default_factory=list)
    budget_range: tuple[float, float] = Field(default=(0, 10000))
    preferred_rooms: List[float] = Field(default_factory=list)
    must_have_amenities: List[str] = Field(default_factory=list)
    preferred_neighborhoods: List[str] = Field(default_factory=list)
    saved_searches: List[SearchCriteria] = Field(default_factory=list)
    viewed_properties: List[str] = Field(default_factory=list)
    favorited_properties: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
