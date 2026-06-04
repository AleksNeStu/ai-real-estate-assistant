import logging
import re
from pathlib import Path
from typing import Any, List, Literal, Optional
from urllib.parse import urlparse

import numpy as np
import pandas as pd
import requests
from faker import Faker
from yarl import URL

from core.security_utils import sanitize_for_log

# Configure logger
logger = logging.getLogger(__name__)

# Initialize Faker for Poland locale (for generating fake owner data)
fake_pl = Faker("pl_PL")

# Set the pandas option to opt into future behavior
pd.options.future.no_silent_downcasting = True

# Source type constants for tracking
SourceType = Literal["csv", "excel", "url", "unknown"]


class DataLoaderCsv:
    def __init__(self, csv_path: Path | URL | str | None):
        if csv_path is None:
            self.csv_path = None
            return

        if isinstance(csv_path, Path) and not csv_path.is_file():
            err_msg = f"The Path {sanitize_for_log(csv_path)} does not exists."
            # raise FileNotFoundError(err_msg)
            logger.warning(err_msg)
            csv_path = None
        elif isinstance(csv_path, URL) and not self.url_exists(csv_path):
            err_msg = f"The URL at {sanitize_for_log(csv_path)} does not exist."
            # raise FileNotFoundError(err_msg)
            logger.warning(err_msg)
            csv_path = None

        self.csv_path = csv_path

    @staticmethod
    def url_exists(url: URL) -> bool:
        parsed_url = urlparse(str(url))
        is_valid_url = all([parsed_url.scheme, parsed_url.netloc])
        if not is_valid_url:
            return False  # URL structure is not valid
        try:
            response = requests.head(str(url), allow_redirects=True, timeout=10)
            return response.status_code < 400
        except requests.RequestException:
            return False  # Handle any exceptions during the request

    @staticmethod
    def convert_github_url_to_raw(url: str) -> str:
        """Convert GitHub URL to raw content URL."""
        if "github.com" in url and "/blob/" in url:
            # Convert github.com/user/repo/blob/branch/file to raw.githubusercontent.com/user/repo/branch/file
            return url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
        return url

    def load_df(self) -> pd.DataFrame:
        """Load tabular data (CSV/Excel) with flexible parsing."""
        if self.csv_path is None:
            raise ValueError("No CSV/Excel path provided")

        csv_url = str(self.csv_path)

        if isinstance(self.csv_path, (str, URL)):
            csv_url = self.convert_github_url_to_raw(csv_url)

        parsed = urlparse(csv_url)
        path_for_suffix = parsed.path if parsed.scheme and parsed.netloc else csv_url
        suffix = Path(path_for_suffix).suffix.lower()
        is_excel = suffix in {".xlsx", ".xls"}

        try:
            if is_excel:
                try:
                    if suffix == ".xls":
                        df = pd.read_excel(csv_url, engine="xlrd")
                    else:
                        df = pd.read_excel(csv_url, engine="openpyxl")
                except ValueError:
                    df = pd.read_excel(csv_url)
            else:
                df = pd.read_csv(csv_url)
        except ImportError as e:
            raise ImportError(
                "Excel input requires optional dependencies: openpyxl (.xlsx) or xlrd (.xls)."
            ) from e
        except Exception as e:
            if is_excel:
                raise Exception(f"Failed to load Excel file: {sanitize_for_log(e)}") from e

            try:
                df = pd.read_csv(
                    csv_url,
                    encoding="utf-8",
                    on_bad_lines="skip",
                    engine="python",
                )
            except Exception as e2:
                try:
                    df = pd.read_csv(
                        csv_url,
                        encoding="latin-1",
                        on_bad_lines="skip",
                        engine="python",
                    )
                except Exception as e3:
                    raise Exception(
                        f"Failed to load CSV: {sanitize_for_log(e)}. Additional attempts failed: {sanitize_for_log(e2)}, {sanitize_for_log(e3)}"
                    ) from e3

        logger.info("Data frame loaded from %s, rows: %s", sanitize_for_log(csv_url), len(df))
        return df

    def load_format_df(self, df: pd.DataFrame, rows_count: int | None = None) -> pd.DataFrame:
        """Returns the DataFrame. If not loaded, loads and prepares the data first."""
        df_formatted = self.format_df(df, rows_count=rows_count)
        logger.info("Data frame formatted from %s", sanitize_for_log(self.csv_path))
        return df_formatted

    @staticmethod
    def bathrooms_fake(rooms: float) -> float:
        # Add 'bathrooms': Either 1 or 2, check consistency with 'rooms' (e.g., bathrooms should be realistic)
        if pd.isna(rooms) or rooms < 2:
            return 1.0
        return float(np.random.choice([1.0, 2.0]))

    @staticmethod
    def price_media_fake(price: float) -> float:
        # Add 'price_media': Fake values like internet, gas, electricity, not more than 20% of 'price'
        # Generate a fake price for utilities, up to 20% of the 'price'
        return round(np.random.uniform(0, 0.2 * price), 2)

    @staticmethod
    def camel_to_snake(name: str) -> str:
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    @staticmethod
    def format_df(df: pd.DataFrame, rows_count: int | None = None) -> pd.DataFrame:
        # Get header
        header = df.columns.tolist()

        # Drop rows with any NaN values
        df_copy = df.copy()
        logger.info("Original data frame rows: %s", len(df_copy))

        # Camel case to snake for header first
        df_copy.columns = [DataLoaderCsv.camel_to_snake(col) for col in df_copy.columns]

        # Map common synonyms to canonical schema keys (best effort)
        if "price" not in df_copy.columns:
            price_cols = [
                col
                for col in df_copy.columns
                if any(x in col.lower() for x in ["price", "cost", "rent"])
            ]
            if price_cols:
                df_copy = df_copy.rename(columns={price_cols[0]: "price"})

        # Add missing essential columns with default values
        if "city" not in df_copy.columns:
            # Try to find location column
            location_cols = [
                col
                for col in df_copy.columns
                if any(x in col.lower() for x in ["city", "location", "place", "town"])
            ]
            if location_cols:
                df_copy = df_copy.rename(columns={location_cols[0]: "city"})
            else:
                df_copy["city"] = "Unknown"

        if "rooms" not in df_copy.columns:
            # Try to find rooms column
            room_cols = [
                col for col in df_copy.columns if "room" in col.lower() or "bedroom" in col.lower()
            ]
            if room_cols:
                df_copy = df_copy.rename(columns={room_cols[0]: "rooms"})
            else:
                df_copy["rooms"] = 2.0
        else:
            df_copy["rooms"] = df_copy["rooms"].fillna(2.0)

        # Prefer canonical 'area_sqm'
        if "area_sqm" not in df_copy.columns:
            area_cols = [
                col
                for col in df_copy.columns
                if any(x in col.lower() for x in ["area_sqm", "area", "size", "sqm", "square"])
            ]
            if area_cols:
                df_copy = df_copy.rename(columns={area_cols[0]: "area_sqm"})

        # Currency handling: normalize currency column if present, set defaults
        if "currency" not in df_copy.columns:
            currency_cols = [
                col for col in df_copy.columns if "currency" in col.lower() or "curr" in col.lower()
            ]
            if currency_cols:
                df_copy = df_copy.rename(columns={currency_cols[0]: "currency"})
            else:
                # Heuristic default: PLN for common Polish cities, else Unknown
                pl_cities = {
                    "warsaw",
                    "warszawa",
                    "krakow",
                    "wroclaw",
                    "poznan",
                    "gdansk",
                    "szczecin",
                    "lublin",
                    "katowice",
                    "bydgoszcz",
                    "lodz",
                }
                default_curr = (
                    "PLN"
                    if (
                        "city" in df_copy.columns
                        and any(
                            str(c).lower() in pl_cities
                            for c in df_copy["city"].dropna().astype(str).unique()
                        )
                    )
                    else "Unknown"
                )
                df_copy["currency"] = default_curr

        # Listing type normalization
        if "listing_type" not in df_copy.columns:
            lt_cols = [
                col
                for col in df_copy.columns
                if any(
                    x in col.lower()
                    for x in ["listing_type", "deal_type", "sale_or_rent", "listing", "status"]
                )
            ]
            if lt_cols:
                df_copy = df_copy.rename(columns={lt_cols[0]: "listing_type"})
            else:
                df_copy["listing_type"] = "rent"
        else:
            df_copy["listing_type"] = df_copy["listing_type"].fillna("rent")
        df_copy["listing_type"] = (
            df_copy["listing_type"]
            .astype(str)
            .str.strip()
            .str.lower()
            .replace(
                {
                    "for_rent": "rent",
                    "rental": "rent",
                    "lease": "rent",
                    "for_sale": "sale",
                    "sold": "sale",
                    "room_rent": "room",
                    "sublet": "sublease",
                }
            )
        )

        # Geocoordinates: fill latitude/longitude deterministically by city where missing
        city_coords = {
            "warsaw": (52.2297, 21.0122),
            "krakow": (50.0647, 19.9450),
            "wroclaw": (51.1079, 17.0385),
            "poznan": (52.4064, 16.9252),
            "gdansk": (54.3520, 18.6466),
            "szczecin": (53.4285, 14.5528),
            "lublin": (51.2465, 22.5684),
            "katowice": (50.2649, 19.0238),
            "bydgoszcz": (53.1235, 18.0084),
            "lodz": (51.7592, 19.4560),
        }
        # Ensure columns exist
        if "latitude" not in df_copy.columns:
            df_copy["latitude"] = np.nan
        if "longitude" not in df_copy.columns:
            df_copy["longitude"] = np.nan

        # Vectorized fill
        if "city" in df_copy.columns:
            # Create normalized city series for lookup
            cities_normalized = df_copy["city"].astype(str).str.strip().str.lower()

            # Create mapping series
            lat_map = cities_normalized.map(lambda x: city_coords.get(x, (None, None))[0])
            lon_map = cities_normalized.map(lambda x: city_coords.get(x, (None, None))[1])

            # Fill missing values
            df_copy["latitude"] = df_copy["latitude"].fillna(lat_map)
            df_copy["longitude"] = df_copy["longitude"].fillna(lon_map)

            # Coerce to float
            df_copy["latitude"] = pd.to_numeric(df_copy["latitude"], errors="coerce")
            df_copy["longitude"] = pd.to_numeric(df_copy["longitude"], errors="coerce")

        # Do not drop rows; allow missing values (schema-agnostic ingestion)
        df_cleaned = df_copy

        # Shuffle the DataFrame to ensure randomness
        df_shuffled = df_cleaned.sample(frac=1, random_state=1).reset_index(drop=True)

        df_final = df_shuffled.head(rows_count).copy() if rows_count else df_shuffled.copy()

        # Replace values with True/False
        df_final = df_final.replace({"yes": True, "no": False})

        # Normalize boolean columns: fill NaN -> False and coerce to bool
        bool_cols = [
            "has_parking",
            "has_garden",
            "has_pool",
            "has_garage",
            "has_bike_room",
            "is_furnished",
            "pets_allowed",
            "has_balcony",
            "has_elevator",
        ]
        for col in bool_cols:
            if col in df_final.columns:
                series = df_final[col].fillna(False)
                series = series.map(lambda v: bool(v) if not pd.isna(v) else False)
                df_final[col] = series.astype(bool)

        # Replace int to float where applicable (avoid silent downcasting)
        def _to_float_series(s: pd.Series) -> pd.Series:
            try:
                return s.astype(float)
            except Exception:
                return s

        df_final = df_final.apply(
            lambda x: _to_float_series(x) if pd.api.types.is_integer_dtype(x) else x
        )

        # Bathrooms normalization (best effort)
        if "bathrooms" not in df_final.columns and "rooms" in df_final.columns:
            # Vectorized bathroom estimation
            df_final["bathrooms"] = 1.0

            # Find properties with 2+ rooms
            mask_large = df_final["rooms"] >= 2

            if mask_large.any():
                # Randomly assign 1.0 or 2.0 to large properties
                # We use numpy to generate random choices for the masked selection
                random_baths = np.random.choice([1.0, 2.0], size=mask_large.sum())
                df_final.loc[mask_large, "bathrooms"] = random_baths

        elif "bathrooms" in df_final.columns:
            df_final["bathrooms"] = df_final["bathrooms"].fillna(1.0)

        for field in ["has_garden", "has_pool", "has_garage", "has_bike_room"]:
            if field not in df_final.columns:
                df_final[field] = np.random.choice([True, False], size=len(df_final))
        if "has_elevator" not in df_final.columns:
            df_final["has_elevator"] = np.random.choice([True, False], size=len(df_final))

        # Year built normalization
        if "year_built" not in df_final.columns:
            year_cols = [
                col
                for col in df_final.columns
                if any(x in col.lower() for x in ["year_built", "construction_year", "built_year"])
            ]
            if year_cols:
                df_final = df_final.rename(columns={year_cols[0]: "year_built"})
            else:
                df_final["year_built"] = np.random.randint(1970, 2025, size=len(df_final))
        else:
            df_final["year_built"] = df_final["year_built"].fillna(2000)

        # Energy rating normalization
        if "energy_rating" not in df_final.columns:
            energy_cols = [
                col
                for col in df_final.columns
                if any(x in col.lower() for x in ["energy_rating", "energy_class", "epc"])
            ]
            if energy_cols:
                df_final = df_final.rename(columns={energy_cols[0]: "energy_rating"})
            else:
                df_final["energy_rating"] = np.random.choice(
                    ["A", "B", "C", "D", "E", "F", "G"], size=len(df_final)
                )
        else:
            df_final["energy_rating"] = df_final["energy_rating"].fillna("C")

        # Log added columns and final row count
        header_final = df_final.columns.tolist()
        diff_header = set(header_final) - set(header)

        if diff_header:
            logger.info("Added columns with generated data: %s", sanitize_for_log(diff_header))
        logger.info("Formatted data frame rows: %s", len(df_final))

        return df_final


class DataLoaderExcel(DataLoaderCsv):
    """
    Enhanced Excel loader with sheet selection and source tracking.

    Supports .xlsx, .xls, and .ods files with:
    - Sheet detection and selection
    - Header row configuration
    - Source type tracking
    """

    def __init__(
        self,
        file_path: Path | str,
        sheet_name: Optional[str] = None,
        header_row: Optional[int] = 0,
        source_type: SourceType = "excel",
    ):
        """
        Initialize Excel loader.

        Args:
            file_path: Path to Excel file (.xlsx, .xls, .ods)
            sheet_name: Specific sheet name to load (None = first sheet)
            header_row: Row number to use as header (0-indexed)
            source_type: Source type for tracking
        """
        super().__init__(file_path)
        self.sheet_name = sheet_name
        self.header_row = header_row
        self.source_type = source_type

    def get_sheet_names(self) -> List[str]:
        """
        Get list of sheet names from Excel file.

        Returns:
            List of sheet names

        Raises:
            ImportError: If required Excel libraries not installed
            Exception: If file cannot be read
        """
        if self.csv_path is None:
            return []

        file_path = str(self.csv_path)
        suffix = Path(file_path).suffix.lower()

        try:
            if suffix == ".xlsx":
                import openpyxl

                wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
                sheet_names = list(wb.sheetnames)
                wb.close()
                return sheet_names
            elif suffix == ".xls":
                import xlrd

                workbook = xlrd.open_workbook(file_path)
                sheet_names = list(workbook.sheet_names())
                return sheet_names
            elif suffix == ".ods":
                try:
                    from odf.opendocument import load

                    doc = load(file_path)
                    return list(doc.spreadsheets.keys())
                except ImportError:
                    # Fallback to pandas ExcelFile
                    excel_file = pd.ExcelFile(file_path, engine="odf")
                    sheet_names = list(excel_file.sheet_names)
                    excel_file.close()
                    return sheet_names
            else:
                excel_file = pd.ExcelFile(file_path)
                sheet_names = list(excel_file.sheet_names)
                excel_file.close()
                return sheet_names
        except ImportError as e:
            raise ImportError(
                f"Excel file reading requires optional dependencies. "
                f"For .xlsx: openpyxl (already installed). "
                f"For .xls: xlrd. "
                f"For .ods: odfpy or ezodf. "
                f"Error: {e}"
            ) from e

    def load_df(self) -> pd.DataFrame:
        """
        Load Excel data with sheet selection and header configuration.

        Returns:
            DataFrame with loaded data

        Raises:
            ValueError: If file path not provided or sheet not found
            Exception: If file cannot be loaded
        """
        if self.csv_path is None:
            raise ValueError("No Excel file path provided")

        file_path = str(self.csv_path)
        suffix = Path(file_path).suffix.lower()
        is_excel = suffix in {".xlsx", ".xls", ".ods"}

        if not is_excel:
            raise ValueError(
                f"Unsupported file format: {suffix}. Excel loader supports .xlsx, .xls, .ods files."
            )

        try:
            # Build kwargs for pd.read_excel
            read_kwargs: dict[str, Any] = {}

            if self.sheet_name:
                read_kwargs["sheet_name"] = self.sheet_name
            if self.header_row is not None:
                read_kwargs["header"] = self.header_row

            # Select appropriate engine based on file type
            if suffix == ".xlsx":
                read_kwargs["engine"] = "openpyxl"
            elif suffix == ".xls":
                import importlib.util

                if importlib.util.find_spec("xlrd"):
                    read_kwargs["engine"] = "xlrd"
            elif suffix == ".ods":
                import importlib.util

                if importlib.util.find_spec("odf"):
                    read_kwargs["engine"] = "odf"

            df = pd.read_excel(file_path, **read_kwargs)

            logger.info(
                "Excel data loaded from %s (sheet: %s, rows: %s)",
                sanitize_for_log(file_path),
                sanitize_for_log(self.sheet_name or "default"),
                len(df),
            )
            return df

        except ImportError as e:
            raise ImportError(
                "Excel input requires optional dependencies: "
                "openpyxl (.xlsx), xlrd (.xls), or odfpy (.ods)."
            ) from e
        except Exception as e:
            raise Exception(f"Failed to load Excel file: {sanitize_for_log(e)}") from e

    @classmethod
    def detect_source_type(cls, file_path: Path | str | URL) -> SourceType:
        """
        Detect source type from file path.

        Args:
            file_path: Path to file

        Returns:
            Source type: "csv", "excel", "url", or "unknown"
        """
        path_str = str(file_path)

        # Check if URL
        if isinstance(file_path, URL) or urlparse(path_str).scheme in {"http", "https"}:
            path_str = cls.convert_github_url_to_raw(path_str)
            suffix = Path(urlparse(path_str).path).suffix.lower()
            if suffix in {".xlsx", ".xls", ".ods"}:
                return "url"  # URL pointing to Excel
            return "url"  # URL pointing to CSV

        # Check file extension
        suffix = Path(path_str).suffix.lower()
        if suffix == ".csv":
            return "csv"
        elif suffix in {".xlsx", ".xls", ".ods"}:
            return "excel"

        return "unknown"
