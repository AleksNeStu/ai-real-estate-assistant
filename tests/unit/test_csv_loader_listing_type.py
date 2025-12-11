import pandas as pd
from data.csv_loader import DataLoaderCsv


def test_format_df_sets_listing_type_default_rent_when_missing():
    df = pd.DataFrame({
        'city': ['Warsaw'],
        'price': [5000],
        'rooms': [2]
    })
    out = DataLoaderCsv.format_df(df)
    assert 'listing_type' in out.columns
    assert out.loc[0, 'listing_type'] == 'rent'


def test_format_df_renames_and_normalizes_listing_type():
    df = pd.DataFrame({
        'city': ['Berlin'],
        'price': [1200],
        'rooms': [2],
        'deal_type': ['for_rent']
    })
    out = DataLoaderCsv.format_df(df)
    assert 'listing_type' in out.columns
    assert out.loc[0, 'listing_type'] == 'rent'

