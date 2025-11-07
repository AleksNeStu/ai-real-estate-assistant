"""
Tests for saved searches and user preferences module.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from utils import SavedSearchManager, SavedSearch, UserPreferences, FavoriteProperty
from data.schemas import PropertyType


@pytest.fixture
def temp_storage():
    """Create temporary storage directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def search_manager(temp_storage):
    """Create SavedSearchManager with temp storage."""
    return SavedSearchManager(storage_path=temp_storage)


class TestSavedSearch:
    """Tests for SavedSearch model."""

    def test_saved_search_creation(self):
        """Test creating a saved search."""
        search = SavedSearch(
            id="search1",
            name="Affordable Apartments",
            city="Krakow",
            max_price=1000,
            min_rooms=2
        )

        assert search.id == "search1"
        assert search.name == "Affordable Apartments"
        assert search.city == "Krakow"
        assert search.max_price == 1000
        assert search.min_rooms == 2

    def test_saved_search_optional_fields(self):
        """Test saved search with optional fields."""
        search = SavedSearch(
            id="search2",
            name="Luxury Homes",
            description="High-end properties",
            min_price=2000,
            property_types=["house", "apartment"],
            must_have_parking=True,
            must_have_garden=True
        )

        assert search.description == "High-end properties"
        assert len(search.property_types) == 2
        assert search.must_have_parking is True
        assert search.must_have_garden is True

    def test_saved_search_defaults(self):
        """Test saved search default values."""
        search = SavedSearch(
            id="search3",
            name="Basic Search"
        )

        assert search.use_count == 0
        assert search.notify_on_new is False
        assert search.must_have_parking is False
        assert len(search.property_types) == 0

    def test_saved_search_matches_basic(self):
        """Test property matching with basic criteria."""
        search = SavedSearch(
            id="s1",
            name="Test",
            city="Krakow",
            max_price=1000
        )

        # Matching property
        prop1 = {
            'city': 'Krakow',
            'price': 800,
            'rooms': 2
        }
        assert search.matches(prop1) is True

        # Non-matching city
        prop2 = {
            'city': 'Warsaw',
            'price': 800,
            'rooms': 2
        }
        assert search.matches(prop2) is False

        # Price too high
        prop3 = {
            'city': 'Krakow',
            'price': 1200,
            'rooms': 2
        }
        assert search.matches(prop3) is False

    def test_saved_search_matches_price_range(self):
        """Test property matching with price range."""
        search = SavedSearch(
            id="s2",
            name="Mid-range",
            min_price=800,
            max_price=1500
        )

        # Within range
        prop1 = {'price': 1000, 'rooms': 2}
        assert search.matches(prop1) is True

        # Below minimum
        prop2 = {'price': 600, 'rooms': 2}
        assert search.matches(prop2) is False

        # Above maximum
        prop3 = {'price': 1600, 'rooms': 2}
        assert search.matches(prop3) is False

    def test_saved_search_matches_rooms(self):
        """Test property matching with room criteria."""
        search = SavedSearch(
            id="s3",
            name="2-3 bedrooms",
            min_rooms=2,
            max_rooms=3
        )

        assert search.matches({'rooms': 2, 'price': 1000}) is True
        assert search.matches({'rooms': 3, 'price': 1000}) is True
        assert search.matches({'rooms': 1, 'price': 1000}) is False
        assert search.matches({'rooms': 4, 'price': 1000}) is False

    def test_saved_search_matches_amenities(self):
        """Test property matching with amenity requirements."""
        search = SavedSearch(
            id="s4",
            name="With amenities",
            must_have_parking=True,
            must_have_garden=True
        )

        # Has both
        prop1 = {
            'price': 1000,
            'rooms': 2,
            'has_parking': True,
            'has_garden': True
        }
        assert search.matches(prop1) is True

        # Missing garden
        prop2 = {
            'price': 1000,
            'rooms': 2,
            'has_parking': True,
            'has_garden': False
        }
        assert search.matches(prop2) is False

    def test_saved_search_matches_property_type(self):
        """Test property matching with property type filter."""
        search = SavedSearch(
            id="s5",
            name="Apartments only",
            property_types=["apartment"]
        )

        # Matching type
        prop1 = {
            'price': 1000,
            'rooms': 2,
            'property_type': 'apartment'
        }
        assert search.matches(prop1) is True

        # Non-matching type
        prop2 = {
            'price': 1000,
            'rooms': 2,
            'property_type': 'house'
        }
        assert search.matches(prop2) is False

    def test_saved_search_to_query_string(self):
        """Test converting search to natural language query."""
        search = SavedSearch(
            id="s6",
            name="Test Search",
            city="Krakow",
            min_rooms=2,
            max_rooms=2,
            max_price=1000,
            must_have_parking=True
        )

        query = search.to_query_string()

        assert isinstance(query, str)
        assert 'Krakow' in query
        assert '2 rooms' in query or '2-bedroom' in query or 'with 2 rooms' in query
        assert '1000' in query
        assert 'parking' in query

    def test_saved_search_to_query_string_empty(self):
        """Test query string generation with no criteria."""
        search = SavedSearch(
            id="s7",
            name="Empty Search"
        )

        query = search.to_query_string()
        assert isinstance(query, str)
        assert len(query) > 0


class TestSavedSearchManager:
    """Tests for SavedSearchManager class."""

    def test_manager_initialization(self, temp_storage):
        """Test manager initialization."""
        manager = SavedSearchManager(storage_path=temp_storage)

        assert manager is not None
        assert Path(temp_storage).exists()
        assert len(manager.saved_searches) == 0

    def test_save_search(self, search_manager):
        """Test saving a search."""
        search = SavedSearch(
            id="test1",
            name="Test Search",
            city="Krakow"
        )

        result = search_manager.save_search(search)

        assert result.id == "test1"
        assert len(search_manager.saved_searches) == 1

    def test_save_search_update_existing(self, search_manager):
        """Test updating an existing search."""
        search1 = SavedSearch(
            id="test2",
            name="Original Name",
            city="Krakow"
        )
        search_manager.save_search(search1)

        # Update with same ID
        search2 = SavedSearch(
            id="test2",
            name="Updated Name",
            city="Warsaw"
        )
        search_manager.save_search(search2)

        # Should still have one search
        assert len(search_manager.saved_searches) == 1
        # Should have updated values
        retrieved = search_manager.get_search("test2")
        assert retrieved.name == "Updated Name"
        assert retrieved.city == "Warsaw"

    def test_get_search(self, search_manager):
        """Test retrieving a saved search."""
        search = SavedSearch(
            id="test3",
            name="Test Search",
            max_price=1200
        )
        search_manager.save_search(search)

        retrieved = search_manager.get_search("test3")

        assert retrieved is not None
        assert retrieved.id == "test3"
        assert retrieved.max_price == 1200

    def test_get_search_nonexistent(self, search_manager):
        """Test retrieving non-existent search."""
        result = search_manager.get_search("nonexistent")
        assert result is None

    def test_get_all_searches(self, search_manager):
        """Test getting all saved searches."""
        search1 = SavedSearch(id="s1", name="Search 1")
        search2 = SavedSearch(id="s2", name="Search 2")
        search3 = SavedSearch(id="s3", name="Search 3")

        search_manager.save_search(search1)
        search_manager.save_search(search2)
        search_manager.save_search(search3)

        all_searches = search_manager.get_all_searches()

        assert len(all_searches) == 3
        assert all(isinstance(s, SavedSearch) for s in all_searches)

    def test_delete_search(self, search_manager):
        """Test deleting a search."""
        search = SavedSearch(id="test4", name="To Delete")
        search_manager.save_search(search)

        assert len(search_manager.saved_searches) == 1

        result = search_manager.delete_search("test4")

        assert result is True
        assert len(search_manager.saved_searches) == 0

    def test_delete_search_nonexistent(self, search_manager):
        """Test deleting non-existent search."""
        result = search_manager.delete_search("nonexistent")
        assert result is False

    def test_increment_search_usage(self, search_manager):
        """Test incrementing search usage count."""
        search = SavedSearch(id="test5", name="Usage Test", use_count=0)
        search_manager.save_search(search)

        search_manager.increment_search_usage("test5")

        updated = search_manager.get_search("test5")
        assert updated.use_count == 1
        assert updated.last_used is not None

    def test_persistence(self, temp_storage):
        """Test that searches persist across manager instances."""
        # Create first manager and save search
        manager1 = SavedSearchManager(storage_path=temp_storage)
        search = SavedSearch(id="persist1", name="Persistent Search", city="Krakow")
        manager1.save_search(search)

        # Create second manager with same storage
        manager2 = SavedSearchManager(storage_path=temp_storage)

        # Should load existing searches
        assert len(manager2.saved_searches) == 1
        retrieved = manager2.get_search("persist1")
        assert retrieved.name == "Persistent Search"


class TestUserPreferences:
    """Tests for UserPreferences model."""

    def test_user_preferences_creation(self):
        """Test creating user preferences."""
        prefs = UserPreferences(
            default_sort="price_asc",
            results_per_page=20,
            show_map=True,
            max_budget=1500
        )

        assert prefs.default_sort == "price_asc"
        assert prefs.results_per_page == 20
        assert prefs.show_map is True
        assert prefs.max_budget == 1500

    def test_user_preferences_defaults(self):
        """Test default preference values."""
        prefs = UserPreferences()

        assert prefs.default_sort == "price_asc"
        assert prefs.results_per_page == 10
        assert prefs.show_map is True
        assert prefs.email_notifications is False

    def test_update_preferences(self, search_manager):
        """Test updating user preferences."""
        prefs = UserPreferences(
            default_sort="rooms",
            results_per_page=15,
            max_budget=2000,
            preferred_cities=["Krakow", "Warsaw"]
        )

        search_manager.update_preferences(prefs)
        retrieved = search_manager.get_preferences()

        assert retrieved.default_sort == "rooms"
        assert retrieved.results_per_page == 15
        assert "Krakow" in retrieved.preferred_cities

    def test_preferences_persistence(self, temp_storage):
        """Test preferences persist across manager instances."""
        manager1 = SavedSearchManager(storage_path=temp_storage)
        prefs = UserPreferences(max_budget=3000, preferred_cities=["Krakow"])
        manager1.update_preferences(prefs)

        manager2 = SavedSearchManager(storage_path=temp_storage)
        retrieved = manager2.get_preferences()

        assert retrieved.max_budget == 3000
        assert "Krakow" in retrieved.preferred_cities


class TestFavoriteProperty:
    """Tests for favorite properties functionality."""

    def test_favorite_property_creation(self):
        """Test creating a favorite property."""
        fav = FavoriteProperty(
            property_id="prop123",
            notes="Great location!",
            tags=["favorite", "krakow"]
        )

        assert fav.property_id == "prop123"
        assert fav.notes == "Great location!"
        assert len(fav.tags) == 2
        assert fav.added_at is not None

    def test_add_favorite(self, search_manager):
        """Test adding a property to favorites."""
        fav = search_manager.add_favorite(
            property_id="prop1",
            notes="Nice apartment",
            tags=["favorite"]
        )

        assert fav.property_id == "prop1"
        assert fav.notes == "Nice apartment"
        assert len(search_manager.favorite_properties) == 1

    def test_add_favorite_duplicate(self, search_manager):
        """Test adding same property to favorites twice."""
        search_manager.add_favorite("prop2", notes="First note")
        search_manager.add_favorite("prop2", notes="Updated note")

        # Should still have only one
        assert len(search_manager.favorite_properties) == 1

        # Should have updated notes
        favs = search_manager.get_favorites()
        assert favs[0].notes == "Updated note"

    def test_remove_favorite(self, search_manager):
        """Test removing a favorite property."""
        search_manager.add_favorite("prop3")
        assert len(search_manager.favorite_properties) == 1

        result = search_manager.remove_favorite("prop3")

        assert result is True
        assert len(search_manager.favorite_properties) == 0

    def test_remove_favorite_nonexistent(self, search_manager):
        """Test removing non-existent favorite."""
        result = search_manager.remove_favorite("nonexistent")
        assert result is False

    def test_get_favorites(self, search_manager):
        """Test getting all favorites."""
        search_manager.add_favorite("prop4", tags=["tag1"])
        search_manager.add_favorite("prop5", tags=["tag2"])
        search_manager.add_favorite("prop6", tags=["tag3"])

        favorites = search_manager.get_favorites()

        assert len(favorites) == 3
        assert all(isinstance(f, FavoriteProperty) for f in favorites)

    def test_is_favorite(self, search_manager):
        """Test checking if property is favorited."""
        search_manager.add_favorite("prop7")

        assert search_manager.is_favorite("prop7") is True
        assert search_manager.is_favorite("prop8") is False

    def test_favorites_persistence(self, temp_storage):
        """Test favorites persist across manager instances."""
        manager1 = SavedSearchManager(storage_path=temp_storage)
        manager1.add_favorite("persist_fav", notes="Test note")

        manager2 = SavedSearchManager(storage_path=temp_storage)

        assert manager2.is_favorite("persist_fav") is True
        favs = manager2.get_favorites()
        assert len(favs) == 1
        assert favs[0].notes == "Test note"


class TestStorageFiles:
    """Tests for storage file management."""

    def test_storage_files_created(self, temp_storage):
        """Test that storage files are created."""
        manager = SavedSearchManager(storage_path=temp_storage)

        # Save some data
        search = SavedSearch(id="s1", name="Test")
        manager.save_search(search)
        manager.add_favorite("prop1")
        prefs = UserPreferences(max_budget=1500)
        manager.update_preferences(prefs)

        # Check files exist
        storage_path = Path(temp_storage)
        assert (storage_path / "saved_searches.json").exists()
        assert (storage_path / "favorites.json").exists()
        assert (storage_path / "preferences.json").exists()

    def test_json_file_content(self, temp_storage):
        """Test JSON file content is valid."""
        manager = SavedSearchManager(storage_path=temp_storage)
        search = SavedSearch(id="json1", name="JSON Test", city="Krakow")
        manager.save_search(search)

        # Read and parse JSON file
        with open(Path(temp_storage) / "saved_searches.json", 'r') as f:
            data = json.load(f)

        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]['id'] == "json1"
        assert data[0]['name'] == "JSON Test"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_manager(self, search_manager):
        """Test operations on empty manager."""
        assert len(search_manager.get_all_searches()) == 0
        assert len(search_manager.get_favorites()) == 0
        assert search_manager.get_search("any") is None
        assert search_manager.is_favorite("any") is False

    def test_search_with_all_criteria(self):
        """Test search with maximum criteria specified."""
        search = SavedSearch(
            id="comprehensive",
            name="Comprehensive Search",
            description="All criteria",
            city="Krakow",
            min_price=500,
            max_price=2000,
            min_rooms=2,
            max_rooms=4,
            property_types=["apartment", "house"],
            must_have_parking=True,
            must_have_garden=True,
            must_have_pool=True,
            must_be_furnished=True,
            notify_on_new=True,
            notify_on_price_drop=True
        )

        # Should match property with all features
        prop = {
            'city': 'Krakow',
            'price': 1500,
            'rooms': 3,
            'property_type': 'apartment',
            'has_parking': True,
            'has_garden': True,
            'has_pool': True,
            'is_furnished': True
        }
        assert search.matches(prop) is True

        # Should not match if missing one feature
        prop_missing = {
            'city': 'Krakow',
            'price': 1500,
            'rooms': 3,
            'property_type': 'apartment',
            'has_parking': True,
            'has_garden': True,
            'has_pool': False,  # Missing pool
            'is_furnished': True
        }
        assert search.matches(prop_missing) is False
