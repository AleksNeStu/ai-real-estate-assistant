import numpy as np
import pandas as pd

from common.cfg import *

# SettingWithCopyWarning: A value is trying to be set on a copy of a slice from a DataFrame
pd.options.mode.chained_assignment = None
# Set the pandas option to opt into future behavior
pd.options.future.no_silent_downcasting =True

class DataLoaderLocalCsv:

    def __init__(
            self, file_path: Path = poland_csv, rows_count = 2000
    ):
        if not file_path.is_file():
            raise FileNotFoundError(f"The file at {file_path} does not exist.")
        self.file_path = file_path
        self.rows_count = rows_count
        self._df: pd.DataFrame | None = None
        self._df_formatted: pd.DataFrame | None = None


    @property
    def df(self):
        if not self._df:
            self._df = pd.read_csv(self.file_path)
            print(f"Data frame loaded from {self.file_path}")
        return self._df


    @property
    def df_formatted(self):
        """Returns the DataFrame. If not loaded, loads and prepares the data first."""
        if not self._df_formatted:
            self._df_formatted = self.format_df(self.df)
            print(f"Data frame formatted from {self.file_path}")
        return self._df_formatted

    def bathrooms_fake(self, rooms: float):
        # Add 'bathrooms': Either 1 or 2, check consistency with 'rooms' (e.g., bathrooms should be realistic)
        if pd.isna(rooms) or rooms < 2:
            return 1.0
        return np.random.choice([1.0, 2.0])

    def price_media_fake(self, price: float):
        # Add 'price_media': Fake values like internet, gas, electricity, not more than 20% of 'price'
        # Generate a fake price for utilities, up to 20% of the 'price'
        return round(np.random.uniform(0, 0.2 * price), 2)

    def format_df(self, df: pd.DataFrame):
        # Get header
        header = df.columns.tolist()
        # print(f'Original header: ')

        # Drop rows with any NaN values
        df_cleaned = df.copy()
        print(f'Original data frame rows: {len(df_cleaned)}')
        df_cleaned = df_cleaned.dropna()

        # Get unique cities
        cities = df_cleaned['city'].unique()
        cities_count = len(cities)

        # Shuffle the DataFrame to ensure randomness
        df_shuffled = df_cleaned.sample(frac=1, random_state=1).reset_index(drop=True)

        # Limit the overall number of rows to 2000
        df_final = df_shuffled.head(self.rows_count)

        # Replace values with True/False
        df_final.replace({
            'yes': True,
            'no': False
        }, inplace=True)

        # Replace int to float
        df_final = df_final.apply(lambda x: x.astype(float) if pd.api.types.is_integer_dtype(x) else x)

        # Add fake (closer to real) data
        df_final['price_media'] = df_final['price'].apply(self.price_media_fake)
        df_final['bathrooms'] = df_final['rooms'].apply(self.bathrooms_fake)
        for field in ['hasGarden', 'hasPool', 'hasGarage', 'hasBikeRoom']:
            df_final[field] = np.random.choice([True, False], size=len(df_final))

        #TODO: Add logic form expected header to generate missing values for any type of src data
        header_final = df_final.columns.tolist()
        # print(f'Final header: {header_final}')
        diff_header = set(header_final) - set(header)

        print(f'Added header with fake data: {diff_header}')
        print(f'Formatted data frame rows: {len(df_final)}')

        return df_final

