"""
Tests for Excel file upload and ingestion endpoints (Task #48).

Covers:
- Direct file upload endpoint
- Sheet preview endpoint
- Excel edge cases (empty sheets, merged cells, multi-sheet)
- ChromaPropertyStore delete_by_source_type
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from data.csv_loader import DataLoaderExcel
from data.schemas import Property, PropertyCollection

# ============================================================================
# DataLoaderExcel Edge Case Tests
# ============================================================================


class TestDataLoaderExcelEdgeCases:
    """Tests for DataLoaderExcel edge case handling."""

    def test_empty_sheet_returns_empty_df(self, tmp_path: Path):
        """Test that an empty sheet returns an empty DataFrame."""
        pytest.importorskip("openpyxl")

        # Create Excel with empty sheet
        p = tmp_path / "empty.xlsx"
        df_empty = pd.DataFrame()
        df_empty.to_excel(p, index=False)

        loader = DataLoaderExcel(str(p))
        df = loader.load_df()

        assert len(df) == 0
        assert isinstance(df, pd.DataFrame)

    def test_custom_header_row(self, tmp_path: Path):
        """Test loading with a non-zero header row."""
        pytest.importorskip("openpyxl")

        # Create Excel with data starting at row 2 (index 1)
        p = tmp_path / "header_row.xlsx"
        df_data = pd.DataFrame(
            {
                "Unnamed: 0": ["Skip this row"],
                "city": ["Warsaw"],
                "price": [1500],
                "rooms": [3],
            }
        )
        df_data.to_excel(p, index=False, header=False)

        # Write with proper header at row 1
        with pd.ExcelWriter(p, engine="openpyxl") as writer:
            pd.DataFrame({"col1": ["Header row 0"]}).to_excel(
                writer, index=False, header=False, startrow=0
            )
            pd.DataFrame({"city": ["Krakow"], "price": [1000], "rooms": [2]}).to_excel(
                writer, index=False, header=True, startrow=1
            )

        loader = DataLoaderExcel(str(p), header_row=1)
        df = loader.load_df()

        assert "city" in df.columns
        assert len(df) >= 1

    def test_multi_sheet_selection(self, tmp_path: Path):
        """Test selecting specific sheets from a multi-sheet file."""
        pytest.importorskip("openpyxl")

        p = tmp_path / "multi_sheet.xlsx"
        with pd.ExcelWriter(p, engine="openpyxl") as writer:
            pd.DataFrame({"city": ["Warsaw"], "price": [1000]}).to_excel(
                writer, sheet_name="Sheet1", index=False
            )
            pd.DataFrame({"city": ["Krakow"], "price": [2000]}).to_excel(
                writer, sheet_name="Sheet2", index=False
            )

        # Get sheet names
        loader = DataLoaderExcel(str(p))
        sheets = loader.get_sheet_names()
        assert "Sheet1" in sheets
        assert "Sheet2" in sheets

        # Load specific sheet
        loader2 = DataLoaderExcel(str(p), sheet_name="Sheet2")
        df = loader2.load_df()
        assert df["city"].iloc[0] == "Krakow"

    def test_invalid_extension_raises_error(self):
        """Test that invalid file extensions raise ValueError."""
        loader = DataLoaderExcel("invalid.txt")
        with pytest.raises(ValueError, match="Unsupported file format"):
            loader.load_df()

    def test_detect_source_type_csv(self):
        """Test source type detection for CSV files."""
        assert DataLoaderExcel.detect_source_type("data.csv") == "csv"
        assert DataLoaderExcel.detect_source_type("/path/to/data.CSV") == "csv"

    def test_detect_source_type_excel(self):
        """Test source type detection for Excel files."""
        assert DataLoaderExcel.detect_source_type("data.xlsx") == "excel"
        assert DataLoaderExcel.detect_source_type("data.xls") == "excel"
        assert DataLoaderExcel.detect_source_type("data.ods") == "excel"
        assert DataLoaderExcel.detect_source_type("/path/to/data.XLSX") == "excel"

    def test_detect_source_type_url(self):
        """Test source type detection for URLs."""
        from yarl import URL

        assert DataLoaderExcel.detect_source_type(URL("https://example.com/data.csv")) == "url"
        assert DataLoaderExcel.detect_source_type(URL("https://example.com/data.xlsx")) == "url"

    def test_detect_source_type_unknown(self):
        """Test source type detection for unknown types."""
        assert DataLoaderExcel.detect_source_type("data.txt") == "unknown"
        assert DataLoaderExcel.detect_source_type("no_extension") == "unknown"


# ============================================================================
# File Upload Endpoint Tests (using TestClient)
# ============================================================================


class TestFileUploadEndpoint:
    """Tests for POST /admin/ingest/upload endpoint."""

    @patch("api.routers.admin.save_collection")
    @patch("api.routers.admin.settings")
    @patch("api.auth.get_settings")
    def test_upload_xlsx_success(
        self, mock_get_settings, mock_settings, mock_save_collection, tmp_path: Path
    ):
        """Test successful upload of .xlsx file."""
        pytest.importorskip("openpyxl")
        from fastapi.testclient import TestClient

        from api.main import app

        mock_get_settings.return_value = MagicMock(api_access_key="test-key")
        mock_settings.max_properties = 1000

        # Create test Excel file
        p = tmp_path / "test.xlsx"
        df = pd.DataFrame(
            {
                "city": ["Warsaw", "Krakow", "Gdansk"],
                "price": [1000, 1200, 900],
                "rooms": [2, 3, 1],
                "area_sqm": [50, 70, 35],
            }
        )
        df.to_excel(p, index=False)

        client = TestClient(app)
        client.cookies.set("csrf_token", "test-csrf-token")
        headers = {"X-API-Key": "test-key", "X-CSRF-Token": "test-csrf-token"}

        with open(p, "rb") as f:
            files = {
                "file": (
                    "test.xlsx",
                    f,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            }
            response = client.post(
                "/api/v1/admin/ingest/upload",
                files=files,
                headers=headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["properties_processed"] == 3
        assert data["source_type"] == "excel"

    @patch("api.routers.admin.save_collection")
    @patch("api.routers.admin.settings")
    @patch("api.auth.get_settings")
    def test_upload_csv_success(
        self, mock_get_settings, mock_settings, mock_save_collection, tmp_path: Path
    ):
        """Test successful upload of .csv file."""
        from fastapi.testclient import TestClient

        from api.main import app

        mock_get_settings.return_value = MagicMock(api_access_key="test-key")
        mock_settings.max_properties = 1000

        p = tmp_path / "test.csv"
        df = pd.DataFrame(
            {
                "city": ["Warsaw"],
                "price": [1000],
                "rooms": [2],
            }
        )
        df.to_csv(p, index=False)

        client = TestClient(app)
        client.cookies.set("csrf_token", "test-csrf-token")
        headers = {"X-API-Key": "test-key", "X-CSRF-Token": "test-csrf-token"}

        with open(p, "rb") as f:
            files = {"file": ("test.csv", f, "text/csv")}
            response = client.post(
                "/api/v1/admin/ingest/upload",
                files=files,
                headers=headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["properties_processed"] == 1
        assert data["source_type"] == "csv"

    @patch("api.auth.get_settings")
    def test_upload_invalid_type(self, mock_get_settings, tmp_path: Path):
        """Test that invalid file types are rejected."""
        from fastapi.testclient import TestClient

        from api.main import app

        mock_get_settings.return_value = MagicMock(api_access_key="test-key")

        p = tmp_path / "test.json"
        p.write_text('{"not": "valid"}')

        client = TestClient(app)
        client.cookies.set("csrf_token", "test-csrf-token")
        headers = {"X-API-Key": "test-key", "X-CSRF-Token": "test-csrf-token"}

        with open(p, "rb") as f:
            files = {"file": ("test.json", f, "application/json")}
            response = client.post(
                "/api/v1/admin/ingest/upload",
                files=files,
                headers=headers,
            )

        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]


class TestExcelSheetsUploadEndpoint:
    """Tests for POST /admin/excel/sheets/upload endpoint."""

    @patch("api.auth.get_settings")
    def test_get_sheets_from_upload(self, mock_get_settings, tmp_path: Path):
        """Test getting sheet names from uploaded Excel file."""
        pytest.importorskip("openpyxl")
        from fastapi.testclient import TestClient

        from api.main import app

        mock_get_settings.return_value = MagicMock(api_access_key="test-key")

        p = tmp_path / "multi.xlsx"
        with pd.ExcelWriter(p, engine="openpyxl") as writer:
            pd.DataFrame(
                {"city": ["Warsaw", "Krakow", "Gdansk"], "price": [1000, 1200, 900]}
            ).to_excel(writer, sheet_name="Data1", index=False)
            pd.DataFrame({"city": ["Poznan", "Wroclaw"], "price": [1100, 1300]}).to_excel(
                writer, sheet_name="Data2", index=False
            )

        client = TestClient(app)
        client.cookies.set("csrf_token", "test-csrf-token")
        headers = {"X-API-Key": "test-key", "X-CSRF-Token": "test-csrf-token"}

        with open(p, "rb") as f:
            files = {
                "file": (
                    "multi.xlsx",
                    f,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            }
            response = client.post(
                "/api/v1/admin/excel/sheets/upload",
                files=files,
                headers=headers,
            )

        assert response.status_code == 200
        result = response.json()
        assert "Data1" in result["sheet_names"]
        assert "Data2" in result["sheet_names"]
        assert result["row_count"]["Data1"] == 3
        assert result["row_count"]["Data2"] == 2

    @patch("api.auth.get_settings")
    def test_get_sheets_invalid_type(self, mock_get_settings, tmp_path: Path):
        """Test that non-Excel files are rejected."""
        from fastapi.testclient import TestClient

        from api.main import app

        mock_get_settings.return_value = MagicMock(api_access_key="test-key")

        p = tmp_path / "test.csv"
        p.write_text("a,b\n1,2")

        client = TestClient(app)
        client.cookies.set("csrf_token", "test-csrf-token")
        headers = {"X-API-Key": "test-key", "X-CSRF-Token": "test-csrf-token"}

        with open(p, "rb") as f:
            files = {"file": ("test.csv", f, "text/csv")}
            response = client.post(
                "/api/v1/admin/excel/sheets/upload",
                files=files,
                headers=headers,
            )

        assert response.status_code == 400


# ============================================================================
# ChromaPropertyStore Tests
# ============================================================================


class TestChromaPropertyStoreDelete:
    """Tests for ChromaPropertyStore delete methods."""

    def test_delete_by_source_type_exists(self):
        """Test that delete_by_source_type method exists."""
        from vector_store.chroma_store import ChromaPropertyStore

        # Check method exists
        assert hasattr(ChromaPropertyStore, "delete_by_source_type")
        assert callable(ChromaPropertyStore.delete_by_source_type)

    @patch("vector_store.chroma_store.ChromaPropertyStore._get_vector_store")
    def test_delete_by_source_type_calls_delete(self, mock_get_store):
        """Test that delete_by_source_type calls vector store delete with correct filter."""
        from vector_store.chroma_store import ChromaPropertyStore

        # Mock the vector store
        mock_store = MagicMock()
        mock_get_store.return_value = mock_store

        # Create store and call delete
        store = ChromaPropertyStore.__new__(ChromaPropertyStore)
        store._vector_lock = MagicMock()
        store._vector_lock.__enter__ = MagicMock(return_value=None)
        store._vector_lock.__exit__ = MagicMock(return_value=None)
        store.delete_by_source_type("excel")

        # Verify delete was called with correct filter
        mock_store.delete.assert_called_once_with(filter={"source_platform": "excel"})


# ============================================================================
# PropertyCollection Tests
# ============================================================================


class TestPropertyCollectionSourceTracking:
    """Tests for PropertyCollection source tracking."""

    def test_collection_has_source_type(self):
        """Test that PropertyCollection has source_type field."""
        props = [
            Property(city="Warsaw", price=1000, rooms=2, area_sqm=50),
        ]
        collection = PropertyCollection(
            properties=props,
            total_count=1,
            source="test_source",
            source_type="excel",
        )

        assert collection.source == "test_source"
        assert collection.source_type == "excel"

    def test_delete_by_source_type(self):
        """Test PropertyCollection.delete_by_source_type method."""
        props = [
            Property(city="Warsaw", price=1000, rooms=2, area_sqm=50, source_platform="excel"),
            Property(city="Krakow", price=1200, rooms=3, area_sqm=60, source_platform="csv"),
        ]
        collection = PropertyCollection(
            properties=props,
            total_count=2,
        )

        # Delete excel sources
        filtered = collection.delete_by_source_type("excel")

        assert len(filtered.properties) == 1
        assert filtered.properties[0].source_platform == "csv"
