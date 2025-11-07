"""
Tests for property export functionality.
"""

import pytest
import json
from io import BytesIO
import pandas as pd
from utils import PropertyExporter, ExportFormat
from data.schemas import Property, PropertyCollection, PropertyType


@pytest.fixture
def export_properties():
    """Create sample properties for export testing."""
    properties = [
        Property(
            id="e1",
            city="Krakow",
            rooms=2,
            bathrooms=1,
            price=850,
            area_sqm=52,
            has_parking=True,
            has_garden=False,
            property_type=PropertyType.APARTMENT,
            title="Nice Apartment in Center"
        ),
        Property(
            id="e2",
            city="Warsaw",
            rooms=3,
            bathrooms=2,
            price=1350,
            area_sqm=75,
            has_parking=True,
            has_garden=True,
            property_type=PropertyType.HOUSE,
            title="Spacious House"
        ),
        Property(
            id="e3",
            city="Krakow",
            rooms=1,
            bathrooms=1,
            price=600,
            area_sqm=30,
            has_parking=False,
            has_garden=False,
            property_type=PropertyType.STUDIO,
            title="Cozy Studio"
        ),
    ]
    return PropertyCollection(properties=properties, total_count=3)


@pytest.fixture
def exporter(export_properties):
    """Create PropertyExporter instance."""
    return PropertyExporter(export_properties)


class TestPropertyExporter:
    """Tests for PropertyExporter class."""

    def test_initialization(self, export_properties):
        """Test exporter initialization."""
        exporter = PropertyExporter(export_properties)
        assert exporter is not None
        assert len(exporter.df) == 3

    def test_dataframe_conversion(self, exporter):
        """Test properties converted to DataFrame."""
        df = exporter.df
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert 'city' in df.columns
        assert 'price' in df.columns


class TestCSVExport:
    """Tests for CSV export functionality."""

    def test_export_to_csv_basic(self, exporter):
        """Test basic CSV export."""
        csv_data = exporter.export_to_csv()

        assert isinstance(csv_data, str)
        assert len(csv_data) > 0
        # Should contain header
        assert 'city' in csv_data
        assert 'price' in csv_data
        # Should contain data
        assert 'Krakow' in csv_data
        assert 'Warsaw' in csv_data

    def test_export_to_csv_no_header(self, exporter):
        """Test CSV export without header."""
        csv_data = exporter.export_to_csv(include_header=False)

        assert isinstance(csv_data, str)
        # Should NOT have header row
        lines = csv_data.strip().split('\n')
        # First line should be data, not headers
        assert 'city' not in lines[0]

    def test_export_to_csv_specific_columns(self, exporter):
        """Test CSV export with specific columns."""
        csv_data = exporter.export_to_csv(columns=['city', 'price', 'rooms'])

        assert 'city' in csv_data
        assert 'price' in csv_data
        assert 'rooms' in csv_data

    def test_csv_parseable(self, exporter):
        """Test CSV output is valid and parseable."""
        csv_data = exporter.export_to_csv()

        # Should be parseable by pandas
        from io import StringIO
        df = pd.read_csv(StringIO(csv_data))
        assert len(df) == 3
        assert 'city' in df.columns


class TestExcelExport:
    """Tests for Excel export functionality."""

    def test_export_to_excel_basic(self, exporter):
        """Test basic Excel export."""
        excel_data = exporter.export_to_excel()

        assert isinstance(excel_data, BytesIO)
        assert excel_data.getbuffer().nbytes > 0  # File has content

    def test_export_to_excel_with_summary(self, exporter):
        """Test Excel export with summary sheet."""
        excel_data = exporter.export_to_excel(
            include_summary=True,
            include_statistics=True
        )

        assert isinstance(excel_data, BytesIO)
        # Should have content
        assert excel_data.getbuffer().nbytes > 0

    def test_export_to_excel_without_summary(self, exporter):
        """Test Excel export without summary."""
        excel_data = exporter.export_to_excel(
            include_summary=False,
            include_statistics=False
        )

        assert isinstance(excel_data, BytesIO)

    def test_excel_readable(self, exporter):
        """Test Excel file is valid and readable."""
        excel_data = exporter.export_to_excel()

        # Should be readable by pandas
        df = pd.read_excel(excel_data, sheet_name='Properties')
        assert len(df) == 3
        assert 'city' in df.columns


class TestJSONExport:
    """Tests for JSON export functionality."""

    def test_export_to_json_basic(self, exporter):
        """Test basic JSON export."""
        json_data = exporter.export_to_json()

        assert isinstance(json_data, str)
        assert len(json_data) > 0

        # Should be valid JSON
        parsed = json.loads(json_data)
        assert 'properties' in parsed
        assert len(parsed['properties']) == 3

    def test_export_to_json_with_metadata(self, exporter):
        """Test JSON export with metadata."""
        json_data = exporter.export_to_json(include_metadata=True)

        parsed = json.loads(json_data)
        assert 'metadata' in parsed
        assert 'total_count' in parsed['metadata']
        assert 'exported_at' in parsed['metadata']
        assert parsed['metadata']['total_count'] == 3

    def test_export_to_json_without_metadata(self, exporter):
        """Test JSON export without metadata."""
        json_data = exporter.export_to_json(include_metadata=False)

        parsed = json.loads(json_data)
        assert 'metadata' not in parsed
        assert 'properties' in parsed

    def test_export_to_json_pretty(self, exporter):
        """Test JSON export with pretty formatting."""
        json_data = exporter.export_to_json(pretty=True)

        # Pretty printed JSON should have newlines
        assert '\n' in json_data
        assert '  ' in json_data  # Indentation

    def test_export_to_json_compact(self, exporter):
        """Test JSON export in compact format."""
        json_data = exporter.export_to_json(pretty=False)

        # Compact JSON should be on one line (mostly)
        assert json_data.count('\n') < 5

    def test_json_valid_structure(self, exporter):
        """Test JSON has correct structure."""
        json_data = exporter.export_to_json()
        parsed = json.loads(json_data)

        # Check first property has expected fields
        first_prop = parsed['properties'][0]
        assert 'city' in first_prop
        assert 'price' in first_prop
        assert 'rooms' in first_prop
        assert 'property_type' in first_prop


class TestMarkdownExport:
    """Tests for Markdown export functionality."""

    def test_export_to_markdown_basic(self, exporter):
        """Test basic Markdown export."""
        md_data = exporter.export_to_markdown()

        assert isinstance(md_data, str)
        assert len(md_data) > 0
        # Should have headers
        assert '# Property Listing Report' in md_data
        assert '## Property Listings' in md_data

    def test_export_to_markdown_with_summary(self, exporter):
        """Test Markdown export with summary."""
        md_data = exporter.export_to_markdown(include_summary=True)

        assert '## Summary Statistics' in md_data
        assert 'Average Price' in md_data
        assert 'Median Price' in md_data

    def test_export_to_markdown_without_summary(self, exporter):
        """Test Markdown export without summary."""
        md_data = exporter.export_to_markdown(include_summary=False)

        assert '## Summary Statistics' not in md_data
        assert '## Property Listings' in md_data

    def test_export_to_markdown_max_properties(self, exporter):
        """Test Markdown export with property limit."""
        md_data = exporter.export_to_markdown(max_properties=2)

        # Should mention showing 2 of 3
        assert 'Showing 2 of 3' in md_data

    def test_markdown_contains_property_details(self, exporter):
        """Test Markdown contains property information."""
        md_data = exporter.export_to_markdown()

        # Should contain city names
        assert 'Krakow' in md_data
        assert 'Warsaw' in md_data
        # Should contain prices
        assert '$' in md_data
        # Should contain property features
        assert 'rooms' in md_data or 'bedroom' in md_data


class TestGenericExport:
    """Tests for generic export() method."""

    def test_export_csv_format(self, exporter):
        """Test generic export with CSV format."""
        data = exporter.export(ExportFormat.CSV)
        assert isinstance(data, str)
        assert len(data) > 0

    def test_export_excel_format(self, exporter):
        """Test generic export with Excel format."""
        data = exporter.export(ExportFormat.EXCEL)
        assert isinstance(data, BytesIO)

    def test_export_json_format(self, exporter):
        """Test generic export with JSON format."""
        data = exporter.export(ExportFormat.JSON)
        assert isinstance(data, str)
        parsed = json.loads(data)
        assert 'properties' in parsed

    def test_export_markdown_format(self, exporter):
        """Test generic export with Markdown format."""
        data = exporter.export(ExportFormat.MARKDOWN)
        assert isinstance(data, str)
        assert '# Property Listing Report' in data

    def test_export_with_options(self, exporter):
        """Test generic export with format-specific options."""
        # CSV with specific columns
        csv_data = exporter.export(ExportFormat.CSV, columns=['city', 'price'])
        assert 'city' in csv_data
        assert 'price' in csv_data

        # JSON with metadata
        json_data = exporter.export(ExportFormat.JSON, include_metadata=True)
        parsed = json.loads(json_data)
        assert 'metadata' in parsed


class TestFilenameGeneration:
    """Tests for filename generation."""

    def test_get_filename_csv(self, exporter):
        """Test CSV filename generation."""
        filename = exporter.get_filename(ExportFormat.CSV)

        assert filename.endswith('.csv')
        assert 'properties_' in filename
        # Should have timestamp
        assert len(filename) > 20

    def test_get_filename_excel(self, exporter):
        """Test Excel filename generation."""
        filename = exporter.get_filename(ExportFormat.EXCEL)

        assert filename.endswith('.xlsx')
        assert 'properties_' in filename

    def test_get_filename_json(self, exporter):
        """Test JSON filename generation."""
        filename = exporter.get_filename(ExportFormat.JSON)

        assert filename.endswith('.json')
        assert 'properties_' in filename

    def test_get_filename_markdown(self, exporter):
        """Test Markdown filename generation."""
        filename = exporter.get_filename(ExportFormat.MARKDOWN)

        assert filename.endswith('.md')
        assert 'properties_' in filename

    def test_get_filename_custom_prefix(self, exporter):
        """Test filename generation with custom prefix."""
        filename = exporter.get_filename(ExportFormat.CSV, prefix="my_export")

        assert 'my_export_' in filename
        assert filename.endswith('.csv')


class TestExportFormat:
    """Tests for ExportFormat enum."""

    def test_export_format_values(self):
        """Test ExportFormat enum values."""
        assert ExportFormat.CSV.value == "csv"
        assert ExportFormat.EXCEL.value == "xlsx"
        assert ExportFormat.JSON.value == "json"
        assert ExportFormat.MARKDOWN.value == "md"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_export_empty_collection(self):
        """Test exporting empty property collection."""
        empty_collection = PropertyCollection(properties=[], total_count=0)
        exporter = PropertyExporter(empty_collection)

        # Should not crash
        csv_data = exporter.export_to_csv()
        assert isinstance(csv_data, str)

        json_data = exporter.export_to_json()
        parsed = json.loads(json_data)
        assert len(parsed['properties']) == 0

    def test_export_single_property(self):
        """Test exporting single property."""
        single_prop = PropertyCollection(
            properties=[
                Property(
                    id="single",
                    city="Test",
                    rooms=2,
                    price=1000,
                    property_type=PropertyType.APARTMENT
                )
            ],
            total_count=1
        )
        exporter = PropertyExporter(single_prop)

        csv_data = exporter.export_to_csv()
        assert 'Test' in csv_data

        json_data = exporter.export_to_json()
        parsed = json.loads(json_data)
        assert len(parsed['properties']) == 1

    def test_export_with_missing_optional_fields(self):
        """Test export with properties missing optional fields."""
        minimal_prop = PropertyCollection(
            properties=[
                Property(
                    id="minimal",
                    city="Test",
                    rooms=2,
                    price=1000,
                    property_type=PropertyType.APARTMENT
                    # Missing: area_sqm, title, description, etc.
                )
            ],
            total_count=1
        )
        exporter = PropertyExporter(minimal_prop)

        # Should handle missing fields gracefully
        csv_data = exporter.export_to_csv()
        assert isinstance(csv_data, str)

        json_data = exporter.export_to_json()
        parsed = json.loads(json_data)
        assert len(parsed['properties']) == 1
