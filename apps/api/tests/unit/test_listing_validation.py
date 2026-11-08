"""
Tests for the listing validation that used to delete whole listings.

Task #42: a listing priced below 50 and a title shorter than five
characters were rejected by the schema, the search router caught the error
and skipped the row, and the listing vanished from the results with only a
log line to show for it. A shared room at 45 EUR is a listing, not an
error.
"""

from data.schemas import Property


class TestTheSchemaKeepsUnusualListings:
    def test_a_short_title_is_a_title(self):
        prop = Property.model_validate({"city": "Krakow", "title": "ABC"})

        assert prop.title == "ABC"

    def test_a_missing_title_is_still_a_listing(self):
        prop = Property.model_validate({"city": "Krakow", "price": 500000})

        assert prop.title is None

    def test_a_shared_room_at_forty_five_keeps_its_price(self):
        prop = Property.model_validate({"city": "Berlin", "price": 45, "listing_type": "room"})

        assert prop.price == 45

    def test_a_price_below_fifty_is_not_rejected(self):
        # The check used to raise "Price suspiciously low (<50)" and the
        # listing was dropped from the search results.
        prop = Property.model_validate({"city": "Berlin", "price": 30})

        assert prop.price == 30

    def test_a_price_above_the_ceiling_is_not_rejected(self):
        prop = Property.model_validate({"city": "Warsaw", "price": 250_000_000})

        assert prop.price == 250_000_000

    def test_a_negative_price_is_still_refused(self):
        # The floor that matters is zero, and the field keeps it.
        try:
            Property.model_validate({"city": "Berlin", "price": -10})
        except Exception as exc:  # pydantic.ValidationError
            assert "price" in str(exc)
        else:  # pragma: no cover - the guard must hold
            raise AssertionError("a negative price must be refused")


class TestTheFailedFieldsHelper:
    def test_the_helper_names_the_offending_field(self):
        from pydantic import ValidationError

        from api.routers.search import _fields_that_failed

        try:
            Property.model_validate({"city": "Krakow", "latitude": 999})
        except ValidationError as exc:
            assert _fields_that_failed(exc) == {"latitude"}
        else:  # pragma: no cover - the guard must hold
            raise AssertionError("a latitude of 999 must be refused")

    def test_the_helper_never_names_the_city(self):
        from pydantic import ValidationError

        from api.routers.search import _fields_that_failed

        try:
            Property.model_validate({"price": 100})
        except ValidationError as exc:
            # Without a city there is nothing to show, so the row is skipped
            # rather than patched.
            assert _fields_that_failed(exc) == set()
        else:  # pragma: no cover - the guard must hold
            raise AssertionError("a listing without a city must be refused")
