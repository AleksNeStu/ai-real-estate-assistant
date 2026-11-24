"""A registered sale becomes a listing of the catalogue.

The conversion is the boundary between two vocabularies: the register holds
the prices people paid, and the catalogue holds what the app offers. These
tests hold that boundary to its own rules - the id names one sale and never
two, the price is the price of the deed, and the listing says what the
price is.
"""

from datetime import date
from typing import Any

from data.places import find_place
from data.rcn.rcn_catalogue import (
    catalogue_id,
    floor_phrase,
    listing_title,
    market_name,
    month_name,
    property_from_deed,
    street_title,
)
from data.rcn.rcn_models import RCNAddress, RCNTransaction


def _deed(**overrides: Any) -> RCNTransaction:
    """One registered sale, as the register writes it."""
    values: dict[str, Any] = {
        "external_id": "5CD7540E-F012-2DDC-E063-0C0A1EAC5265",
        "teryt": "1261",
        "address": RCNAddress(city="KRAKÓW", street="TOPOLOWA", number="48"),
        "area_sqm": 38.72,
        "price": 790_000.0,
        "transaction_date": date(2026, 8, 27),
        "market": "rynekWtorny",
        "rooms": 2,
        "floor": 4,
        "deed_reference": "Rep. A 18806/2026",
        "notary": "NOTARIUSZ NIEMIEC MATEUSZ",
        "source_url": "https://example.org/12_transakcje_ceny_lokale.parquet",
    }
    values.update(overrides)
    return RCNTransaction(**values)


def test_the_id_of_a_sale_names_that_sale() -> None:
    """The id is the register's own id, under a name of its own."""
    deed = _deed()
    assert catalogue_id(deed) == "rcn-5CD7540E-F012-2DDC-E063-0C0A1EAC5265"


def test_two_sales_never_share_an_id() -> None:
    """Two ids that fold to the same string are still two listings.

    The folding folds what an id may not carry away. Two different ids that
    fold alike would be one listing written twice, and the second write
    would silently replace the first.
    """
    first = catalogue_id(_deed(external_id="a/b"))
    second = catalogue_id(_deed(external_id="a-b"))
    assert first != second
    assert first.startswith("rcn-a-b-")
    assert second == "rcn-a-b"


def test_a_sale_without_a_price_is_not_a_listing() -> None:
    """There is nothing to show and nothing to compare."""
    place = find_place("Kraków")
    assert place is not None
    assert property_from_deed(_deed(price=0), place) is None
    assert property_from_deed(_deed(area_sqm=0), place) is None


def test_the_listing_carries_the_sale_and_says_what_it_is() -> None:
    """The listing names the flat, the deed and the price."""
    place = find_place("Kraków")
    assert place is not None
    listing = property_from_deed(_deed(), place)
    assert listing is not None

    assert listing.title == "2-room flat on Topolowa"
    assert listing.city == place.seed_name
    assert listing.region == place.region
    assert listing.listing_type == "sale"
    assert listing.property_type == "apartment"
    assert listing.price == 790_000.0
    assert listing.source_platform == "rcn"
    assert listing.source_url == "https://example.org/12_transakcje_ceny_lokale.parquet"
    assert listing.rooms == 2
    assert listing.floor == 4

    # The register knows no bathrooms and no degrees, so the listing claims
    # neither.
    assert listing.bathrooms is None
    assert listing.latitude is None
    assert listing.longitude is None

    description = listing.description or ""
    assert "18806/2026" in description
    assert "not an asking price" in description
    assert "27 August 2026" in description


def test_the_listing_carries_the_catalogue_s_spelling_of_its_city() -> None:
    """A listing is found under the city the catalogue knows.

    The catalogue writes Warsaw in one spelling and the register in another.
    A listing that carries the register's spelling is a listing of a city
    the catalogue does not know - and it would not be found next to the
    seeded flats of the same city.
    """
    place = find_place("Warszawa")
    assert place is not None
    listing = property_from_deed(
        _deed(
            external_id="5E55DF5E-BF28-1BE9-E063-0C0A1EACD335",
            address=RCNAddress(city="WARSZAWA", street="MARSZAŁKOWSKA", number="12"),
        ),
        place,
    )
    assert listing is not None
    assert listing.city == "Warsaw"
    assert listing.region == "mazowieckie"
    assert listing.district == "Śródmieście"
    assert listing.address == "ul. Marszałkowska 12, Śródmieście, Warsaw, Poland"


def test_the_floor_is_spoken_the_way_a_page_speaks_it() -> None:
    """The register counts the ground floor as zero."""
    assert floor_phrase(0) == "on the ground floor"
    assert floor_phrase(1) == "on the 1st floor"
    assert floor_phrase(2) == "on the 2nd floor"
    assert floor_phrase(3) == "on the 3rd floor"
    assert floor_phrase(4) == "on the 4th floor"
    assert floor_phrase(11) == "on the 11th floor"
    assert floor_phrase(12) == "on the 12th floor"
    assert floor_phrase(21) == "on the 21st floor"


def test_the_street_is_written_the_way_a_page_writes_it() -> None:
    """The register writes the street in capitals."""
    assert street_title("TOPOLOWA") == "Topolowa"
    assert street_title("AL. JEROZOLIMSKIE") == "Al. Jerozolimskie"


def test_a_street_with_a_hyphen_keeps_the_capital_of_every_part() -> None:
    """The city writes "Zwierzyniecka-Boczna", and so does the catalogue."""
    assert street_title("ZWIERZYNIECKA-BOCZNA") == "Zwierzyniecka-Boczna"


def test_the_address_of_a_street_that_carries_a_prefix_does_not_carry_two() -> None:
    """The register names the avenue with its prefix - "Al. Jerozolimskie"."""
    place = find_place("Kraków")
    assert place is not None
    listing = property_from_deed(
        _deed(address=RCNAddress(city="KRAKÓW", street="AL. JEROZOLIMSKIE", number="5")), place
    )
    assert listing is not None
    assert listing.address is not None
    assert listing.address.startswith("Al. Jerozolimskie 5")
    assert "ul." not in listing.address


def test_the_address_of_a_street_carries_the_prefix_of_a_street() -> None:
    """A street of the city is addressed the way the city addresses it."""
    place = find_place("Kraków")
    assert place is not None
    listing = property_from_deed(
        _deed(address=RCNAddress(city="KRAKÓW", street="TOPOLOWA", number="48")), place
    )
    assert listing is not None
    assert listing.address is not None
    assert listing.address.startswith("ul. Topolowa 48")


def test_the_month_is_named_in_the_words_of_the_site() -> None:
    """The name of a month does not depend on the locale of the machine.

    A deployment that runs under another locale would spell the same sale
    "August" and "agosto", and the catalogue of a listing would carry the
    date of a sale in two spellings.
    """
    assert month_name(1) == "January"
    assert month_name(8) == "August"
    assert month_name(12) == "December"


def test_the_market_is_named_in_the_words_of_the_site() -> None:
    """The register writes the market in one word and in capitals."""
    assert market_name("rynekWtorny") == "secondary market"
    assert market_name("RYNEKWTORNY") == "secondary market"
    assert market_name("rynekPierwotny") == "primary market"


def test_a_sale_without_a_street_is_named_after_its_city() -> None:
    """The register publishes sales it cannot put on a street."""
    place = find_place("Kraków")
    assert place is not None
    deed = _deed(address=RCNAddress(city="KRAKÓW", street="", number=""))
    assert listing_title(deed, place) == "2-room flat in Kraków"
    listing = property_from_deed(deed, place)
    assert listing is not None
    assert listing.district is None
    assert "Kraków" in (listing.address or "")


def test_a_street_the_catalogue_does_not_know_stays_without_a_district() -> None:
    """A street of no district of the city is not given a wrong one."""
    place = find_place("Kraków")
    assert place is not None
    listing = property_from_deed(
        _deed(address=RCNAddress(city="KRAKÓW", street="ULICA NIEZNANA", number="7")), place
    )
    assert listing is not None
    assert listing.district is None
    assert listing.neighborhood is None
    assert "ul. Ulica Nieznana 7" in (listing.address or "")
