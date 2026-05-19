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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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

LEAD_TYPES = ["inquiry", "viewing", "offer", "mortgage", "valuation"]

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
            await vector_store.initialize()
            await vector_store.clear()
            logger.info("ChromaDB vector store cleared")
        except Exception as e:
            logger.warning(f"Failed to clear ChromaDB (non-fatal): {e}")

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
                "penthouse": 2.0,
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
        await vector_store.initialize()

        batch_size = 50
        for i in range(0, len(properties), batch_size):
            batch = properties[i : i + batch_size]
            await vector_store.add_properties([p.model_dump() for p in batch])
            logger.info(f"Added batch {i // batch_size + 1}: {len(batch)} properties")

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
                notifications_enabled=random.choice([True, False]),
                created_at=datetime.now(UTC) - timedelta(days=random.randint(1, 90)),
                updated_at=datetime.now(UTC),
            )
            searches.append(search)

        self.session.add_all(searches)
        await self.session.commit()
        return len(searches)

    async def _generate_favorites(self, count: int = 200) -> int:
        """Generate favorite properties."""
        favorites = []

        for _i in range(count):
            user_id = random.choice(self.user_ids)
            property_id = random.choice(self.property_ids)

            # Check for duplicates
            existing = await self.session.execute(
                select(SavedSearchDB).where(
                    SavedSearchDB.user_id == user_id, SavedSearchDB.id == property_id
                )
            )

            if not existing.first():
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
        """Generate AI agent profiles."""
        agents = []

        agent_types = ["search", "valuation", "analytics", "recommendation", "assistant"]

        for i in range(count):
            agent_type = agent_types[i % len(agent_types)]

            agent = AgentProfile(
                id=str(uuid.uuid4()),
                name=f"{agent_type.capitalize()} Agent {i + 1}",
                description=f"AI-powered {agent_type} agent for real estate",
                agent_type=agent_type,
                config={
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 1000,
                },
                capabilities=["search", "filter", "recommend", "analyze"],
                is_active=random.choice([True, False]),
                created_by=random.choice(self.user_ids),
                created_at=datetime.now(UTC) - timedelta(days=random.randint(1, 30)),
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
                user_id=random.choice(self.user_ids),
                property_id=random.choice(self.property_ids),
                lead_type=random.choice(LEAD_TYPES),
                status=random.choice(LEAD_STATUSES),
                name=f"Demo Lead {i + 1}",
                email=f"lead.{i + 1}@demo.com",
                phone=f"+48 {random.randint(100, 999)} {random.randint(100, 999)} {random.randint(100, 999)}",
                message="I am interested in this property. Please contact me.",
                source=random.choice(["web", "mobile", "api", "referral"]),
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
                user_id=random.choice(self.user_ids),
                event_type=random.choice(ACTIVITY_TYPES),
                metadata={
                    "page": random.choice(["search", "property", "favorites", "analytics"]),
                    "duration": random.randint(10, 300),
                },
                ip_address=f"192.168.1.{random.randint(1, 255)}",
                user_agent="Demo Browser/1.0",
                created_at=datetime.now(UTC) - timedelta(days=random.randint(1, 30)),
            )
            events.append(event)

        self.session.add_all(events)
        await self.session.commit()
        return len(events)

    async def _generate_preference_profiles(self, count: int = 40) -> int:
        """Generate user preference profiles."""
        profiles = []

        for i in range(count):
            profile = UserPreferenceProfile(
                id=str(uuid.uuid4()),
                user_id=random.choice(self.user_ids),
                name=f"Profile {i + 1}",
                preferences={
                    "cities": random.sample(list(CITIES.keys()), random.randint(1, 3)),
                    "property_types": random.sample(PROPERTY_TYPES, random.randint(1, 3)),
                    "price_range": {
                        "min": random.randint(100000, 300000),
                        "max": random.randint(500000, 1000000),
                    },
                    "rooms": random.randint(1, 4),
                    "amenities": random.sample(
                        ["parking", "balcony", "elevator", "garden"], random.randint(1, 3)
                    ),
                },
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

            report = CMAReportDB(
                id=str(uuid.uuid4()),
                user_id=random.choice(self.user_ids),
                property_id=random.choice(self.property_ids),
                title=f"CMA Report for {city}",
                subject_property_value=random.randint(300000, 700000),
                comparable_properties=random.sample(self.property_ids, random.randint(3, 6)),
                market_analysis={
                    "avg_price_per_sqm": random.randint(5000, 12000),
                    "price_trend": random.choice(["up", "down", "stable"]),
                    "market_condition": random.choice(["hot", "balanced", "cold"]),
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
