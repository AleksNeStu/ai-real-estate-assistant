import pandas as pd
from data.csv_loader import DataLoaderCsv


def test_format_df_adds_currency_default_pln_for_polish_cities():
    df = pd.DataFrame({
        'city': ['Warsaw', 'Krakow'],
        'price': [5000, 4500],
        'rooms': [2, 3],
        'area_sqm': [40, 60],
    })
    formatted = DataLoaderCsv.format_df(df)
    assert 'currency' in formatted.columns
    # expect PLN default because city is Polish
    assert set(formatted['currency'].unique()) == {'PLN'}


def test_format_df_renames_existing_currency_column():
    df = pd.DataFrame({
        'city': ['Berlin'],
        'price': [1200],
        'rooms': [2],
        'area_sqm': [50],
        'price_currency': ['EUR'],
    })
    formatted = DataLoaderCsv.format_df(df)
    assert 'currency' in formatted.columns
    assert formatted.loc[0, 'currency'] == 'EUR'

