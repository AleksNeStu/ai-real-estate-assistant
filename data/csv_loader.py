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

    def load_df(self):
        df = pd.read_csv(str(self.csv_path))
        print(f"Data frame loaded from {self.csv_path}, rows: {len(df)}")
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
        df_cleaned = df_copy.dropna()
        # Camel case to snake for header
        df_cleaned.columns = [
            DataLoaderCsv.camel_to_snake(col) for col in df_cleaned.columns]

        # Get unique cities
        cities = df_cleaned['city'].unique()
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

        # Add fake (closer to real) data
        df_final['price_media'] = df_final['price'].apply(DataLoaderCsv.price_media_fake)
        df_final['price_delta'] = np.array(np.random.choice(
            np.linspace(0,0.05,10),
            size=len(df_final)) * df_final['price']).astype(int)
        df_final['negotiation_rate'] = np.random.choice(
            ['high', 'middle', 'low'], p=[0.1, 0.6, 0.3], size=df_final_count)
        df_final['bathrooms'] = df_final['rooms'].apply(DataLoaderCsv.bathrooms_fake)
        df_final['owner_name'] = [fake_pl.name() for _ in range(df_final_count)]
        df_final['owner_phone'] = [fake_pl.phone_number() for _ in range(df_final_count)]
        for field in ['has_garden', 'has_pool', 'has_garage', 'has_bike_room']:
            df_final[field] = np.random.choice([True, False], size=len(df_final))

        #TODO: Add logic form expected header to generate missing values for any type of src data
        header_final = df_final.columns.tolist()
        # print(f'Final header: {header_final}')
        diff_header = set(header_final) - set(header)

        print(f'Added header with fake data: {diff_header}')
        print(f'Formatted data frame rows: {len(df_final)}')

        return df_final

