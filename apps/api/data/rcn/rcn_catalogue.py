"""How a registered sale becomes a listing of the catalogue.

The register holds the prices people paid. The catalogue holds what the app
offers. A registered sale is not a listing - there is no asking price, no
seller and no photograph - but it is a flat, in a city, with an area, a
number of rooms and a price the market accepted. A catalogue built from the
register therefore says what every one of its listings is: a flat that really
changed hands, at that price, on that day, in the register's own words and
with the register's own export as its source.

The listing is honest about what the register does not know. The register
publishes the position of a building in the Polish national projection
(PL-1992 metres), not in degrees, so the listing carries no coordinates
rather than a fabricated pair of them. It does not say whether the flat has
a balcony or a lift either - the register knows no such thing - so the
listing claims none of them.
"""

import hashlib
import re
from typing import Optional

from data.places import Place, district_of_street
from data.rcn.rcn_models import RCNTransaction, normalize_text
from data.schemas import ListingType, Property, PropertyType

# The name the catalogue knows the register by. It is the same name the
# stored sales carry, so a listing and the sale behind it are one source.
REGISTER_SOURCE = "rcn"

# The markets the register names, in the words of the site. The register
# writes them in one word and in capitals.
_MARKETS = {
    "RYNEKWTORNY": "secondary market",
    "RYNEKPIERWOTNY": "primary market",
}

# The letters an id of the catalogue may carry: the register's own feature
# id, with everything that is not a letter or a digit folded away.
_ID_UNSAFE = re.compile(r"[^A-Za-z0-9_-]+")

# The months in the words of the site. The name of a month is written here
# and not read from the locale of the machine: a deployment that runs under
# another locale would spell the same sale "August" and "agosto", and the
# catalogue of a listing would carry the date of a sale in two spellings.
_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def month_name(month: int) -> str:
    """The name of a month, in the words of the site."""
    return _MONTHS[month - 1]


def catalogue_id(deed: RCNTransaction) -> str:
    """The id a registered sale is listed under.

    The register's own feature id names one flat, so the id is that id
    under a name of its own: a listing of the register and a listing of
    another source are two listings, and the catalogue tells them apart by
    their id alone.

    Two different ids that fold to the same string would be one listing
    written twice, so a folding that loses anything carries a digest of the
    id it came from.
    """
    safe = _ID_UNSAFE.sub("-", deed.external_id).strip("-")
    if safe != deed.external_id:
        digest = hashlib.sha256(deed.external_id.encode("utf-8")).hexdigest()[:8]
        safe = f"{safe}-{digest}"
    return f"rcn-{safe}"


def street_title(street: str) -> str:
    """The register's spelling of a street, in the spelling of the pages.

    The register writes the street in capitals; the catalogue writes it the
    way a page names it. A street the register writes with a hyphen keeps
    the capital of every part of it - "Zwierzyniecka-Boczna" - because that
    is how the city writes it.
    """
    words = []
    for word in (street or "").split():
        words.append("-".join(part[:1].upper() + part[1:].lower() for part in word.split("-")))
    return " ".join(words)


def market_name(market: str) -> str:
    """The market a sale happened in, in the words of the site."""
    folded = normalize_text(market).replace(" ", "")
    return _MARKETS.get(folded, market or "")


def _ordinal(number: int) -> str:
    """The ordinal of a number: 1st, 2nd, 3rd, 4th."""
    if 11 <= number % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def floor_phrase(floor: int) -> str:
    """The floor of a building, the way a page says it.

    The register counts the ground floor as zero and the cellars as the
    floors below it.
    """
    if floor == 0:
        return "on the ground floor"
    return f"on the {_ordinal(floor)} floor"


# The prefixes the register writes a street with. A street the register
# names with one of them carries it already - "AL. JEROZOLIMSKIE" is the
# avenue, prefix and all - and a street it does not is a street of the
# city, and "ul." is what a Polish address carries.
_STREET_PREFIXES = frozenset({"al", "ul", "pl", "os", "pk", "r"})


def _street_prefix(street: str) -> str:
    """The prefix the address of a street carries, if it needs one."""
    first = street.split(" ", 1)[0].lower().rstrip(".")
    if first in _STREET_PREFIXES:
        return ""
    return "ul."


def listing_title(deed: RCNTransaction, place: Place) -> str:
    """The title of the listing."""
    street = street_title(deed.address.street)
    rooms = f"{deed.rooms}-room " if deed.rooms else ""
    if street:
        return f"{rooms}flat on {street}"
    return f"{rooms}flat in {place.name}"


def listing_description(deed: RCNTransaction, place: Place, district: Optional[str]) -> str:
    """What the listing says about the sale behind it.

    The price is the price the buyer paid. The listing says so, so that
    nobody reads it as an asking price.
    """
    where = district or place.name
    subject = f"A {deed.rooms}-room flat" if deed.rooms else "A flat"
    subject += f" of {deed.area_sqm:g} m²"
    if deed.floor is not None and deed.floor >= 0:
        subject += f" {floor_phrase(deed.floor)}"
    subject += f" in {where}."

    sentences = [
        subject,
        (
            f"Sold for {deed.price:,.0f} PLN ({deed.price_per_sqm:,.0f} PLN per square meter) "
            f"on {deed.transaction_date.day} "
            f"{month_name(deed.transaction_date.month)} {deed.transaction_date.year}, in the "
            f"official register of transaction prices."
        ),
    ]
    if deed.deed_reference:
        sentences.append(f"Deed {deed.deed_reference}.")
    market = market_name(deed.market)
    if market:
        sentences.append(f"{market[0].upper()}{market[1:]}.")
    sentences.append("The price is what the buyer paid, not an asking price.")
    return " ".join(sentences)


def property_from_deed(deed: RCNTransaction, place: Place) -> Optional[Property]:
    """The listing of a registered sale, or None when the sale cannot be one.

    A sale without a price or without an area is not a flat the catalogue can
    offer: there is nothing to show and nothing to compare.
    """
    if deed.price <= 0 or deed.area_sqm <= 0:
        return None

    district = district_of_street(place, deed.address.street)
    street = street_title(deed.address.street)

    address_parts = []
    if street:
        address_parts.append(f"{_street_prefix(street)} {street} {deed.address.number}".strip())
    if district is not None:
        address_parts.append(district.name)
    address_parts.append(place.seed_name)
    address_parts.append("Poland")

    return Property(
        id=catalogue_id(deed),
        title=listing_title(deed, place),
        description=listing_description(deed, place, district.name if district else None),
        country="Poland",
        region=place.region,
        city=place.seed_name,
        district=district.name if district else None,
        neighborhood=district.name if district else None,
        address=", ".join(address_parts),
        # The register publishes the position of a building in the Polish
        # national projection - in metres, not in degrees. The listing
        # carries no coordinates rather than a pair of numbers that mean
        # something else.
        latitude=None,
        longitude=None,
        property_type=PropertyType.APARTMENT,
        listing_type=ListingType.SALE,
        rooms=float(deed.rooms) if deed.rooms else None,
        # The register says nothing about the bathrooms of a flat.
        bathrooms=None,
        area_sqm=deed.area_sqm,
        floor=float(deed.floor) if deed.floor is not None and deed.floor >= 0 else None,
        price=deed.price,
        currency=deed.currency,
        source_url=deed.source_url or None,
        source_platform=REGISTER_SOURCE,
    )


def properties_from_deeds(deeds: list[RCNTransaction], place: Place) -> list[Property]:
    """The listings of the registered sales of one city."""
    properties = []
    for deed in deeds:
        listing = property_from_deed(deed, place)
        if listing is not None:
            properties.append(listing)
    return properties
