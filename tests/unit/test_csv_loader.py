import pandas as pd
import pytest
from pathlib import Path
import tempfile
from data.csv_loader import DataLoaderCsv


def test_convert_github_url_to_raw():
    u = "https://github.com/user/repo/blob/main/data.csv"
    r = DataLoaderCsv.convert_github_url_to_raw(u)
    assert r == "https://raw.githubusercontent.com/user/repo/main/data.csv"


def test_format_df_adds_missing_columns_and_normalizes():
    df = pd.DataFrame({
        "City": ["Krakow", None],
        "Rooms": [2, None],
        "Price": [900, 1200],
        "has_parking": ["yes", None],
        "has_balcony": [1, 0],
    })
    out = DataLoaderCsv.format_df(df)
    assert "city" in out.columns
    assert "rooms" in out.columns
    assert "bathrooms" in out.columns
    assert out.loc[0, "has_parking"] in (True, False)
    assert isinstance(out.loc[0, "rooms"], float)
    assert len(out) == 2


def test_bathrooms_fake_logic():
    assert DataLoaderCsv.bathrooms_fake(1.0) == 1.0
    v = DataLoaderCsv.bathrooms_fake(3.0)
    assert v in (1.0, 2.0)


def test_load_df_reads_csv_from_path():
    df_in = pd.DataFrame({"city": ["Krakow"], "price": [900], "rooms": [2]})
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "data.csv"
        df_in.to_csv(p, index=False)
        loader = DataLoaderCsv(p)
        df_out = loader.load_df()

    assert list(df_out.columns) == ["city", "price", "rooms"]
    assert len(df_out) == 1


def test_load_df_reads_excel_from_path():
    pytest.importorskip("openpyxl")

    df_in = pd.DataFrame({"city": ["Warsaw"], "price": [1200], "rooms": [3]})
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "data.xlsx"
        df_in.to_excel(p, index=False)
        loader = DataLoaderCsv(p)
        df_out = loader.load_df()

    assert list(df_out.columns) == ["city", "price", "rooms"]
    assert len(df_out) == 1

