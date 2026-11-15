"""
Seed ChromaDB with sample Polish property data.

Generates 60 realistic property listings across major Polish cities
and loads them into the ChromaPropertyStore vector store.

Usage:
    cd apps/api
    python scripts/seed_properties.py              # Seed with defaults
    python scripts/seed_properties.py --force       # Re-seed even if data exists
    python scripts/seed_properties.py --count 100   # Custom count
"""

import argparse
import io
import logging
import os
import random
import sys
import uuid
from pathlib import Path
from typing import cast

# Fix Windows console encoding for Polish characters
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Set env before any app imports
os.environ.setdefault("ENVIRONMENT", "local")

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.schemas import ListingType, Property, PropertyType

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Seed data definitions
# ---------------------------------------------------------------------------

CITIES = {
    "Kraków": {
        "region": "Małopolskie",
        "districts": [
            "Stare Miasto",
            "Kazimierz",
            "Podgórze",
            "Krowodrza",
            "Nowa Huta",
            "Bronowice",
            "Zwierzyniec",
            "Grzegórzki",
        ],
        "lat_range": (50.04, 50.10),
        "lon_range": (19.88, 20.02),
        "price_rent_sqm": (45, 95),
        "price_sale_sqm": (9000, 18000),
    },
    "Warszawa": {
        "region": "Mazowieckie",
        "districts": [
            "Śródmieście",
            "Mokotów",
            "Wilanów",
            "Wola",
            "Żoliborz",
            "Ursynów",
            "Praga-Południe",
            "Praga-Północ",
        ],
        "lat_range": (52.18, 52.31),
        "lon_range": (20.93, 21.10),
        "price_rent_sqm": (50, 110),
        "price_sale_sqm": (10000, 20000),
    },
    "Wrocław": {
        "region": "Dolnośląskie",
        "districts": ["Stare Miasto", "Krzyki", "Fabryczna", "Psie Pole", "Oława", "Śródmieście"],
        "lat_range": (51.06, 51.15),
        "lon_range": (16.85, 17.10),
        "price_rent_sqm": (40, 85),
        "price_sale_sqm": (8000, 16000),
    },
    "Gdańsk": {
        "region": "Pomorskie",
        "districts": ["Stare Miasto", "Wrzeszcz", "Oliwa", "Przymorze", "Żabianka", "Orunia"],
        "lat_range": (54.33, 54.40),
        "lon_range": (18.55, 18.70),
        "price_rent_sqm": (40, 90),
        "price_sale_sqm": (8500, 17000),
    },
    "Poznań": {
        "region": "Wielkopolskie",
        "districts": ["Stare Miasto", "Jeżyce", "Wilda", "Łazarz", "Winogrady", "Piątkowo"],
        "lat_range": (52.38, 52.47),
        "lon_range": (16.85, 17.00),
        "price_rent_sqm": (35, 80),
        "price_sale_sqm": (7500, 15000),
    },
}

STREET_NAMES = {
    "Kraków": [
        "Floriańska",
        "Grodzka",
        "Dietla",
        "Starowiślna",
        "Krakowska",
        "Weseła",
        "Miodowa",
        "Józefińska",
        "Tatarska",
        "Wrocławska",
    ],
    "Warszawa": [
        "Marszałkowska",
        "Nowy Świat",
        "Krakowskie Przedmieście",
        "Tamka",
        "Poznańska",
        "Hoża",
        "Koszykowa",
        "Ludna",
        "Gagarina",
        "KEN",
    ],
    "Wrocław": [
        "Rynek",
        "Świdnicka",
        "Legnicka",
        "Grabiszyńska",
        "Powstańców Śląskich",
        "Księcia Witolda",
        "Hugona Kołłątaja",
        "Zwycięska",
    ],
    "Gdańsk": [
        "Długa",
        "Długi Targ",
        "Grunwaldzka",
        "Kołobrzeska",
        "Bohaterów Getta",
        "Heweliusza",
        "Opolska",
        "Startowa",
    ],
    "Poznań": [
        "Święty Marcin",
        "Piekary",
        "27 Grudnia",
        "Fredry",
        "Gwarna",
        "Matejki",
        "Bukowska",
        "Polna",
    ],
}

DESCRIPTIONS = {
    "apartment": [
        "Bright and spacious apartment with modern finishes in a well-maintained building.",
        "Renovated apartment in a historic tenement house with high ceilings and original details.",
        "Modern apartment in a newly built development with underground parking and 24h security.",
        "Cozy apartment with balcony overlooking a quiet courtyard, close to public transport.",
        "Elegant apartment with open-plan kitchen and large living room, ideal for professionals.",
        "Functional apartment in a green neighborhood, near schools and shopping centers.",
        "Stylish apartment with panoramic city views, fully equipped kitchen.",
        "Family-friendly apartment near parks with playground and sports facilities.",
    ],
    "house": [
        "Detached house with garden in a quiet suburban neighborhood, excellent for families.",
        "Semi-detached house with garage and private backyard, close to schools.",
        "Modern house with energy-efficient design and smart home features.",
        "Renovated house with large terrace and barbecue area, great for entertaining.",
    ],
    "studio": [
        "Compact studio with efficient layout, ideal for students or young professionals.",
        "Modern studio with kitchenette and separate sleeping area in city center.",
        "Bright studio with large windows and balcony, near public transport hub.",
    ],
}

AMENITY_COMBOS = [
    {"has_elevator": True, "has_balcony": True},
    {"has_parking": True, "has_elevator": True},
    {"has_garden": True, "has_parking": True},
    {"has_balcony": True, "is_furnished": True},
    {"has_elevator": True, "has_parking": True, "has_balcony": True},
    {"has_garage": True, "has_garden": True},
    {"has_balcony": True, "pets_allowed": True},
    {"has_elevator": True, "is_furnished": True, "has_balcony": True},
    {"has_parking": True, "has_balcony": True, "has_bike_room": True},
    {"has_garden": True, "has_balcony": True, "pets_allowed": True},
]

FLOOR_COMBOS = [
    (1, 4),
    (2, 5),
    (3, 6),
    (4, 10),
    (1, 3),
    (5, 8),
    (2, 4),
    (7, 12),
    (3, 5),
    (10, 16),
]


def generate_property(index: int) -> Property:
    """Generate a single realistic property listing."""
    city_name = random.choice(list(CITIES.keys()))
    city = CITIES[city_name]
    district = random.choice(city["districts"])

    listing_type = random.choices(
        [ListingType.RENT, ListingType.SALE],
        weights=[55, 45],
    )[0]

    property_type = random.choices(
        [PropertyType.APARTMENT, PropertyType.HOUSE, PropertyType.STUDIO],
        weights=[60, 20, 20],
    )[0]

    # Area based on property type
    if property_type == PropertyType.STUDIO:
        area = round(random.uniform(20, 42), 1)
        rooms = 1.0
    elif property_type == PropertyType.APARTMENT:
        rooms = random.choice([2.0, 3.0, 3.0, 4.0, 4.0, 5.0])
        area = round(rooms * random.uniform(15, 28), 1)
    else:  # house
        rooms = random.choice([4.0, 5.0, 5.0, 6.0, 7.0])
        area = round(rooms * random.uniform(18, 30), 1)

    # Price based on listing type and city
    if listing_type == ListingType.RENT:
        price_per_sqm = random.uniform(*cast(list[float], city["price_rent_sqm"]))
        price = round(area * price_per_sqm, 0)
    else:
        price_per_sqm = random.uniform(*cast(list[float], city["price_sale_sqm"]))
        price = round(area * price_per_sqm, 0)

    # Location
    lat = round(random.uniform(*cast(list[float], city["lat_range"])), 6)
    lon = round(random.uniform(*cast(list[float], city["lon_range"])), 6)
    street = random.choice(STREET_NAMES.get(city_name, ["Unknown"]))
    street_number = random.randint(1, 120)

    # Amenities
    amenities = random.choice(AMENITY_COMBOS)

    # Floor (apartments only)
    floor = None
    total_floors = None
    if property_type in (PropertyType.APARTMENT, PropertyType.STUDIO):
        floor, total_floors = random.choice(FLOOR_COMBOS)

    # Year built
    year_built = random.choices(
        [random.randint(1890, 1945), random.randint(1960, 1990), random.randint(2000, 2024)],
        weights=[15, 35, 50],
    )[0]

    # Description
    desc_pool = DESCRIPTIONS.get(property_type.value, DESCRIPTIONS["apartment"])
    description = random.choice(desc_pool)
    description += f" Located in {district}, {city_name}. {rooms:.0f} rooms, {area} sqm."
    if listing_type == ListingType.RENT:
        description += f" Rent: {price:.0f} PLN/month."
    else:
        description += f" Price: {price:.0f} PLN."

    title = f"{property_type.value.capitalize()} {area} sqm, {rooms:.0g} rooms — {district}, {city_name}"

    return Property(
        id=f"seed-{uuid.uuid4().hex[:8]}-{index:03d}",
        title=title,
        description=description,
        country="Poland",
        region=city["region"],
        city=city_name,
        district=district,
        address=f"ul. {street} {street_number}",
        latitude=lat,
        longitude=lon,
        property_type=property_type,
        listing_type=listing_type,
        rooms=rooms,
        bathrooms=1.0 if rooms <= 3 else random.choice([1.0, 2.0]),
        area_sqm=area,
        floor=floor,
        total_floors=total_floors,
        year_built=year_built,
        price=price,
        currency="PLN",
        price_per_sqm=round(price / area, 2) if area > 0 else None,
        deposit=round(price * random.uniform(1.0, 2.0))
        if listing_type == ListingType.RENT
        else None,
        source_platform="seed_data",
        **amenities,
    )


def main():
    parser = argparse.ArgumentParser(description="Seed ChromaDB with sample property data")
    parser.add_argument(
        "--count", type=int, default=60, help="Number of properties to generate (default: 60)"
    )
    parser.add_argument("--force", action="store_true", help="Force re-seed even if data exists")
    args = parser.parse_args()

    from vector_store.chroma_store import ChromaPropertyStore

    logger.info("Initializing ChromaPropertyStore...")
    store = ChromaPropertyStore()

    # Check existing data
    try:
        existing = store._get_vector_store()
        if existing:
            count = existing._collection.count()
            if count > 0 and not args.force:
                logger.info(f"Collection already has {count} documents. Use --force to re-seed.")
                return
            elif count > 0 and args.force:
                logger.info(f"Collection has {count} documents. Force re-seeding...")
    except Exception as e:
        logger.warning(f"Could not check existing data: {e}")

    # Generate properties
    random.seed(42)  # Reproducible data
    logger.info(f"Generating {args.count} properties...")
    properties = [generate_property(i) for i in range(args.count)]

    # Validate
    valid = []
    for p in properties:
        try:
            p.to_search_text()  # Validate it can generate search text
            valid.append(p)
        except Exception as e:
            logger.warning(f"Skipping invalid property {p.id}: {e}")

    logger.info(f"Generated {len(valid)} valid properties out of {args.count}")

    # Summary by city
    by_city = {}
    for p in valid:
        by_city.setdefault(p.city, []).append(p)
    for city, props in sorted(by_city.items()):
        rents = [p for p in props if p.listing_type == ListingType.RENT]
        sales = [p for p in props if p.listing_type == ListingType.SALE]
        logger.info(f"  {city}: {len(props)} properties ({len(rents)} rent, {len(sales)} sale)")

    # Load into vector store
    logger.info("Loading properties into ChromaDB...")
    added = store.add_properties(valid, batch_size=20)
    logger.info(f"Successfully added {added} properties to vector store")

    # Verify
    try:
        vs = store._get_vector_store()
        if vs:
            final_count = vs._collection.count()
            logger.info(f"Vector store now contains {final_count} documents")
    except Exception:
        pass

    logger.info("Seed complete!")


if __name__ == "__main__":
    main()
