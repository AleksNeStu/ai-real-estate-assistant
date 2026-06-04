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

from core.security_utils import sanitize_for_log

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger

from config.settings import get_settings
from data.schemas import Property as PropertySchema
from db.models import (
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

USER_ROLES = ["user", "admin", "agent", "premium_user"]

LEAD_STATUSES = ["new", "contacted", "qualified", "converted", "lost"]

NOTIFICATION_TYPES = ["email", "push", "sms", "in_app"]

ACTIVITY_TYPES = ["search", "view", "favorite", "inquiry", "login"]


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

        for i in range(count):
            role = USER_ROLES[i % len(USER_ROLES)]
            user = User(
                id=str(uuid.uuid4()),
                email=f"demo.{role}{i + 1}@realestate.demo",
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
        """Generate properties and add to ChromaDB vector store."""
        properties = []

        for i in range(count):
            city = random.choice(list(CITIES.keys()))
            city_data = CITIES[city]
            district = random.choice(city_data["districts"])
            prop_type = random.choice(PROPERTY_TYPES)
            listing_type = random.choice(LISTING_TYPES)

            # Generate realistic price based on type and location
            base_price = {
                "Kraków": 400000,
                "Warsaw": 500000,
                "Gdańsk": 350000,
                "Wrocław": 380000,
                "Poznań": 420000,
            }[city]
            price_multiplier = {
                "apartment": 1.0,
                "studio": 0.7,
                "house": 1.5,
                "townhouse": 1.3,
                "loft": 1.2,
            }[prop_type]
            base_price = int(base_price * price_multiplier * random.uniform(0.5, 2.0))

            property_data = {
                "id": f"prop-{i + 1:04d}",
                "title": f"{random.choice(['Modern', 'Luxury', 'Cozy', 'Spacious', 'Elegant'])} {prop_type.capitalize()} in {district}",
                "address": f"ul. {random.choice(['Marszałkowska', 'Grodzka', 'Długa', 'Floriańska', 'Piotrkowska'])} {random.randint(1, 100)}, {district}, {city}, Poland",
                "city": city,
                "district": district,
                "price": base_price,
                "currency": "PLN",
                "rooms": random.randint(1, 5),
                "area_sqm": random.randint(25, 200),
                "property_type": prop_type,
                "listing_type": listing_type,
                "source_url": f"https://demo-real-estate.example.com/property/{i + 1}",
                "description": f"Beautiful {prop_type} in {district}. Features modern amenities, great location, and excellent connectivity.",
                "has_parking": random.choice([True, False]),
                "has_balcony": random.choice([True, False]),
                "has_elevator": random.choice([True, False]),
                "floor": random.randint(1, 10),
                "total_floors": random.randint(3, 15),
                "year_built": random.randint(1990, 2023),
                "latitude": city_data["lat"] + random.uniform(-0.05, 0.05),
                "longitude": city_data["lng"] + random.uniform(-0.05, 0.05),
                "created_at": (
                    datetime.now(UTC) - timedelta(days=random.randint(1, 180))
                ).isoformat(),
            }

            properties.append(PropertySchema(**property_data))
            self.property_ids.append(property_data["id"])

        # Add to ChromaDB
        vector_store = ChromaPropertyStore()

        batch_size = 50
        for i in range(0, len(properties), batch_size):
            batch = properties[i : i + batch_size]
            vector_store.add_properties(batch)
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
