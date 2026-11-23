"""The places the site knows, and the streets of their districts.

WHY THE CATALOGUE LIVES HERE

The site has two kinds of place: the seeded catalogue of listings, and the
official register of notarial prices. Both need the same list of cities and
the same districts, and both need to agree - a page that says "Zwierzyniec"
while the listing says "Zwierzyniec" is the same place, and a page that says
something else is a second place the reader has to reconcile.

So the catalogue is written once, here, and the seeded generator reads it.
The streets of every district are part of it, because the register holds the
sales of a street and not of a district: a district's own figures are the
figures of the sales registered on its streets.

THE STREETS ARE REAL

Every street in the catalogue is a street of that district in that city. The
register knows them - Floriańska and Grodzka in Kraków's Old Town, Puławska
in Warsaw's Mokotów - which is what makes a district page possible at all:
the register's own sales, on the district's own streets.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

from data.rcn.rcn_models import normalize_text


@dataclass(frozen=True)
class District:
    """One district of a city, and the streets it stands on."""

    name: str
    streets: tuple[str, ...]


@dataclass(frozen=True)
class Place:
    """One city, the way the register and the catalogue each spell it.

    ``name`` is what the pages say. ``seed_name`` is what the seeded
    catalogue calls the city - it is the key the listings are written with.
    ``register_city`` is the register's own spelling of the municipality,
    which is what the register's rows are keyed by.

    ``teryt`` is the code of the municipality in the national registry of
    territorial divisions - the code the register files every sale of the
    city under. It is the one place the register's own exports name the
    municipality in, for the starostas who publish their sales without an
    address.
    """

    name: str
    seed_name: str
    register_city: str
    teryt: str
    districts: tuple[District, ...]


# The streets of every district. A listing that stands in Zwierzyniec has to
# carry a street of Zwierzyniec - the street of another district is the kind
# of detail a visitor notices at once, and it is the street the register's
# sales are counted on.
DISTRICT_STREETS: dict[str, dict[str, tuple[str, ...]]] = {
    "Kraków": {
        "Old Town": ("Floriańska", "Grodzka", "Sienna", "Kanonicza", "Wielopole"),
        "Kazimierz": ("Kanonicza", "Bocheńska", "Józefa", "Wąska", "Jezuitów"),
        "Podgórze": ("Kalwaria", "Górka", "Kobierzyńska", "Rynkowa", "Lipowa"),
        "Bronowice": ("Bronowicka", "Styczna", "Cieszyńska", "Głowackiego", "Topolowa"),
        "Zwierzyniec": ("Zwierzyniecka", "Kościuszki", "Stradomska", "Gdańska", "Błonia"),
    },
    "Warsaw": {
        "Śródmieście": ("Marszałkowska", "Nowy Świat", "Krucza", "Chmielna", "Żurawia"),
        "Mokotów": ("Puławska", "Mokotowska", "Iwicka", "Kazimierzowska", "Racławicka"),
        "Wola": ("Aleje Jerozolimskie", "Woronicza", "Towarowa", "Kasprzyka", "Sokoła"),
        "Praga": ("Targowa", "Ząbkowska", "Brzeska", "Stalowa", "Kijowska"),
        "Żoliborz": (
            "Słowackiego",
            "Żeliborska",
            "Modzelewskiego",
            "Krasińskiego",
            "Czartoryskiego",
        ),
    },
    "Gdańsk": {
        "Main Town": ("Długa", "Mariacka", "Świętego Ducha", "Ogarna", "Frauengasse"),
        "Wrzeszcz": (
            "Wrzeszczyńska",
            "Słowackiego",
            "Skarżyńska",
            "Partyzantów",
            "Wojska Polskiego",
        ),
        "Oliwa": ("Aleja Grunwaldzka", "Pułaskiego", "Sobieskiego", "Abrahama", "Polna"),
        "Jelitkowo": ("Jelitkowska", "Nisułka", "Słoneczna", "Kartuska", "Słowackiego"),
        "Brzeźno": (
            "Brzeźnieńska",
            "Kliszewska",
            "Powstańców Warszawskich",
            "Kołobrzeska",
            "Rakoczego",
        ),
    },
    "Wrocław": {
        "Market Square": ("Rynek", "Szewska", "Włodkowica", "Kuźnicza", "Piotra Ściegiennego"),
        "Krzyki": (
            "Białawska",
            "Armii Krajowej",
            "Drobnera",
            "Powstańców Śląskich",
            "Kamiennogórska",
        ),
        "Fabryczna": ("Zelazna", "Bukowska", "Wrocławska", "Grabiszyńska", "Legnicka"),
        "Psie Pole": ("Dolnośląska", "Kwiatkowskiego", "Botaniczna", "Jaśminowa", "Słowiańska"),
        "Stare Miasto": ("Odrzańska", "Podwale", "Ruska", "Krasińskiego", "Wyszyńskiego"),
    },
    "Poznań": {
        "Old Town": ("Wielka", "Święty Marcin", "Żydowska", "Paderewskiego", "Wodna"),
        "Wilda": ("Piątkowska", "Garbary", "Wyszyńskiego", "Świętokrzyska", "Głogowska"),
        "Jeżyce": ("Słowackiego", "Dąbrowskiego", "Krasickiego", "Mickiewicza", "Bnieńska"),
        "Grunwald": ("Grunwaldzka", "FGSA", "Bukowiańska", "Skórzeccka", "Seweryna"),
        "Winogrady": ("Cieszkowskiego", "Pułaskiego", "Dołęgi", "Szypułkowska", "Lechicka"),
    },
}

# The streets of every city, so a listing of a city carries an address of
# that city.
CITY_STREETS: dict[str, tuple[str, ...]] = {
    "Kraków": ("Floriańska", "Grodzka", "Długa", "Wierzbowa", "Kanonicza"),
    "Warsaw": ("Marszałkowska", "Nowy Świat", "Krucza", "Mokotowska", "Freta"),
    "Gdańsk": ("Długa", "Mariacka", "Piwna", "Jęczmienna", "Garbary"),
    "Wrocław": (
        "Świętego Mikołaja",
        "Oławska",
        "Kazimierza Wielkiego",
        "Św. Marcina",
        "Włodkowica",
    ),
    "Poznań": ("Długa", "Święty Marcin", "Główny", "Mickiewicza", "Naramowicka"),
}

# The register spells the city its own way; the catalogue of listings spells
# it another. Both are kept, so a page can be written in the register's
# wording and a listing in the catalogue's. The TERYT code is the code the
# register files the city's sales under.
_PLACE_SEEDS = (
    ("Kraków", "Kraków", "KRAKÓW", "1261"),
    ("Warszawa", "Warsaw", "WARSZAWA", "1465"),
    ("Gdańsk", "Gdańsk", "GDAŃSK", "2261"),
    ("Wrocław", "Wrocław", "WROCŁAW", "0264"),
    ("Poznań", "Poznań", "POZNAŃ", "3064"),
)


def _districts_of(seed_name: str) -> tuple[District, ...]:
    return tuple(
        District(name=name, streets=streets)
        for name, streets in DISTRICT_STREETS[seed_name].items()
    )


PLACES: tuple[Place, ...] = tuple(
    Place(
        name=name,
        seed_name=seed_name,
        register_city=register_city,
        teryt=teryt,
        districts=_districts_of(seed_name),
    )
    for name, seed_name, register_city, teryt in _PLACE_SEEDS
)


def _folded(value: str) -> str:
    """The form two place names are compared in."""
    return normalize_text(value).replace(" ", "")


# The letters that do not decompose into a base letter and a combining mark.
# ``ó`` decomposes and is handled by the general rule, but ``ł`` is a letter
# of its own: NFD leaves it alone, so it has to be spelled out.
_TRANSLITERATIONS = {
    "ł": "l",
    "Ł": "l",
    "đ": "d",
    "Đ": "d",
    "ð": "d",
    "Ð": "d",
    "ø": "o",
    "Ø": "o",
    "æ": "ae",
    "Æ": "ae",
    "œ": "oe",
    "Œ": "oe",
    "ß": "ss",
    "ẞ": "ss",
    "þ": "th",
    "Þ": "th",
}


def place_slug(value: str) -> str:
    """The link of a place name.

    The same folding the links of an address use: no case, no diacritics, no
    punctuation. A URL with diacritics in it has two spellings, and a page
    whose canonical names one of them while a crawler arrives with the other
    is a page that competes with itself.
    """
    transliterated = "".join(_TRANSLITERATIONS.get(character, character) for character in value)
    decomposed = unicodedata.normalize("NFD", transliterated)
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "-", stripped.lower()).strip("-")


def find_place_by_slug(slug: str) -> Optional[Place]:
    """The place a link stands for, or None."""
    wanted = (slug or "").strip().lower()
    if not wanted:
        return None
    for place in PLACES:
        if place_slug(place.name) == wanted or place_slug(place.seed_name) == wanted:
            return place
    return None


def find_district_by_slug(place: Place, slug: str) -> Optional[District]:
    """The district of a place a link stands for, or None."""
    wanted = (slug or "").strip().lower()
    if not wanted:
        return None
    for district in place.districts:
        if place_slug(district.name) == wanted:
            return district
    return None


def find_place(name: str) -> Optional[Place]:
    """The place a name stands for, or None.

    The name may be spelled the way the pages spell it, the way the seeded
    catalogue spells it or the way the register spells it - a visitor types
    what they know.
    """
    wanted = _folded(name)
    if not wanted:
        return None
    for place in PLACES:
        for spelling in (place.name, place.seed_name, place.register_city):
            if _folded(spelling) == wanted:
                return place
    return None


def city_for_teryt(teryt: str) -> Optional[str]:
    """The city a municipality code stands for, in the register's spelling.

    The register files every sale under the code of the municipality it
    happened in - the TERYT code the national registry of territorial
    divisions gives it. A sale the register publishes without a street still
    belongs to that municipality, so the code is what names the city.

    Only the municipalities the site knows are named: a sale of a place the
    site does not serve is of no use to it, and a name invented for it would
    only be a second spelling of the same place.
    """
    wanted = (teryt or "").strip()
    if not wanted:
        return None
    for place in PLACES:
        if place.teryt == wanted:
            return place.register_city
    return None


def find_district(place: Place, name: str) -> Optional[District]:
    """The district of a place a name stands for, or None."""
    wanted = _folded(name)
    if not wanted:
        return None
    for district in place.districts:
        if _folded(district.name) == wanted:
            return district
    return None


def districts_of(seed_name: str) -> dict[str, tuple[str, ...]]:
    """The streets of every district of a city, for the seeded catalogue."""
    return DISTRICT_STREETS[seed_name]


def city_streets(seed_name: str) -> tuple[str, ...]:
    """The streets of a city, for the seeded catalogue."""
    return CITY_STREETS[seed_name]
