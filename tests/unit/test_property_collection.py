import pandas as pd
from data.schemas import PropertyCollection, PropertyType


def test_from_dataframe_fills_id_and_source():
    df = pd.DataFrame({
        "city": ["Krakow", "Warsaw"],
        "price": [900, 1200],
        "rooms": [2, 3],
        "property_type": [PropertyType.APARTMENT, PropertyType.APARTMENT],
    })
    coll = PropertyCollection.from_dataframe(df, source="https://example.com/list.csv")
    assert coll.total_count == 2
    assert all(p.id for p in coll.properties)
    assert all(p.source_url == "https://example.com/list.csv" for p in coll.properties)


def test_to_search_text_contains_key_parts():
    df = pd.DataFrame({
        "city": ["Krakow"],
        "price": [900],
        "rooms": [2],
        "bathrooms": [1],
        "area_sqm": [50],
        "property_type": [PropertyType.APARTMENT],
        "has_parking": [True],
        "has_balcony": [True],
    })
    coll = PropertyCollection.from_dataframe(df, source="src")
    txt = coll.properties[0].to_search_text()
    assert "Property in Krakow" in txt
    assert "Monthly rent" in txt
    assert "Amenities" in txt


def test_filter_by_criteria_basic():
    df = pd.DataFrame({
        "city": ["Krakow", "Warsaw"],
        "price": [900, 1200],
        "rooms": [2, 3],
        "property_type": [PropertyType.APARTMENT, PropertyType.APARTMENT],
        "has_parking": [True, False],
    })
    coll = PropertyCollection.from_dataframe(df, source="src")
    filtered = coll.filter_by_criteria(city="Krakow", min_price=800, max_price=1000, min_rooms=2, has_parking=True)
    assert filtered.total_count == 1
