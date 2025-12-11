"""
Export functionality for property data.

Supports exporting properties to multiple formats:
- CSV: Simple spreadsheet format
- Excel: Formatted spreadsheet with multiple sheets
- JSON: Structured data format
- Markdown: Human-readable report format
"""

from enum import Enum
from typing import List, Optional, BinaryIO
from io import BytesIO, StringIO
import json
from datetime import datetime
import pandas as pd

from data.schemas import Property, PropertyCollection
from analytics import MarketInsights


class ExportFormat(str, Enum):
    """Supported export formats."""
    CSV = "csv"
    EXCEL = "xlsx"
    JSON = "json"
    MARKDOWN = "md"


class PropertyExporter:
    """
    Exporter for property data to various formats.

    Provides methods to export property collections to CSV, Excel, JSON,
    and Markdown formats with optional filtering and customization.
    """

    def __init__(self, properties: PropertyCollection):
        """
        Initialize exporter with property data.

        Args:
            properties: Collection of properties to export
        """
        self.properties = properties
        self.df = self._to_dataframe()

    def _to_dataframe(self) -> pd.DataFrame:
        """Convert properties to pandas DataFrame."""
        data = []
        for prop in self.properties.properties:
            prop_dict = prop.dict()
            # Convert enum to string
            if 'property_type' in prop_dict:
                prop_type = prop_dict['property_type']
                prop_dict['property_type'] = prop_type.value if hasattr(prop_type, 'value') else str(prop_type)
            if 'negotiation_rate' in prop_dict and prop_dict['negotiation_rate']:
                neg_rate = prop_dict['negotiation_rate']
                prop_dict['negotiation_rate'] = neg_rate.value if hasattr(neg_rate, 'value') else str(neg_rate)
            data.append(prop_dict)
        return pd.DataFrame(data)

    def export_to_csv(
        self,
        columns: Optional[List[str]] = None,
        include_header: bool = True
    ) -> str:
        """
        Export properties to CSV format.

        Args:
            columns: Optional list of columns to include
            include_header: Whether to include header row

        Returns:
            CSV string
        """
        df = self.df[columns] if columns else self.df

        return df.to_csv(index=False, header=include_header)

    def export_to_excel(
        self,
        include_summary: bool = True,
        include_statistics: bool = True
    ) -> BytesIO:
        """
        Export properties to Excel format with multiple sheets.

        Args:
            include_summary: Include summary sheet with statistics
            include_statistics: Include detailed statistics sheet

        Returns:
            BytesIO object containing Excel file
        """
        output = BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Main properties sheet
            self.df.to_excel(writer, sheet_name='Properties', index=False)

            if include_summary:
                # Summary sheet
                summary_data = {
                    'Metric': [
                        'Total Properties',
                        'Average Price',
                        'Median Price',
                        'Min Price',
                        'Max Price',
                        'Average Rooms',
                        'Properties with Parking',
                        'Properties with Garden',
                        'Furnished Properties'
                    ],
                    'Value': [
                        len(self.df),
                        f"${self.df['price'].mean():.2f}",
                        f"${self.df['price'].median():.2f}",
                        f"${self.df['price'].min():.2f}",
                        f"${self.df['price'].max():.2f}",
                        f"{self.df['rooms'].mean():.1f}",
                        f"{self.df['has_parking'].sum()} ({self.df['has_parking'].mean()*100:.1f}%)",
                        f"{self.df['has_garden'].sum()} ({self.df['has_garden'].mean()*100:.1f}%)",
                        f"{self.df['is_furnished'].sum()} ({self.df['is_furnished'].mean()*100:.1f}%)"
                    ]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)

            if include_statistics:
                # Statistics by city
                city_stats = self.df.groupby('city').agg({
                    'price': ['count', 'mean', 'median', 'min', 'max'],
                    'rooms': 'mean',
                    'has_parking': 'mean'
                }).round(2)
                city_stats.to_excel(writer, sheet_name='By City')

                # Statistics by property type
                type_stats = self.df.groupby('property_type').agg({
                    'price': ['count', 'mean', 'median'],
                    'rooms': 'mean',
                    'area_sqm': 'mean'
                }).round(2)
                type_stats.to_excel(writer, sheet_name='By Type')

        output.seek(0)
        return output

    def export_to_json(
        self,
        pretty: bool = True,
        include_metadata: bool = True
    ) -> str:
        """
        Export properties to JSON format.

        Args:
            pretty: Use pretty formatting with indentation
            include_metadata: Include export metadata

        Returns:
            JSON string
        """
        data = {
            'properties': [prop.dict() for prop in self.properties.properties]
        }

        if include_metadata:
            data['metadata'] = {
                'total_count': self.properties.total_count,
                'exported_at': datetime.now().isoformat(),
                'export_format': 'json'
            }

        indent = 2 if pretty else None
        return json.dumps(data, indent=indent, default=str)

    def export_to_markdown(
        self,
        include_summary: bool = True,
        max_properties: Optional[int] = None
    ) -> str:
        """
        Export properties to Markdown report format.

        Args:
            include_summary: Include summary statistics
            max_properties: Maximum number of properties to include (None = all)

        Returns:
            Markdown formatted string
        """
        lines = []

        # Header
        lines.append("# Property Listing Report")
        lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"\nTotal Properties: {len(self.properties.properties)}")
        lines.append("\n---\n")

        # Summary statistics
        if include_summary:
            lines.append("## Summary Statistics\n")
            lines.append(f"- **Average Price**: ${self.df['price'].mean():.2f}")
            lines.append(f"- **Median Price**: ${self.df['price'].median():.2f}")
            lines.append(f"- **Price Range**: ${self.df['price'].min():.2f} - ${self.df['price'].max():.2f}")
            lines.append(f"- **Average Rooms**: {self.df['rooms'].mean():.1f}")
            lines.append(f"- **Properties with Parking**: {self.df['has_parking'].sum()} ({self.df['has_parking'].mean()*100:.1f}%)")
            lines.append(f"- **Properties with Garden**: {self.df['has_garden'].sum()} ({self.df['has_garden'].mean()*100:.1f}%)\n")

            # By city
            lines.append("### By City\n")
            city_counts = self.df['city'].value_counts()
            for city, count in city_counts.items():
                city_avg = self.df[self.df['city'] == city]['price'].mean()
                lines.append(f"- **{city}**: {count} properties (avg: ${city_avg:.2f})")
            lines.append("\n---\n")

        # Properties
        lines.append("## Property Listings\n")

        properties_to_show = self.properties.properties[:max_properties] if max_properties else self.properties.properties

        for i, prop in enumerate(properties_to_show, 1):
            lines.append(f"### {i}. Property in {prop.city}")
            if prop.title:
                lines.append(f"**{prop.title}**\n")

            lines.append(f"- **Price**: ${prop.price}/month")
            lines.append(f"- **Type**: {prop.property_type.value if hasattr(prop.property_type, 'value') else str(prop.property_type)}")
            lines.append(f"- **Rooms**: {int(prop.rooms)} bedrooms, {int(prop.bathrooms)} bathrooms")

            if prop.area_sqm:
                lines.append(f"- **Area**: {prop.area_sqm} sqm")

            # Amenities
            amenities = []
            if prop.has_parking:
                amenities.append("Parking")
            if prop.has_garden:
                amenities.append("Garden")
            if prop.has_pool:
                amenities.append("Pool")
            if prop.is_furnished:
                amenities.append("Furnished")
            if prop.has_balcony:
                amenities.append("Balcony")
            if prop.has_elevator:
                amenities.append("Elevator")

            if amenities:
                lines.append(f"- **Amenities**: {', '.join(amenities)}")

            if prop.description:
                lines.append(f"\n{prop.description}")

            if prop.source_url:
                lines.append(f"\n[View Listing]({prop.source_url})")

            lines.append("\n---\n")

        if max_properties and len(self.properties.properties) > max_properties:
            lines.append(f"\n*Showing {max_properties} of {len(self.properties.properties)} properties*\n")

        return '\n'.join(lines)

    def export(
        self,
        format: ExportFormat,
        **kwargs
    ) -> str | BytesIO:
        """
        Export properties to specified format.

        Args:
            format: Export format (CSV, Excel, JSON, Markdown)
            **kwargs: Format-specific options

        Returns:
            Exported data (string or BytesIO depending on format)
        """
        if format == ExportFormat.CSV:
            return self.export_to_csv(**kwargs)
        elif format == ExportFormat.EXCEL:
            return self.export_to_excel(**kwargs)
        elif format == ExportFormat.JSON:
            return self.export_to_json(**kwargs)
        elif format == ExportFormat.MARKDOWN:
            return self.export_to_markdown(**kwargs)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def get_filename(self, format: ExportFormat, prefix: str = "properties") -> str:
        """
        Generate filename for export.

        Args:
            format: Export format
            prefix: Filename prefix

        Returns:
            Filename with timestamp and extension
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = format.value
        return f"{prefix}_{timestamp}.{extension}"


class InsightsExporter:
    def __init__(self, insights: MarketInsights):
        self.insights = insights

    def export_city_indices_csv(self, cities: List[str] | None = None) -> str:
        df = self.insights.get_city_price_indices(cities)
        return df.to_csv(index=False)

    def export_city_indices_json(self, cities: List[str] | None = None, pretty: bool = True) -> str:
        df = self.insights.get_city_price_indices(cities)
        obj = {"indices": df.to_dict(orient="records")}
        return json.dumps(obj, indent=2 if pretty else None)

    def export_city_indices_markdown(self, cities: List[str] | None = None) -> str:
        df = self.insights.get_city_price_indices(cities)
        buf = StringIO()
        buf.write("# City Price Indices\n\n")
        buf.write(df.to_markdown(index=False))
        return buf.getvalue()

    def export_city_indices_excel(self, cities: List[str] | None = None) -> BytesIO:
        df = self.insights.get_city_price_indices(cities)
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="CityIndices", index=False)
        output.seek(0)
        return output

    def export_monthly_index_csv(self, city: str | None = None) -> str:
        df = self.insights.get_monthly_price_index(city)
        return df.to_csv(index=False)

    def export_monthly_index_json(self, city: str | None = None, pretty: bool = True) -> str:
        df = self.insights.get_monthly_price_index(city)
        df = df.copy()
        if 'month' in df.columns:
            df['month'] = df['month'].astype(str)
        obj = {"monthly_index": df.to_dict(orient="records")}
        return json.dumps(obj, indent=2 if pretty else None)

    def export_monthly_index_markdown(self, city: str | None = None) -> str:
        df = self.insights.get_monthly_price_index(city)
        buf = StringIO()
        title = f"# Monthly Price Index{f' — {city}' if city else ''}\n\n"
        buf.write(title)
        buf.write(df.to_markdown(index=False))
        return buf.getvalue()

    def export_monthly_index_excel(self, city: str | None = None) -> BytesIO:
        df = self.insights.get_monthly_price_index(city)
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="MonthlyIndex", index=False)
        output.seek(0)
        return output

    def generate_digest_markdown(self, cities: List[str] | None = None) -> str:
        city_idx = self.insights.get_city_price_indices(cities)
        yoy_latest = self.insights.get_cities_yoy(cities)
        top_up = yoy_latest.sort_values('yoy_pct', ascending=False).head(5)
        top_down = yoy_latest.sort_values('yoy_pct', ascending=True).head(5)
        buf = StringIO()
        buf.write("# Expert Digest\n\n")
        buf.write("## City Price Indices\n\n")
        buf.write(city_idx.to_markdown(index=False))
        buf.write("\n\n## YoY — Top Gainers\n\n")
        buf.write(top_up.to_markdown(index=False))
        buf.write("\n\n## YoY — Top Decliners\n\n")
        buf.write(top_down.to_markdown(index=False))
        return buf.getvalue()
