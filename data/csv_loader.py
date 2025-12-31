from urllib.parse import urlparse
from pathlib import Path
from yarl import URL
import logging
import streamlit as st
import numpy as np
import pandas as pd
import re
import requests
from faker import Faker
from typing import Any

# Configure logger
logger = logging.getLogger(__name__)

# Initialize Faker for Poland locale (for generating fake owner data)
fake_pl = Faker('pl_PL')

# Set the pandas option to opt into future behavior
pd.options.future.no_silent_downcasting = True



class DataLoaderCsv:

    def __init__(
            self, csv_path: Path | URL | str | None
    ):
        if csv_path is None:
            self.csv_path = None
            return

        if isinstance(csv_path, Path) and not csv_path.is_file():
            err_msg = f"The Path {csv_path} does not exists."
            # raise FileNotFoundError(err_msg)
            st.warning(err_msg, icon='⚠')
            csv_path = None
        elif isinstance(csv_path, URL) and not self.url_exists(csv_path):
            err_msg = f"The URL at {csv_path} does not exist."
            # raise FileNotFoundError(err_msg)
            st.warning(err_msg, icon='⚠')
            csv_path = None

        self.csv_path = csv_path

    @staticmethod
    def url_exists(url: URL) -> bool:
        parsed_url = urlparse(str(url))
        is_valid_url = all([parsed_url.scheme, parsed_url.netloc])
        if not is_valid_url:
            return False  # URL structure is not valid
        try:
            response = requests.head(str(url), allow_redirects=True)
            return response.status_code < 400
        except requests.RequestException:
            return False  # Handle any exceptions during the request

    @staticmethod
    def convert_github_url_to_raw(url: str) -> str:
        """Convert GitHub URL to raw content URL."""
        if 'github.com' in url and '/blob/' in url:
            # Convert github.com/user/repo/blob/branch/file to raw.githubusercontent.com/user/repo/branch/file
            return url.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
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
                raise Exception(f"Failed to load Excel file: {str(e)}") from e

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
                        f"Failed to load CSV: {str(e)}. Additional attempts failed: {str(e2)}, {str(e3)}"
                    ) from e3

        logger.info(f"Data frame loaded from {csv_url}, rows: {len(df)}")
        return df

    def load_format_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Returns the DataFrame. If not loaded, loads and prepares the data first."""
        df_formatted = self.format_df(df)
        logger.info(f"Data frame formatted from {self.csv_path}")
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
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    @staticmethod
    def format_df(df: pd.DataFrame, rows_count: int | None = None) -> pd.DataFrame:
        # Get header
        header = df.columns.tolist()

        # Drop rows with any NaN values
        df_copy = df.copy()
        logger.info(f'Original data frame rows: {len(df_copy)}')

        # Camel case to snake for header first
        df_copy.columns = [
            DataLoaderCsv.camel_to_snake(col) for col in df_copy.columns]

        # Map common synonyms to canonical schema keys (best effort)
        if 'price' not in df_copy.columns:
            price_cols = [col for col in df_copy.columns if any(x in col.lower() for x in ['price', 'cost', 'rent'])]
            if price_cols:
                df_copy = df_copy.rename(columns={price_cols[0]: 'price'})

        # Add missing essential columns with default values
        if 'city' not in df_copy.columns:
            # Try to find location column
            location_cols = [col for col in df_copy.columns if any(x in col.lower() for x in ['city', 'location', 'place', 'town'])]
            if location_cols:
                df_copy = df_copy.rename(columns={location_cols[0]: 'city'})
            else:
                df_copy['city'] = 'Unknown'

        if 'rooms' not in df_copy.columns:
            # Try to find rooms column
            room_cols = [col for col in df_copy.columns if 'room' in col.lower() or 'bedroom' in col.lower()]
            if room_cols:
                df_copy = df_copy.rename(columns={room_cols[0]: 'rooms'})
            else:
                df_copy['rooms'] = 2.0
        else:
            df_copy['rooms'] = df_copy['rooms'].fillna(2.0)

        # Prefer canonical 'area_sqm'
        if 'area_sqm' not in df_copy.columns:
            area_cols = [col for col in df_copy.columns if any(x in col.lower() for x in ['area_sqm', 'area', 'size', 'sqm', 'square'])]
            if area_cols:
                df_copy = df_copy.rename(columns={area_cols[0]: 'area_sqm'})

        # Currency handling: normalize currency column if present, set defaults
        if 'currency' not in df_copy.columns:
            currency_cols = [col for col in df_copy.columns if 'currency' in col.lower() or 'curr' in col.lower()]
            if currency_cols:
                df_copy = df_copy.rename(columns={currency_cols[0]: 'currency'})
            else:
                # Heuristic default: PLN for common Polish cities, else Unknown
                pl_cities = {'warsaw','warszawa','krakow','wroclaw','poznan','gdansk','szczecin','lublin','katowice','bydgoszcz','lodz'}
                default_curr = 'PLN' if ('city' in df_copy.columns and any(str(c).lower() in pl_cities for c in df_copy['city'].dropna().astype(str).unique())) else 'Unknown'
                df_copy['currency'] = default_curr

        # Listing type normalization
        if 'listing_type' not in df_copy.columns:
            lt_cols = [col for col in df_copy.columns if any(x in col.lower() for x in ['listing_type', 'deal_type', 'sale_or_rent', 'listing', 'status'])]
            if lt_cols:
                df_copy = df_copy.rename(columns={lt_cols[0]: 'listing_type'})
            else:
                df_copy['listing_type'] = 'rent'
        else:
            df_copy['listing_type'] = df_copy['listing_type'].fillna('rent')
        df_copy['listing_type'] = df_copy['listing_type'].astype(str).str.strip().str.lower().replace({
            'for_rent': 'rent',
            'rental': 'rent',
            'lease': 'rent',
            'for_sale': 'sale',
            'sold': 'sale',
            'room_rent': 'room',
            'sublet': 'sublease'
        })

        # Geocoordinates: fill latitude/longitude deterministically by city where missing
        city_coords = {
            'warsaw': (52.2297, 21.0122),
            'krakow': (50.0647, 19.9450),
            'wroclaw': (51.1079, 17.0385),
            'poznan': (52.4064, 16.9252),
            'gdansk': (54.3520, 18.6466),
            'szczecin': (53.4285, 14.5528),
            'lublin': (51.2465, 22.5684),
            'katowice': (50.2649, 19.0238),
            'bydgoszcz': (53.1235, 18.0084),
            'lodz': (51.7592, 19.4560)
        }
        # Ensure columns exist
        if 'latitude' not in df_copy.columns:
            df_copy['latitude'] = None
        if 'longitude' not in df_copy.columns:
            df_copy['longitude'] = None
        if 'city' in df_copy.columns:
            def _fill_lat(row: pd.Series) -> float | None:
                if pd.isna(row.get('latitude')) and pd.notna(row.get('city')):
                    c = str(row['city']).strip().lower()
                    return city_coords.get(c, (None, None))[0]
                val: Any = row.get('latitude')
                if val is None or pd.isna(val):
                    return None
                try:
                    return float(val)
                except Exception:
                    return None
            def _fill_lon(row: pd.Series) -> float | None:
                if pd.isna(row.get('longitude')) and pd.notna(row.get('city')):
                    c = str(row['city']).strip().lower()
                    return city_coords.get(c, (None, None))[1]
                val: Any = row.get('longitude')
                if val is None or pd.isna(val):
                    return None
                try:
                    return float(val)
                except Exception:
                    return None
            df_copy['latitude'] = df_copy.apply(_fill_lat, axis=1)
            df_copy['longitude'] = df_copy.apply(_fill_lon, axis=1)
            # Coerce to float where available
            try:
                df_copy['latitude'] = df_copy['latitude'].astype(float)
                df_copy['longitude'] = df_copy['longitude'].astype(float)
            except Exception:
                pass

        # Do not drop rows; allow missing values (schema-agnostic ingestion)
        df_cleaned = df_copy

        # Shuffle the DataFrame to ensure randomness
        df_shuffled = df_cleaned.sample(frac=1, random_state=1).reset_index(drop=True)

        df_final = (df_shuffled.head(rows_count).copy() if rows_count else df_shuffled.copy())

        # Replace values with True/False
        df_final = df_final.replace({'yes': True, 'no': False})

        # Normalize boolean columns: fill NaN -> False and coerce to bool
        bool_cols = [
            'has_parking', 'has_garden', 'has_pool', 'has_garage', 'has_bike_room',
            'is_furnished', 'pets_allowed', 'has_balcony', 'has_elevator'
        ]
        for col in bool_cols:
            if col in df_final.columns:
                series = df_final[col].fillna(False)
                series = series.map(lambda v: bool(v) if not pd.isna(v) else False)
                df_final.loc[:, col] = series

        # Replace int to float where applicable (avoid silent downcasting)
        def _to_float_series(s: pd.Series) -> pd.Series:
            try:
                return s.astype(float)
            except Exception:
                return s
        df_final = df_final.apply(lambda x: _to_float_series(x) if pd.api.types.is_integer_dtype(x) else x)

        # Bathrooms normalization (best effort)
        if 'bathrooms' not in df_final.columns and 'rooms' in df_final.columns:
            df_final['bathrooms'] = df_final['rooms'].apply(DataLoaderCsv.bathrooms_fake)
        elif 'bathrooms' in df_final.columns:
            df_final['bathrooms'] = df_final['bathrooms'].fillna(1.0)

        for field in ['has_garden', 'has_pool', 'has_garage', 'has_bike_room']:
            if field not in df_final.columns:
                df_final[field] = np.random.choice([True, False], size=len(df_final))
        if 'has_elevator' not in df_final.columns:
            df_final['has_elevator'] = np.random.choice([True, False], size=len(df_final))

        # Log added columns and final row count
        header_final = df_final.columns.tolist()
        diff_header = set(header_final) - set(header)

        if diff_header:
            logger.info(f'Added columns with generated data: {diff_header}')
        logger.info(f'Formatted data frame rows: {len(df_final)}')

        return df_final

