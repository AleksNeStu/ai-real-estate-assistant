import pandas as pd
import pytest
from data.csv_loader import DataLoaderCsv


def test_format_df_populates_lat_lon_for_known_city():
    df = pd.DataFrame({
        'city': ['Warsaw', 'UnknownCity'],
        'price': [5000, 3000],
        'rooms': [2, 1]
    })
    out = DataLoaderCsv.format_df(df)
    # Warsaw should get deterministic coords
    lat = out.loc[0, 'latitude']
    lon = out.loc[0, 'longitude']
    assert lat == pytest.approx(52.2297, abs=0.0001)
    assert lon == pytest.approx(21.0122, abs=0.0001)
    # UnknownCity stays None
    assert pd.isna(out.loc[1, 'latitude']) or out.loc[1, 'latitude'] is None
    assert pd.isna(out.loc[1, 'longitude']) or out.loc[1, 'longitude'] is None
