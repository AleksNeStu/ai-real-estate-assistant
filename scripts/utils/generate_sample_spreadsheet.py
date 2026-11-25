#!/usr/bin/env python3
"""
Write the sample property spreadsheet that ships with the repository.

Zero-argument: every run rewrites the same two files with the same rows, so
the copy in the repository is always the output of this script and never a
hand-edited file that has drifted away from it. The CSV comes out byte for
byte the same; the workbook carries a creation timestamp, so its bytes differ
between runs even though its rows do not.

    samples/properties-sample.xlsx   the workbook - one sheet, named "Listings"
    samples/properties-sample.csv    the same rows as text

The rows are invented. Polish cities, prices in PLN, addresses on a street
that does not exist - nothing in the file is a real listing, and no address
points at a real door.

The column names are the field names of the property schema
(apps/api/data/schemas.py). The loader (apps/api/data/excel_loader.py) maps
those names onto the schema without guessing, which is why a file written
this way loads as it reads: the header names the field, and the row fills it.
A column the schema does not know is kept as an extra field and ignored, so
the file stays readable when the schema grows.

Run it with the same interpreter as the backend (the loader reads .xlsx
through openpyxl):

    python scripts/utils/generate_sample_spreadsheet.py
"""

import csv
import sys
from pathlib import Path
from typing import Any, Dict, List

# Repository root: scripts/utils/<this file> -> scripts/utils -> scripts -> root
REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DIR = REPO_ROOT / "samples"
XLSX_PATH = SAMPLE_DIR / "properties-sample.xlsx"
CSV_PATH = SAMPLE_DIR / "properties-sample.csv"

# The sheet name the admin panel shows in the sheet picker.
SHEET_NAME = "Listings"

# The columns, in the order they are written. Every name is a field of the
# property schema, so the loader maps the header onto the schema as it is.
COLUMNS = [
    "title",
    "description",
    "city",
    "district",
    "neighborhood",
    "address",
    "latitude",
    "longitude",
    "property_type",
    "listing_type",
    "rooms",
    "bathrooms",
    "area_sqm",
    "floor",
    "total_floors",
    "year_built",
    "energy_rating",
    "price",
    "currency",
    "deposit",
    "has_parking",
    "has_garage",
    "has_garden",
    "has_pool",
    "has_bike_room",
    "is_furnished",
    "pets_allowed",
    "has_balcony",
    "has_elevator",
    "distance_to_school",
    "distance_to_transport",
]

# The rows. Twelve apartments spread over eight Polish cities, six of them
# for rent and six for sale, plus a shared room and a house - the listing
# types the schema knows. The amenities are written as "yes" and "no" because
# that is what the loader reads them as.
#
# A numeric cell is never left empty. An empty cell arrives at the schema as
# NaN, and NaN fails the "greater than or equal to zero" the money fields
# carry - so an empty deposit would drop the listing instead of leaving the
# deposit unset. A listing that has no deposit writes a zero.
ROWS: List[Dict[str, Any]] = [
    {
        "title": "Two-room apartment in Srodmiescie",
        "description": (
            "Bright two-room apartment on the third floor, five minutes on foot "
            "from the main square, with a balcony over the courtyard."
        ),
        "city": "Krakow",
        "district": "Srodmiescie",
        "neighborhood": "Stare Miasto",
        "address": "ul. Przykladowa 12/4",
        "latitude": 50.0631,
        "longitude": 19.9472,
        "property_type": "apartment",
        "listing_type": "rent",
        "rooms": 2,
        "bathrooms": 1,
        "area_sqm": 48.5,
        "floor": 3,
        "total_floors": 6,
        "year_built": 2015,
        "energy_rating": "C",
        "price": 3200,
        "currency": "PLN",
        "deposit": 3200,
        "has_parking": "yes",
        "has_garage": "no",
        "has_garden": "no",
        "has_pool": "no",
        "has_bike_room": "yes",
        "is_furnished": "no",
        "pets_allowed": "yes",
        "has_balcony": "yes",
        "has_elevator": "yes",
        "distance_to_school": 350,
        "distance_to_transport": 120,
    },
    {
        "title": "Three-room apartment in Wola",
        "description": (
            "Three rooms in a low-rise block of the nineties, a parking space "
            "in the yard and the tram stop at the end of the street."
        ),
        "city": "Warsaw",
        "district": "Wola",
        "neighborhood": "Nalewy",
        "address": "ul. Przykladowa 7/3",
        "latitude": 52.2312,
        "longitude": 21.0105,
        "property_type": "apartment",
        "listing_type": "rent",
        "rooms": 3,
        "bathrooms": 1,
        "area_sqm": 71.0,
        "floor": 7,
        "total_floors": 12,
        "year_built": 2019,
        "energy_rating": "B",
        "price": 4500,
        "currency": "PLN",
        "deposit": 4500,
        "has_parking": "yes",
        "has_garage": "yes",
        "has_garden": "no",
        "has_pool": "no",
        "has_bike_room": "yes",
        "is_furnished": "no",
        "pets_allowed": "yes",
        "has_balcony": "yes",
        "has_elevator": "yes",
        "distance_to_school": 800,
        "distance_to_transport": 200,
    },
    {
        "title": "Studio near the market",
        "description": (
            "A small studio with a separate kitchen, furnished, on the second "
            "floor of an old town house."
        ),
        "city": "Wroclaw",
        "district": "Srodmiescie",
        "neighborhood": "Nadodrze",
        "address": "ul. Przykladowa 3/8",
        "latitude": 51.1096,
        "longitude": 17.0361,
        "property_type": "studio",
        "listing_type": "rent",
        "rooms": 1,
        "bathrooms": 1,
        "area_sqm": 29.0,
        "floor": 2,
        "total_floors": 5,
        "year_built": 1998,
        "energy_rating": "D",
        "price": 2200,
        "currency": "PLN",
        "deposit": 2200,
        "has_parking": "no",
        "has_garage": "no",
        "has_garden": "no",
        "has_pool": "no",
        "has_bike_room": "yes",
        "is_furnished": "yes",
        "pets_allowed": "no",
        "has_balcony": "no",
        "has_elevator": "no",
        "distance_to_school": 600,
        "distance_to_transport": 150,
    },
    {
        "title": "Four-room apartment with a garage",
        "description": (
            "Four rooms, a garage under the building and a balcony over the "
            "garden. The last floor of a small block."
        ),
        "city": "Poznan",
        "district": "Grunwald",
        "neighborhood": "Naramowice",
        "address": "ul. Przykladowa 21",
        "latitude": 52.4098,
        "longitude": 16.9189,
        "property_type": "apartment",
        "listing_type": "rent",
        "rooms": 4,
        "bathrooms": 2,
        "area_sqm": 88.0,
        "floor": 4,
        "total_floors": 4,
        "year_built": 2012,
        "energy_rating": "C",
        "price": 5200,
        "currency": "PLN",
        "deposit": 5200,
        "has_parking": "yes",
        "has_garage": "yes",
        "has_garden": "no",
        "has_pool": "no",
        "has_bike_room": "yes",
        "is_furnished": "no",
        "pets_allowed": "yes",
        "has_balcony": "yes",
        "has_elevator": "no",
        "distance_to_school": 450,
        "distance_to_transport": 400,
    },
    {
        "title": "New two-room apartment in Zaspa",
        "description": (
            "A new apartment in a building from 2021, with a bike room and a "
            "balcony facing the park."
        ),
        "city": "Gdansk",
        "district": "Zaspa",
        "neighborhood": "Jelitkowo",
        "address": "ul. Przykladowa 14/11",
        "latitude": 54.3547,
        "longitude": 18.6412,
        "property_type": "apartment",
        "listing_type": "rent",
        "rooms": 2,
        "bathrooms": 1,
        "area_sqm": 54.0,
        "floor": 9,
        "total_floors": 10,
        "year_built": 2021,
        "energy_rating": "A",
        "price": 3400,
        "currency": "PLN",
        "deposit": 3400,
        "has_parking": "yes",
        "has_garage": "no",
        "has_garden": "no",
        "has_pool": "no",
        "has_bike_room": "yes",
        "is_furnished": "no",
        "pets_allowed": "yes",
        "has_balcony": "yes",
        "has_elevator": "yes",
        "distance_to_school": 700,
        "distance_to_transport": 250,
    },
    {
        "title": "Two-room apartment in the centre",
        "description": (
            "A plain two-room apartment in a pre-war building, on the first "
            "floor, five minutes from the station."
        ),
        "city": "Katowice",
        "district": "Srodmiescie",
        "neighborhood": "Nikiszowiec",
        "address": "ul. Przykladowa 5/2",
        "latitude": 50.2663,
        "longitude": 19.0251,
        "property_type": "apartment",
        "listing_type": "rent",
        "rooms": 2,
        "bathrooms": 1,
        "area_sqm": 45.0,
        "floor": 1,
        "total_floors": 3,
        "year_built": 1985,
        "energy_rating": "E",
        "price": 2100,
        "currency": "PLN",
        "deposit": 2100,
        "has_parking": "no",
        "has_garage": "no",
        "has_garden": "no",
        "has_pool": "no",
        "has_bike_room": "no",
        "is_furnished": "no",
        "pets_allowed": "no",
        "has_balcony": "no",
        "has_elevator": "no",
        "distance_to_school": 900,
        "distance_to_transport": 300,
    },
    {
        "title": "Three-room apartment for sale in Podgorze",
        "description": (
            "Three rooms in a block from 2007, with a garage and a south-facing "
            "balcony. Close to the river and the old market."
        ),
        "city": "Krakow",
        "district": "Podgorze",
        "neighborhood": "Kazimierz",
        "address": "ul. Przykladowa 31/2",
        "latitude": 50.0521,
        "longitude": 19.9556,
        "property_type": "apartment",
        "listing_type": "sale",
        "rooms": 3,
        "bathrooms": 1,
        "area_sqm": 68.0,
        "floor": 2,
        "total_floors": 5,
        "year_built": 2007,
        "energy_rating": "C",
        "price": 890000,
        "currency": "PLN",
        "deposit": 0,
        "has_parking": "no",
        "has_garage": "yes",
        "has_garden": "no",
        "has_pool": "no",
        "has_bike_room": "yes",
        "is_furnished": "no",
        "pets_allowed": "yes",
        "has_balcony": "yes",
        "has_elevator": "no",
        "distance_to_school": 500,
        "distance_to_transport": 350,
    },
    {
        "title": "Four-room apartment for sale in Mokotow",
        "description": (
            "Four rooms on the fifth floor of a 2016 building, with a parking "
            "space and a garage. Two bathrooms and a utility room."
        ),
        "city": "Warsaw",
        "district": "Mokotow",
        "neighborhood": "Sielce",
        "address": "ul. Przykladowa 44/9",
        "latitude": 52.2146,
        "longitude": 21.0298,
        "property_type": "apartment",
        "listing_type": "sale",
        "rooms": 4,
        "bathrooms": 2,
        "area_sqm": 96.0,
        "floor": 5,
        "total_floors": 9,
        "year_built": 2016,
        "energy_rating": "B",
        "price": 1250000,
        "currency": "PLN",
        "deposit": 0,
        "has_parking": "yes",
        "has_garage": "yes",
        "has_garden": "no",
        "has_pool": "no",
        "has_bike_room": "yes",
        "is_furnished": "no",
        "pets_allowed": "yes",
        "has_balcony": "yes",
        "has_elevator": "yes",
        "distance_to_school": 650,
        "distance_to_transport": 180,
    },
    {
        "title": "Two-room apartment for sale in Olbin",
        "description": (
            "Two rooms on the third floor of a small block from the nineties, "
            "with a balcony over the river side."
        ),
        "city": "Wroclaw",
        "district": "Olbin",
        "neighborhood": "Wyspa",
        "address": "ul. Przykladowa 18/7",
        "latitude": 51.1152,
        "longitude": 17.0521,
        "property_type": "apartment",
        "listing_type": "sale",
        "rooms": 2,
        "bathrooms": 1,
        "area_sqm": 51.0,
        "floor": 3,
        "total_floors": 4,
        "year_built": 1996,
        "energy_rating": "D",
        "price": 640000,
        "currency": "PLN",
        "deposit": 0,
        "has_parking": "no",
        "has_garage": "no",
        "has_garden": "no",
        "has_pool": "no",
        "has_bike_room": "yes",
        "is_furnished": "no",
        "pets_allowed": "yes",
        "has_balcony": "yes",
        "has_elevator": "no",
        "distance_to_school": 550,
        "distance_to_transport": 400,
    },
    {
        "title": "Three-room apartment for sale near the main station",
        "description": (
            "Three rooms in a block from 2003, a garage in the basement and a "
            "lift. The station is a five-minute walk away."
        ),
        "city": "Gdansk",
        "district": "Srodmiescie",
        "neighborhood": "Dlugie Ogrody",
        "address": "ul. Przykladowa 9/15",
        "latitude": 54.3501,
        "longitude": 18.6489,
        "property_type": "apartment",
        "listing_type": "sale",
        "rooms": 3,
        "bathrooms": 1,
        "area_sqm": 74.0,
        "floor": 2,
        "total_floors": 6,
        "year_built": 2003,
        "energy_rating": "C",
        "price": 980000,
        "currency": "PLN",
        "deposit": 0,
        "has_parking": "no",
        "has_garage": "yes",
        "has_garden": "no",
        "has_pool": "no",
        "has_bike_room": "yes",
        "is_furnished": "no",
        "pets_allowed": "yes",
        "has_balcony": "no",
        "has_elevator": "yes",
        "distance_to_school": 400,
        "distance_to_transport": 100,
    },
    {
        "title": "Two-room apartment for sale in Lublin",
        "description": (
            "Two rooms on the top floor of a low block from 2011, with a "
            "balcony and a parking space in the yard."
        ),
        "city": "Lublin",
        "district": "Srodmiescie",
        "neighborhood": "Stare Miasto",
        "address": "ul. Przykladowa 2/12",
        "latitude": 51.2479,
        "longitude": 22.5701,
        "property_type": "apartment",
        "listing_type": "sale",
        "rooms": 2,
        "bathrooms": 1,
        "area_sqm": 49.0,
        "floor": 4,
        "total_floors": 4,
        "year_built": 2011,
        "energy_rating": "C",
        "price": 420000,
        "currency": "PLN",
        "deposit": 0,
        "has_parking": "no",
        "has_garage": "no",
        "has_garden": "no",
        "has_pool": "no",
        "has_bike_room": "yes",
        "is_furnished": "no",
        "pets_allowed": "yes",
        "has_balcony": "yes",
        "has_elevator": "no",
        "distance_to_school": 350,
        "distance_to_transport": 220,
    },
    {
        "title": "Three-room apartment for sale in the centre",
        "description": (
            "Three rooms on the sixth floor of a 2018 building, with a lift, a "
            "balcony and a parking space in the basement."
        ),
        "city": "Szczecin",
        "district": "Centrum",
        "neighborhood": "Drzetowo",
        "address": "ul. Przykladowa 26/6",
        "latitude": 53.4301,
        "longitude": 14.5488,
        "property_type": "apartment",
        "listing_type": "sale",
        "rooms": 3,
        "bathrooms": 1,
        "area_sqm": 66.0,
        "floor": 6,
        "total_floors": 10,
        "year_built": 2018,
        "energy_rating": "B",
        "price": 730000,
        "currency": "PLN",
        "deposit": 0,
        "has_parking": "yes",
        "has_garage": "no",
        "has_garden": "no",
        "has_pool": "no",
        "has_bike_room": "yes",
        "is_furnished": "no",
        "pets_allowed": "yes",
        "has_balcony": "yes",
        "has_elevator": "yes",
        "distance_to_school": 800,
        "distance_to_transport": 250,
    },
    {
        "title": "Room in a shared flat in Kazimierz",
        "description": (
            "A furnished room in a shared flat of four, in an old town "
            "building. The flat has one bathroom and a shared kitchen."
        ),
        "city": "Krakow",
        "district": "Podgorze",
        "neighborhood": "Kazimierz",
        "address": "ul. Przykladowa 33/9",
        "latitude": 50.0543,
        "longitude": 19.9538,
        "property_type": "apartment",
        "listing_type": "room",
        "rooms": 1,
        "bathrooms": 1,
        "area_sqm": 18.0,
        "floor": 4,
        "total_floors": 4,
        "year_built": 1930,
        "energy_rating": "F",
        "price": 1600,
        "currency": "PLN",
        "deposit": 800,
        "has_parking": "no",
        "has_garage": "no",
        "has_garden": "no",
        "has_pool": "no",
        "has_bike_room": "no",
        "is_furnished": "yes",
        "pets_allowed": "no",
        "has_balcony": "no",
        "has_elevator": "no",
        "distance_to_school": 600,
        "distance_to_transport": 250,
    },
    {
        "title": "House with a garden",
        "description": (
            "A detached house from 1990 with a fenced garden, a garage and a "
            "shed. The plot is planted and quiet at the back."
        ),
        "city": "Poznan",
        "district": "Naramowice",
        "neighborhood": "Strzeszyn",
        "address": "ul. Przykladowa 40",
        "latitude": 52.3985,
        "longitude": 16.9312,
        "property_type": "house",
        "listing_type": "sale",
        "rooms": 5,
        "bathrooms": 2,
        "area_sqm": 140.0,
        "floor": 1,
        "total_floors": 2,
        "year_built": 1990,
        "energy_rating": "D",
        "price": 1450000,
        "currency": "PLN",
        "deposit": 0,
        "has_parking": "yes",
        "has_garage": "yes",
        "has_garden": "yes",
        "has_pool": "no",
        "has_bike_room": "no",
        "is_furnished": "no",
        "pets_allowed": "yes",
        "has_balcony": "yes",
        "has_elevator": "no",
        "distance_to_school": 1200,
        "distance_to_transport": 900,
    },
]


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    """Write the rows as CSV: the header first, then one line per listing."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in COLUMNS})


def write_xlsx(path: Path, rows: List[Dict[str, Any]]) -> None:
    """Write the rows as a workbook with one sheet, named after the picker."""
    try:
        from openpyxl import Workbook
    except ImportError:
        sys.exit(
            "openpyxl is not installed. Run this with the interpreter of the "
            "backend - it is the reader the loader uses for .xlsx files."
        )

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = SHEET_NAME
    sheet.append(COLUMNS)
    for row in rows:
        sheet.append([row.get(column) for column in COLUMNS])
    workbook.save(path)


def main() -> int:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(CSV_PATH, ROWS)
    write_xlsx(XLSX_PATH, ROWS)

    print(f"{len(ROWS)} listings, {len(COLUMNS)} columns")
    print(f"  {XLSX_PATH.relative_to(REPO_ROOT).as_posix()}  (sheet: {SHEET_NAME})")
    print(f"  {CSV_PATH.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
