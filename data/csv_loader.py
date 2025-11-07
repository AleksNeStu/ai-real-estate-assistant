from urllib.parse import urlparse
import streamlit as st
import numpy as np
import pandas as pd
import re

import requests

from common.cfg import *

# SettingWithCopyWarning: A value is trying to be set on a copy of a slice from a DataFrame
pd.options.mode.chained_assignment = None
# Set the pandas option to opt into future behavior
pd.options.future.no_silent_downcasting =True



class DataLoaderCsv:

    def __init__(
            self, csv_path: Path | URL
    ):
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
    def url_exists(url: URL):
        parsed_url = urlparse(str(url))
        is_valid_url = all([parsed_url.scheme, parsed_url.netloc])
        if not is_valid_url:
            return False  # URL structure is not valid
        try:
            response = requests.head(url, allow_redirects=True)
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

    def load_df(self):
        """Load CSV with flexible parsing to handle various formats."""
        csv_url = str(self.csv_path)

        # Convert GitHub URLs to raw format
        if isinstance(self.csv_path, (str, URL)):
            csv_url = self.convert_github_url_to_raw(csv_url)

        try:
            # Try loading with default settings first
            df = pd.read_csv(csv_url)
        except Exception as e:
            # If default fails, try with more flexible settings
            try:
                df = pd.read_csv(
                    csv_url,
                    encoding='utf-8',
                    on_bad_lines='skip',  # Skip bad lines instead of failing
                    engine='python'  # Use python engine for more flexibility
                )
            except Exception as e2:
                # Try with different encoding
                try:
                    df = pd.read_csv(
                        csv_url,
                        encoding='latin-1',
                        on_bad_lines='skip',
                        engine='python'
                    )
                except Exception as e3:
                    raise Exception(f"Failed to load CSV: {str(e)}. Additional attempts failed: {str(e2)}, {str(e3)}")

        print(f"Data frame loaded from {csv_url}, rows: {len(df)}")
        return df

    def load_format_df(self, df: pd.DataFrame):
        """Returns the DataFrame. If not loaded, loads and prepares the data first."""
        df_formatted = self.format_df(df)
        print(f"Data frame formatted from {self.csv_path}")
        return df_formatted

    @staticmethod
    def bathrooms_fake(rooms: float):
        # Add 'bathrooms': Either 1 or 2, check consistency with 'rooms' (e.g., bathrooms should be realistic)
        if pd.isna(rooms) or rooms < 2:
            return 1.0
        return np.random.choice([1.0, 2.0])

    @staticmethod
    def price_media_fake(price: float):
        # Add 'price_media': Fake values like internet, gas, electricity, not more than 20% of 'price'
        # Generate a fake price for utilities, up to 20% of the 'price'
        return round(np.random.uniform(0, 0.2 * price), 2)

    @staticmethod
    def camel_to_snake(name):
        """
        Convert camelCase to snake_case.
        """
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    @staticmethod
    def format_df(df: pd.DataFrame, rows_count=2000):
        # Get header
        header = df.columns.tolist()
        # print(f'Original header: ')

        # Drop rows with any NaN values
        df_copy = df.copy()
        print(f'Original data frame rows: {len(df_copy)}')

        # Camel case to snake for header first
        df_copy.columns = [
            DataLoaderCsv.camel_to_snake(col) for col in df_copy.columns]

        # Required columns - we need at least these for the app to work
        required_columns = ['price']

        # Check if we have at least price column
        if 'price' not in df_copy.columns:
            # Try to find a price-like column
            price_cols = [col for col in df_copy.columns if 'price' in col.lower() or 'cost' in col.lower() or 'rent' in col.lower()]
            if price_cols:
                df_copy = df_copy.rename(columns={price_cols[0]: 'price'})
            else:
                raise ValueError("CSV must have a price or rent column")

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

        if 'area' not in df_copy.columns:
            # Try to find area column
            area_cols = [col for col in df_copy.columns if any(x in col.lower() for x in ['area', 'size', 'sqm', 'square'])]
            if area_cols:
                df_copy = df_copy.rename(columns={area_cols[0]: 'area'})
            else:
                df_copy['area'] = 50.0

        # Drop rows where price is NaN (essential column)
        df_cleaned = df_copy.dropna(subset=['price'])

        # Get unique cities
        cities = df_cleaned['city'].unique() if 'city' in df_cleaned.columns else ['Unknown']
        cities_count = len(cities)

        # Shuffle the DataFrame to ensure randomness
        df_shuffled = df_cleaned.sample(frac=1, random_state=1).reset_index(drop=True)

        # Limit the overall number of rows to 2000
        df_final = df_shuffled.head(rows_count)

        # Replace values with True/False
        df_final.replace({'yes': True, 'no': False}, inplace=True)

        # Replace int to float
        df_final = df_final.apply(lambda x: x.astype(float) if pd.api.types.is_integer_dtype(x) else x)
        df_final_count = len(df_final)

        # Add fake (closer to real) data only if columns don't exist
        if 'price_media' not in df_final.columns:
            df_final['price_media'] = df_final['price'].apply(DataLoaderCsv.price_media_fake)

        if 'price_delta' not in df_final.columns:
            df_final['price_delta'] = np.array(np.random.choice(
                np.linspace(0,0.05,10),
                size=len(df_final)) * df_final['price']).astype(int)

        if 'negotiation_rate' not in df_final.columns:
            df_final['negotiation_rate'] = np.random.choice(
                ['high', 'middle', 'low'], p=[0.1, 0.6, 0.3], size=df_final_count)

        if 'bathrooms' not in df_final.columns:
            df_final['bathrooms'] = df_final['rooms'].apply(DataLoaderCsv.bathrooms_fake)

        if 'owner_name' not in df_final.columns:
            df_final['owner_name'] = [fake_pl.name() for _ in range(df_final_count)]

        if 'owner_phone' not in df_final.columns:
            df_final['owner_phone'] = [fake_pl.phone_number() for _ in range(df_final_count)]

        for field in ['has_garden', 'has_pool', 'has_garage', 'has_bike_room']:
            if field not in df_final.columns:
                df_final[field] = np.random.choice([True, False], size=len(df_final))

        #TODO: Add logic form expected header to generate missing values for any type of src data
        header_final = df_final.columns.tolist()
        # print(f'Final header: {header_final}')
        diff_header = set(header_final) - set(header)

        print(f'Added header with fake data: {diff_header}')
        print(f'Formatted data frame rows: {len(df_final)}')

        return df_final

