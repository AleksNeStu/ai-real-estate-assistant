#!/usr/bin/env python3
"""
Comprehensive Demo Data Generator for AI Real Estate Assistant.

Generates maximum mock data to showcase ALL features:
- 250+ Properties via ChromaDB vector store
- 50 Users with different roles
- 100 Saved searches
- 200 Favorites
- 15 AI Agent profiles
- 30 Market analytics records
- 150 Leads/inquiries
- 300 Notifications
- 25 Comparison reports
- 20 CMA reports
- 40 Preference profiles
"""

import asyncio
import os
import random

# Add project root to path
import sys
import uuid
from datetime import UTC, datetime, timedelta

# Database imports
from sqlalchemy.ext.asyncio import AsyncSession

from core.password import hash_password
from core.security_utils import sanitize_for_log

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger

from config.settings import get_settings
from data.schemas import Property as PropertySchema
from db.models import (
    AgentListing,
    AgentProfile,
    CMAReportDB,
    FavoriteDB,
    Lead,
    SavedSearchDB,
    SearchEvent,
    SearchResultInteraction,
    User,
    UserActivityEvent,
    UserPreferenceProfile,
)
from vector_store.chroma_store import ChromaPropertyStore

# =============================================================================
# CONFIGURATION
# =============================================================================

CITIES = {
    "Kraków": {
        "districts": ["Old Town", "Kazimierz", "Podgórze", "Bronowice", "Zwierzyniec"],
        "lat": 50.0647,
        "lng": 19.9450,
    },
    "Warsaw": {
        "districts": ["Śródmieście", "Mokotów", "Wola", "Praga", "Żoliborz"],
        "lat": 52.2297,
        "lng": 21.0122,
    },
    "Gdańsk": {
        "districts": ["Main Town", "Wrzeszcz", "Oliwa", "Jelitkowo", "Brzeźno"],
        "lat": 54.3520,
        "lng": 18.6466,
    },
    "Wrocław": {
        "districts": ["Market Square", "Krzyki", "Fabryczna", "Psie Pole", "Stare Miasto"],
        "lat": 51.1079,
        "lng": 17.0385,
    },
    "Poznań": {
        "districts": ["Old Town", "Wilda", "Jeżyce", "Grunwald", "Winogrady"],
        "lat": 52.4064,
        "lng": 16.9252,
    },
}

PROPERTY_TYPES = ["apartment", "house", "studio", "loft", "townhouse"]
LISTING_TYPES = ["sale", "rent"]

# What a square meter of a flat costs in every city of the catalogue, in
# zloty. A listing's price is its area times this number, so the prices of
# the catalogue relate to each other the way the prices of a real market do.
CITY_PRICE_PER_SQM = {
    "Kraków": 6200,
    "Warsaw": 6800,
    "Gdańsk": 5400,
    "Wrocław": 5000,
    "Poznań": 5200,
}

# What a square meter rents for per month in the same cities.
CITY_RENT_PER_SQM = {
    "Kraków": 42,
    "Warsaw": 48,
    "Gdańsk": 38,
    "Wrocław": 36,
    "Poznań": 37,
}

# The voivodeship of every city, for the listing's region.
CITY_REGION = {
    "Kraków": "małopolskie",
    "Warsaw": "mazowieckie",
    "Gdańsk": "pomorskie",
    "Wrocław": "dolnośląskie",
    "Poznań": "wielkopolskie",
}

# How many square meters a room occupies in each kind of property. The area
# of a listing follows from its rooms, so a one-room loft is not 192 m².
SQ_M_PER_ROOM = {
    "studio": (24, 34),
    "apartment": (22, 30),
    "loft": (30, 45),
    "townhouse": (24, 32),
    "house": (22, 30),
}

# How many rooms and how many floors a kind of property has.
PROPERTY_SHAPE = {
    "studio": {"rooms": (1, 1), "floors": (3, 9)},
    "apartment": {"rooms": (2, 4), "floors": (3, 12)},
    "loft": {"rooms": (1, 2), "floors": (2, 6)},
    "townhouse": {"rooms": (3, 5), "floors": (2, 3)},
    "house": {"rooms": (4, 6), "floors": (1, 2)},
}

# The title of a listing, per kind of property. {district}, {rooms} and
# {adjective} are filled in.
TITLE_TEMPLATES = {
    "studio": [
        "Compact studio in {district}",
        "Bright studio with a separate kitchen in {district}",
        "Renovated studio in {district}",
    ],
    "apartment": [
        "{rooms} apartment in {district}",
        "{adjective} {rooms} apartment with a balcony in {district}",
        "Renovated {rooms} apartment in {district}",
    ],
    "loft": [
        "Loft in a former factory in {district}",
        "Industrial loft with high ceilings in {district}",
        "Converted loft in {district}",
    ],
    "townhouse": [
        "Townhouse with a garden in {district}",
        "Row house in {district}",
        "Family townhouse in {district}",
    ],
    "house": [
        "Detached house with a garden in {district}",
        "{adjective} family house in {district}",
        "House with a garage in {district}",
    ],
}

ROOMS_WORDS = {
    1: "One-room",
    2: "Two-room",
    3: "Three-room",
    4: "Four-room",
    5: "Five-room",
    6: "Six-room",
}

TITLE_ADJECTIVES = ["Sunny", "Spacious", "Bright", "Well-kept", "Quiet", "Renovated"]


def ordinal(number: int) -> str:
    """The English ordinal of a floor: 1st, 2nd, 3rd, 4th, 9th.

    The description used to read "on the 9 floor of a 9-floor building",
    which is how a reader learns to distrust the whole catalogue.
    """
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


# The centre of every district the catalogue uses. A listing stands in its
# district, not at the edge of the city: the comparable search scores the
# distance, and a listing of a district ten kilometres away from its
# neighbours scored nothing - the CMA wizard came up with an empty list.
DISTRICT_CENTRES = {
    "Kraków": {
        "Old Town": (50.0625, 19.9390),
        "Kazimierz": (50.0552, 19.9448),
        "Podgórze": (50.0510, 19.9600),
        "Bronowice": (50.0660, 19.9180),
        "Zwierzyniec": (50.0700, 19.9230),
    },
    "Warsaw": {
        "Śródmieście": (52.2310, 21.0060),
        "Mokotów": (52.1800, 21.0300),
        "Wola": (52.2350, 20.9700),
        "Praga": (52.2540, 21.0450),
        "Żoliborz": (52.2650, 20.9850),
    },
    "Gdańsk": {
        "Main Town": (54.3480, 18.6530),
        "Wrzeszcz": (54.3250, 18.6070),
        "Oliwa": (54.3560, 18.5560),
        "Jelitkowo": (54.3400, 18.5900),
        "Brzeźno": (54.3770, 18.6280),
    },
    "Wrocław": {
        "Market Square": (51.1070, 17.0260),
        "Krzyki": (51.0800, 17.0600),
        "Fabryczna": (51.0850, 17.0300),
        "Psie Pole": (51.1120, 17.0800),
        "Stare Miasto": (51.1050, 17.0400),
    },
    "Poznań": {
        "Old Town": (52.4070, 16.9300),
        "Wilda": (52.3950, 16.9100),
        "Jeżyce": (52.4200, 16.9000),
        "Grunwald": (52.4400, 16.9100),
        "Winogrady": (52.4200, 16.9400),
    },
}

# How far a listing strays from the centre of its district, in degrees.
# 0.006 of latitude is about 670 metres, 0.009 of longitude about 640.
DISTRICT_SPREAD_LAT = 0.006
DISTRICT_SPREAD_LNG = 0.009

# The streets of every city the catalogue uses, so a listing of a district
# carries an address of that city.
CITY_STREETS = {
    "Kraków": ["Floriańska", "Grodzka", "Długa", "Wierzbowa", "Kanonicza"],
    "Warsaw": ["Marszałkowska", "Nowy Świat", "Krucza", "Mokotowska", "Freta"],
    "Gdańsk": ["Długa", "Mariacka", "Piwna", "Jęczmienna", "Garbary"],
    "Wrocław": [
        "Świętego Mikołaja",
        "Oławska",
        "Kazimierza Wielkiego",
        "Św. Marcina",
        "Włodkowica",
    ],
    "Poznań": ["Długa", "Święty Marcin", "Główny", "Mickiewicza", "Naramowicka"],
}

# The streets of every district. A listing that stands in Zwierzyniec has to
# carry a street of Zwierzyniec - the street of another district is the
# kind of detail a visitor notices at once.
DISTRICT_STREETS: dict[str, dict[str, list[str]]] = {
    "Kraków": {
        "Old Town": ["Floriańska", "Grodzka", "Sienna", "Kanonicza", "Wielopole"],
        "Kazimierz": ["Kanonicza", "Bocheńska", "Józefa", "Wąska", "Jezuitów"],
        "Podgórze": ["Kalwaria", "Górka", "Kobierzyńska", "Rynkowa", "Lipowa"],
        "Bronowice": ["Bronowicka", "Styczna", "Cieszyńska", "Głowackiego", "Topolowa"],
        "Zwierzyniec": ["Zwierzyniecka", "Kościuszki", "Stradomska", "Gdańska", "Błonia"],
    },
    "Warsaw": {
        "Śródmieście": ["Marszałkowska", "Nowy Świat", "Krucza", "Chmielna", "Żurawia"],
        "Mokotów": ["Puławska", "Mokotowska", "Iwicka", "Kazimierzowska", "Racławicka"],
        "Wola": ["Aleje Jerozolimskie", "Woronicza", "Towarowa", "Kasprzyka", "Sokoła"],
        "Praga": ["Targowa", "Ząbkowska", "Brzeska", "Stalowa", "Kijowska"],
        "Żoliborz": [
            "Słowackiego",
            "Żeliborska",
            "Modzelewskiego",
            "Krasińskiego",
            "Czartoryskiego",
        ],
    },
    "Gdańsk": {
        "Main Town": ["Długa", "Mariacka", "Świętego Ducha", "Ogarna", "Frauengasse"],
        "Wrzeszcz": [
            "Wrzeszczyńska",
            "Słowackiego",
            "Skarżyńska",
            "Partyzantów",
            "Wojska Polskiego",
        ],
        "Oliwa": ["Aleja Grunwaldzka", "Pułaskiego", "Sobieskiego", "Abrahama", "Polna"],
        "Jelitkowo": ["Jelitkowska", "Nisułka", "Słoneczna", "Kartuska", "Słowackiego"],
        "Brzeźno": [
            "Brzeźnieńska",
            "Kliszewska",
            "Powstańców Warszawskich",
            "Kołobrzeska",
            "Rakoczego",
        ],
    },
    "Wrocław": {
        "Market Square": ["Rynek", "Szewska", "Włodkowica", "Kuźnicza", "Piotra Ściegiennego"],
        "Krzyki": [
            "Białawska",
            "Armii Krajowej",
            "Drobnera",
            "Powstańców Śląskich",
            "Kamiennogórska",
        ],
        "Fabryczna": ["Zelazna", "Bukowska", "Wrocławska", "Grabiszyńska", "Legnicka"],
        "Psie Pole": ["Dolnośląska", "Kwiatkowskiego", "Botaniczna", "Jaśminowa", "Słowiańska"],
        "Stare Miasto": ["Odrzańska", "Podwale", "Ruska", "Krasińskiego", "Wyszyńskiego"],
    },
    "Poznań": {
        "Old Town": ["Wielka", "Święty Marcin", "Żydowska", "Paderewskiego", "Wodna"],
        "Wilda": ["Piątkowska", "Garbary", "Wyszyńskiego", "Świętokrzyska", "Głogowska"],
        "Jeżyce": ["Słowackiego", "Dąbrowskiego", "Krasickiego", "Mickiewicza", "Bnieńska"],
        "Grunwald": ["Grunwaldzka", "FGSA", "Bukowiańska", "Skórzeccka", "Seweryna"],
        "Winogrady": ["Cieszkowskiego", "Pułaskiego", "Dołęgi", "Szypułkowska", "Lechicka"],
    },
}


def district_centre(city: str, district: str) -> tuple[float, float]:
    """The centre of a district - the point its listings are scattered around."""
    centres = DISTRICT_CENTRES.get(city)
    if centres is None:
        raise KeyError(f"unknown city: {city}")
    centre = centres.get(district)
    if centre is None:
        # A district the table does not know falls back to the centre of its
        # city, spread as wide as the old generator spread every listing.
        city_data = CITIES[city]
        return (city_data["lat"], city_data["lng"])
    return centre


def listing_coordinates(city: str, district: str) -> tuple[float, float]:
    """The coordinates of a listing - inside its district, near its centre."""
    lat, lng = district_centre(city, district)
    return (
        lat + random.uniform(-DISTRICT_SPREAD_LAT, DISTRICT_SPREAD_LAT),
        lng + random.uniform(-DISTRICT_SPREAD_LNG, DISTRICT_SPREAD_LNG),
    )


USER_ROLES = ["user", "admin", "agent", "premium_user"]

LEAD_STATUSES = ["new", "contacted", "qualified", "converted", "lost"]

NOTIFICATION_TYPES = ["email", "push", "sms", "in_app"]

ACTIVITY_TYPES = ["search", "view", "favorite", "inquiry", "login"]


def build_demo_listing(index: int) -> dict:
    """Build one listing of the demo catalogue.

    Every number of the listing is derived from the others: the area
    follows from the number of rooms, the floor is a floor of the building,
    the price is the area times the price of a square meter of that city and
    the amenities follow from the building. The numbers used to be drawn
    independently of each other, which is how the catalogue came to hold a
    192 m2 loft with one bathroom on the ninth floor of an eight-floor
    building.

    The function is pure enough to be tested: it touches no database and no
    vector store.
    """
    city = random.choice(list(CITIES.keys()))
    city_data = CITIES[city]
    district = random.choice(city_data["districts"])
    prop_type = random.choice(PROPERTY_TYPES)
    listing_type = random.choice(LISTING_TYPES)
    latitude, longitude = listing_coordinates(city, district)

    shape = PROPERTY_SHAPE[prop_type]
    rooms = random.randint(*shape["rooms"])
    area_sqm = int(round(rooms * random.uniform(*SQ_M_PER_ROOM[prop_type]) / 5) * 5)
    bathrooms = max(1, min(rooms, random.choice([1, 1, 2])))

    total_floors = random.randint(*shape["floors"])
    floor = random.randint(1, total_floors)

    # A house is older than a flat in a new block; a loft lives in a
    # building that was once something else.
    if prop_type in ("house", "townhouse"):
        year_built = random.randint(1955, 1995)
    elif prop_type == "loft":
        year_built = random.randint(1930, 1985)
    else:
        year_built = random.randint(1990, 2023)

    # The amenities follow from the building: a two-floor house has no
    # elevator, a flat on the first floor has no balcony.
    has_elevator = total_floors >= 4 and random.random() < 0.75
    has_balcony = prop_type in ("apartment", "loft") and floor > 1 and random.random() < 0.6
    has_parking = random.random() < 0.35
    has_garden = prop_type in ("house", "townhouse") and random.random() < 0.6
    has_garage = prop_type == "house" and random.random() < 0.5
    has_pool = random.random() < 0.05
    is_furnished = listing_type == "rent" and random.random() < 0.4
    pets_allowed = random.random() < 0.5

    price_per_sqm = CITY_PRICE_PER_SQM[city] if listing_type == "sale" else CITY_RENT_PER_SQM[city]
    price = area_sqm * price_per_sqm * random.uniform(0.85, 1.2)
    if listing_type == "sale":
        price = int(round(price / 1000.0) * 1000)
    else:
        price = int(round(price / 50.0) * 50)

    street = random.choice(DISTRICT_STREETS.get(city, {}).get(district) or CITY_STREETS[city])
    number = random.randint(1, 80)
    address = f"ul. {street} {number}, {district}, {city}, Poland"

    rooms_word = ROOMS_WORDS.get(rooms, f"{rooms}-room")
    title = random.choice(TITLE_TEMPLATES[prop_type]).format(
        district=district,
        rooms=rooms_word.lower(),
        adjective=random.choice(TITLE_ADJECTIVES),
    )

    amenities = []
    if has_balcony:
        amenities.append("a balcony")
    if has_elevator:
        amenities.append("an elevator")
    if has_parking:
        amenities.append("a parking space")
    if has_garden:
        amenities.append("a garden")
    if has_garage:
        amenities.append("a garage")
    if is_furnished:
        amenities.append("fully furnished rooms")
    amenities_sentence = (
        "The flat comes with " + ", ".join(amenities) + "."
        if amenities
        else "The flat has no special amenities."
    )

    if listing_type == "sale":
        price_sentence = (
            f"Asking price {price:,} PLN ({price / area_sqm:,.0f} PLN per square meter)."
        )
    else:
        price_sentence = f"Monthly rent {price:,} PLN."

    description = (
        f"{title}. {rooms_word} {prop_type} of {area_sqm} m² on the {ordinal(floor)} "
        f"floor of a {total_floors}-floor building in {district}, {city}, "
        f"built in {year_built}. {amenities_sentence} "
        f"A few minutes on foot from the {district} centre and the tram stop. "
        f"{price_sentence}"
    )

    return {
        "id": f"prop-{index + 1:04d}",
        "title": title,
        "address": address,
        "description": description,
        "country": "Poland",
        "region": CITY_REGION[city],
        "city": city,
        "district": district,
        "neighborhood": district,
        "price": price,
        "currency": "PLN",
        "price_per_sqm": round(price / area_sqm, 2),
        "rooms": rooms,
        "bathrooms": bathrooms,
        "area_sqm": area_sqm,
        "property_type": prop_type,
        "listing_type": listing_type,
        "source_url": f"https://demo-real-estate.example.com/property/{index + 1}",
        "has_parking": has_parking,
        "has_garden": has_garden,
        "has_pool": has_pool,
        "has_garage": has_garage,
        "is_furnished": is_furnished,
        "pets_allowed": pets_allowed,
        "has_balcony": has_balcony,
        "has_elevator": has_elevator,
        "floor": floor,
        "total_floors": total_floors,
        "year_built": year_built,
        "energy_rating": random.choice(["A", "B", "C", "D"]),
        "distance_to_transport": random.randint(80, 900),
        "distance_to_school": random.randint(150, 1800),
        "latitude": latitude,
        "longitude": longitude,
        # The moment the listing was scraped, not a moment the model does
        # not carry: the deployment's own panel counts how fresh the
        # catalogue is from it.
        "scraped_at": (datetime.now(UTC) - timedelta(days=random.randint(1, 180))).isoformat(),
        "source_platform": "demo-seed",
    }


# =============================================================================
# DEMO DATA GENERATOR CLASS
# =============================================================================


class ComprehensiveDemoDataGenerator:
    """Generate comprehensive demo data for AI Real Estate Assistant."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self.user_ids = []
        self.property_ids = []
        self.agent_ids = []

    async def generate_all(self) -> dict:
        """Generate all comprehensive demo data."""
        logger.info("Starting comprehensive demo data generation...")

        results = {}

        # 0. Clear existing demo data for clean state
        logger.info("Clearing existing demo data for clean state...")
        await self._clear_existing_data()

        # 1. Generate Users
        logger.info("Generating 50 users...")
        results["users"] = await self._generate_users(50)

        # 2. Generate Properties via ChromaDB
        logger.info("Generating 250+ properties...")
        results["properties"] = await self._generate_properties(250)

        # 3. Generate Saved Searches
        logger.info("Generating 100 saved searches...")
        results["saved_searches"] = await self._generate_saved_searches(100)

        # 4. Generate Favorites
        logger.info("Generating 200 favorites...")
        results["favorites"] = await self._generate_favorites(200)

        # 5. Generate AI Agents
        logger.info("Generating 15 AI agent profiles...")
        results["agents"] = await self._generate_agent_profiles(15)

        # 5b. Link the agents to the properties they represent. The directory
        # and the profile route both count the agent's ACTIVE listings, so
        # without these rows every agent reads zero.
        logger.info("Linking agents to their listings...")
        results["agent_listings"] = await self._generate_agent_listings()

        # 6. Generate Leads
        logger.info("Generating 150 leads...")
        results["leads"] = await self._generate_leads(150)

        # 7. Generate User Activity Events
        logger.info("Generating 300 activity events...")
        results["activities"] = await self._generate_activity_events(300)

        # 8. Generate Preference Profiles
        logger.info("Generating 40 preference profiles...")
        results["preferences"] = await self._generate_preference_profiles(40)

        # 9. Generate CMA Reports
        logger.info("Generating 20 CMA reports...")
        results["cma_reports"] = await self._generate_cma_reports(20)

        logger.info("Comprehensive demo data generation completed!")
        return results

    async def _clear_existing_data(self) -> None:
        """Clear all existing demo data for clean state."""
        from sqlalchemy import delete

        # Clear ChromaDB vector store first
        logger.info("Clearing ChromaDB vector store...")
        try:
            vector_store = ChromaPropertyStore()
            vector_store.clear()
            logger.info("ChromaDB vector store cleared")
        except Exception as e:
            logger.warning("Failed to clear ChromaDB (non-fatal): %s", sanitize_for_log(e))

        # Clear in reverse order of dependencies to avoid foreign key constraints
        logger.info("Clearing CMA reports...")
        await self.session.execute(delete(CMAReportDB))

        logger.info("Clearing preference profiles...")
        await self.session.execute(delete(UserPreferenceProfile))

        logger.info("Clearing activity events...")
        await self.session.execute(delete(UserActivityEvent))

        logger.info("Clearing leads...")
        await self.session.execute(delete(Lead))

        logger.info("Clearing agent profiles...")
        # The listings link agents to properties and carry a unique index on
        # (agent_id, property_id), so they are cleared BEFORE the profiles.
        await self.session.execute(delete(AgentListing))

        logger.info("Clearing agent profiles...")
        await self.session.execute(delete(AgentProfile))

        logger.info("Clearing favorites...")
        await self.session.execute(delete(FavoriteDB))

        logger.info("Clearing saved searches...")
        await self.session.execute(delete(SavedSearchDB))

        logger.info("Clearing search events and interactions...")
        await self.session.execute(delete(SearchResultInteraction))
        await self.session.execute(delete(SearchEvent))

        logger.info("Clearing users...")
        await self.session.execute(delete(User))

        await self.session.commit()
        logger.info("All existing demo data cleared successfully")

    async def _generate_users(self, count: int = 50) -> int:
        """Generate demo users."""
        users = []

        # The accounts are signable when the deployment says how. The
        # password is the deployment's own - it lives in its environment and
        # never in the repository - and without it the accounts carry no
        # password at all, exactly as before.
        demo_password = os.getenv("DEMO_USER_PASSWORD")
        hashed_password = hash_password(demo_password) if demo_password else None

        for i in range(count):
            role = USER_ROLES[i % len(USER_ROLES)]
            user = User(
                id=str(uuid.uuid4()),
                email=f"demo.{role}{i + 1}@realestate.demo",
                role=role,
                hashed_password=hashed_password,
                is_active=True,
                is_verified=True,
                created_at=datetime.now(UTC) - timedelta(days=random.randint(1, 365)),
                updated_at=datetime.now(UTC),
            )
            users.append(user)
            self.user_ids.append(user.id)

        self.session.add_all(users)
        await self.session.commit()
        return len(users)

    async def _generate_properties(self, count: int = 250) -> int:
        """Generate properties and add to ChromaDB vector store.

        Every listing is internally consistent - the floor is a floor of the
        building, the area follows from the number of rooms, the price is
        the area times the price of a square meter of that city. See
        ``build_demo_listing``.
        """
        properties = []

        for i in range(count):
            property_data = build_demo_listing(i)
            properties.append(PropertySchema(**property_data))
            self.property_ids.append(property_data["id"])

        # Add to ChromaDB
        vector_store = ChromaPropertyStore()

        batch_size = 50
        for i in range(0, len(properties), batch_size):
            batch = properties[i : i + batch_size]
            # The embedding of a batch is CPU bound. It runs in a worker thread so
            # the event loop keeps answering while the catalogue fills up - on a
            # small instance the seeding held the loop for minutes and the health
            # check of the deployment never got an answer.
            await asyncio.to_thread(vector_store.add_properties, batch)
            logger.info(
                "Added batch %s: %s properties", sanitize_for_log(i // batch_size + 1), len(batch)
            )

        return len(properties)

    async def _generate_saved_searches(self, count: int = 100) -> int:
        """Generate saved searches."""
        searches = []

        for _i in range(count):
            user_id = random.choice(self.user_ids)
            city = random.choice(list(CITIES.keys()))

            search = SavedSearchDB(
                id=str(uuid.uuid4()),
                user_id=user_id,
                name=f"{city} {random.choice(['apartment', 'house', 'studio'])} search",
                filters={
                    "city": city,
                    "property_type": random.choice(PROPERTY_TYPES),
                    "min_price": random.randint(100000, 300000),
                    "max_price": random.randint(400000, 800000),
                    "min_rooms": random.randint(1, 3),
                    "max_rooms": random.randint(3, 5),
                },
                alert_frequency=random.choice(["instant", "daily", "weekly", "none"]),
                is_active=random.choice([True, False]),
                notify_on_new=random.choice([True, False]),
                notify_on_price_drop=random.choice([True, False]),
                created_at=datetime.now(UTC) - timedelta(days=random.randint(1, 90)),
            )
            searches.append(search)

        self.session.add_all(searches)
        await self.session.commit()
        return len(searches)

    async def _generate_favorites(self, count: int = 200) -> int:
        """Generate favorite properties."""
        favorites = []
        seen_combinations = set()  # Track user_id + property_id combinations

        for _i in range(count):
            user_id = random.choice(self.user_ids)
            property_id = random.choice(self.property_ids)

            # Check for duplicates using set
            combination = f"{user_id}:{property_id}"
            if combination not in seen_combinations:
                seen_combinations.add(combination)
                favorite = FavoriteDB(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    property_id=property_id,
                    notes=random.choice(["", "Great location", "Needs renovation", "Good price"]),
                    created_at=datetime.now(UTC) - timedelta(days=random.randint(1, 60)),
                )
                favorites.append(favorite)

        self.session.add_all(favorites)
        await self.session.commit()
        return len(favorites)

    async def _generate_agent_profiles(self, count: int = 15) -> int:
        """Generate real estate agent profiles."""
        agents = []

        specialties_options = [
            ["residential", "commercial"],
            ["luxury", "investment"],
            ["residential", "new construction"],
            ["commercial", "industrial"],
            ["residential", "vacation"],
        ]

        # Use unique users for agents to avoid UNIQUE constraint on user_id
        agent_users = random.sample(self.user_ids, min(count, len(self.user_ids)))

        for i in range(count):
            if i >= len(agent_users):
                break  # Skip if we don't have enough unique users
            user_id = agent_users[i]
            specialty = specialties_options[i % len(specialties_options)]
            agency_names = [
                "Premium Estates",
                "City Living",
                "Global Properties",
                "Local Realty",
                "Elite Homes",
            ]

            agent = AgentProfile(
                id=str(uuid.uuid4()),
                user_id=user_id,
                agency_name=agency_names[i % len(agency_names)],
                license_number=f"RL-{random.randint(10000, 99999)}",
                license_state=random.choice(["CA", "NY", "TX", "FL", "IL"]),
                professional_email=f"agent.{i + 1}@{agency_names[i % len(agency_names)].lower().replace(' ', '')}.com",
                professional_phone=f"+1 {random.randint(200, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
                office_address=f"{random.randint(100, 999)} Main St, Suite {random.randint(100, 999)}, {random.choice(['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix'])}",
                specialties=specialty,
                service_areas=random.sample(list(CITIES.keys()), random.randint(2, 4)),
                property_types=random.sample(PROPERTY_TYPES, random.randint(2, 4)),
                languages=random.sample(["en", "es", "pl", "de", "fr"], random.randint(1, 3)),
                average_rating=round(random.uniform(3.5, 5.0), 1),
                total_reviews=random.randint(0, 500),
                total_sales=random.randint(0, 200),
                total_rentals=random.randint(0, 100),
                is_active=random.choice([True, False]),
                created_at=datetime.now(UTC) - timedelta(days=random.randint(30, 365)),
            )
            agents.append(agent)
            self.agent_ids.append(agent.id)

        self.session.add_all(agents)
        await self.session.commit()
        return len(agents)

    async def _generate_agent_listings(self) -> int:
        """Link the agents to the properties they represent.

        The agent directory's Listings column and the profile route's count
        both read this table - the count is the number of an agent's ACTIVE
        listings. Without the rows every agent reads zero, so the demo would
        show an empty column.
        """
        listings = []
        for agent_id in self.agent_ids:
            count = random.randint(4, 12)
            property_ids = random.sample(self.property_ids, min(count, len(self.property_ids)))
            for index, property_id in enumerate(property_ids):
                listings.append(
                    AgentListing(
                        id=str(uuid.uuid4()),
                        agent_id=agent_id,
                        property_id=property_id,
                        listing_type=random.choice(["sale", "rent", "both"]),
                        is_primary=index == 0,
                        is_active=True,
                        created_at=datetime.now(UTC) - timedelta(days=random.randint(1, 180)),
                    )
                )

        self.session.add_all(listings)
        await self.session.commit()
        return len(listings)

    async def _generate_leads(self, count: int = 150) -> int:
        """Generate leads/inquiries."""
        leads = []

        for i in range(count):
            lead = Lead(
                id=str(uuid.uuid4()),
                visitor_id=f"visitor-{i + 1}",
                user_id=random.choice(self.user_ids),
                email=f"lead.{i + 1}@demo.com",
                phone=f"+48 {random.randint(100, 999)} {random.randint(100, 999)} {random.randint(100, 999)}",
                name=f"Demo Lead {i + 1}",
                budget_min=random.randint(200000, 400000),
                budget_max=random.randint(500000, 800000),
                preferred_locations=random.sample(list(CITIES.keys()), random.randint(1, 3)),
                status=random.choice(LEAD_STATUSES),
                source=random.choice(["web", "mobile", "api", "referral"]),
                current_score=random.randint(0, 100),
                created_at=datetime.now(UTC) - timedelta(days=random.randint(1, 90)),
                updated_at=datetime.now(UTC),
            )
            leads.append(lead)

        self.session.add_all(leads)
        await self.session.commit()
        return len(leads)

    async def _generate_activity_events(self, count: int = 300) -> int:
        """Generate user activity events."""
        events = []

        for _i in range(count):
            event = UserActivityEvent(
                id=str(uuid.uuid4()),
                user_id_hash=hash(random.choice(self.user_ids)),
                session_id=f"demo-session-{random.randint(1, 100)}",
                event_type=random.choice(ACTIVITY_TYPES),
                event_category=random.choice(["search", "property", "favorites", "analytics"]),
                event_data={
                    "page": random.choice(["search", "property", "favorites", "analytics"]),
                    "duration": random.randint(10, 300),
                },
                duration_ms=random.randint(50, 5000),
                event_timestamp=datetime.now(UTC) - timedelta(days=random.randint(1, 30)),
            )
            events.append(event)

        self.session.add_all(events)
        await self.session.commit()
        return len(events)

    async def _generate_preference_profiles(self, count: int = 40) -> int:
        """Generate user preference profiles."""
        profiles = []

        # user_id is UNIQUE in UserPreferenceProfile, so sample unique users
        unique_users = random.sample(self.user_ids, min(count, len(self.user_ids)))

        for user_id in unique_users:
            profile = UserPreferenceProfile(
                id=str(uuid.uuid4()),
                user_id=user_id,
                preferred_cities=random.sample(list(CITIES.keys()), random.randint(1, 3)),
                preferred_price_min=float(random.randint(100000, 300000)),
                preferred_price_max=float(random.randint(500000, 1000000)),
                preferred_rooms=random.sample([1, 2, 3, 4, 5], random.randint(1, 3)),
                preferred_property_types=random.sample(PROPERTY_TYPES, random.randint(1, 3)),
                amenity_weights={
                    amenity: round(random.uniform(0.3, 1.0), 1)
                    for amenity in random.sample(
                        ["parking", "balcony", "elevator", "garden"], random.randint(1, 3)
                    )
                },
                view_count=random.randint(0, 500),
                favorite_count=random.randint(0, 100),
                search_count=random.randint(0, 200),
                created_at=datetime.now(UTC) - timedelta(days=random.randint(1, 60)),
                updated_at=datetime.now(UTC),
            )
            profiles.append(profile)

        self.session.add_all(profiles)
        await self.session.commit()
        return len(profiles)

    async def _generate_cma_reports(self, count: int = 20) -> int:
        """Generate CMA (Comparative Market Analysis) reports."""
        reports = []

        for _i in range(count):
            city = random.choice(list(CITIES.keys()))
            prop_id = random.choice(self.property_ids)

            report = CMAReportDB(
                id=str(uuid.uuid4()),
                user_id=random.choice(self.user_ids),
                status="completed",
                subject_property_id=prop_id,
                subject_data={
                    "property_id": prop_id,
                    "city": city,
                    "estimated_value": random.randint(300000, 700000),
                },
                comparables=[
                    {
                        "property_id": cid,
                        "similarity_score": round(random.uniform(0.7, 0.99), 2),
                        "adjustments": [],
                        "adjusted_price": random.randint(300000, 700000),
                    }
                    for cid in random.sample(self.property_ids, random.randint(3, 6))
                ],
                valuation={
                    "estimated_value": random.randint(300000, 700000),
                    "value_range_low": random.randint(250000, 400000),
                    "value_range_high": random.randint(500000, 800000),
                    "confidence_score": round(random.uniform(0.6, 0.95), 2),
                    "price_per_sqm": random.randint(5000, 12000),
                },
                market_context={
                    "avg_price_per_sqm": random.randint(5000, 12000),
                    "median_price": random.randint(350000, 600000),
                    "trend": random.choice(["up", "down", "stable"]),
                    "inventory_count": random.randint(10, 200),
                },
                created_at=datetime.now(UTC) - timedelta(days=random.randint(1, 30)),
            )
            reports.append(report)

        self.session.add_all(reports)
        await self.session.commit()
        return len(reports)


# =============================================================================
# MAIN GENERATION FUNCTION
# =============================================================================


async def generate_comprehensive_demo_data(session: AsyncSession) -> dict:
    """Generate comprehensive demo data for maximum feature showcase."""
    generator = ComprehensiveDemoDataGenerator(session)
    return await generator.generate_all()


if __name__ == "__main__":
    import asyncio

    from db.database import get_db_context

    async def main():
        async with get_db_context() as session:
            results = await generate_comprehensive_demo_data(session)
            print("\n✅ Comprehensive demo data generated:")
            print(f"   • {results['users']} users")
            print(f"   • {results['properties']} properties")
            print(f"   • {results['saved_searches']} saved searches")
            print(f"   • {results['favorites']} favorites")
            print(f"   • {results['agents']} agent profiles")
            print(f"   • {results['leads']} leads")
            print(f"   • {results['activities']} activity events")
            print(f"   • {results['preferences']} preference profiles")
            print(f"   • {results['cma_reports']} CMA reports")

    asyncio.run(main())
