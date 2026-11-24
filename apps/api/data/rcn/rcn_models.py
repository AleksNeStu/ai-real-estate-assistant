"""The shape of one RCN transaction, and of the address it carries."""

import unicodedata
from dataclasses import dataclass
from datetime import date
from typing import Optional


def normalize_text(value: Optional[str]) -> str:
    """Fold a place name into a comparable form.

    The register writes streets in capitals with Polish diacritics; a visitor
    writes them the way they say them. Comparing the two needs the same
    folding on both sides.
    """
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(stripped.upper().split())


@dataclass(frozen=True)
class RCNAddress:
    """A Polish address as the RCN spells it.

    The register stores it as one packed string:
    ``MSC:KRAKÓW;UL:RACIBORSKA;NR_PORZ:17`` — municipality, street, number.
    """

    city: str
    street: str
    number: str = ""

    def __str__(self) -> str:
        # A sale the register published without a street is named by the city
        # it belongs to, and nothing else - a street with nothing in front of
        # it would be a street the register never named.
        parts = [self.street] if self.street else []
        if self.number:
            parts.append(self.number)
        if not parts:
            return self.city
        return f"{', '.join(parts)}, {self.city}" if self.city else ", ".join(parts)


@dataclass(frozen=True)
class RCNTransaction:
    """One sold flat, as recorded in a notarial deed.

    ``price`` is the price of the flat itself (``lok_cena_brutto``); the register
    also carries the price of the whole transaction, which can include a garage
    or a parking space, so it is only a fallback.

    ``external_id`` is the register's own feature id — it names one flat. The
    ``transaction_id`` names the transaction the flat was sold in, and several
    flats share one: a deed may sell two flats in the same building at once.
    ``source_url`` is the export the sale was read from — the address of the
    file the publisher sends, which is where the sale is verifiable.
    """

    external_id: str
    teryt: str
    address: RCNAddress
    area_sqm: float
    price: float
    transaction_date: date
    market: str = ""
    rooms: Optional[int] = None
    floor: Optional[int] = None
    deed_reference: str = ""
    notary: str = ""
    x: Optional[float] = None
    y: Optional[float] = None
    transaction_id: str = ""
    source_url: str = ""

    @property
    def price_per_sqm(self) -> float:
        return self.price / self.area_sqm if self.area_sqm else 0.0

    @property
    def currency(self) -> str:
        """The RCN records prices in Polish złoty."""
        return "PLN"
