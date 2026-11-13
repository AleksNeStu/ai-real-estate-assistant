"""
Service for personalized search ranking based on user preferences.

This service provides functionality to:
- Track and aggregate user preferences from behavior
- Generate user preference profiles
- Apply personalization boosts to search results
"""

import logging
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security_utils import sanitize_for_log
from db.models import UserPreferenceProfile
from services.buyer_memory_service import BuyerMemoryService

logger = logging.getLogger(__name__)

# --- Free-text parsing for the buyer's DECLARED facts -------------------------
#
# A fact's content is the buyer's own words ("up to 500k", "Kraków"). The
# parsers below are deliberately tolerant: they never raise on unexpected text
# and a fact they cannot make sense of is ignored rather than guessed at.

# Currency words and symbols carry no amount - they only get in the way.
_CURRENCY_RE = re.compile(
    r"(zł|zlotych|zloty|zl|pln|eur|euro|usd|gbp|chf|kd|\$|€|£)",
    re.IGNORECASE,
)

# "500 000" is one amount, not two. Only a group of exactly three digits is a
# thousands separator ("500 000"), a longer group is two separate numbers.
_DIGIT_GAP_RE = re.compile(r"(?<=\d)[\s  ](?=\d{3}(?!\d))")

# An amount and its scale: 500, 500k, 1.5m, 300 tys, 2 mln.
# The number may carry several separators ("1.500.000") - they are read as
# European thousands separators, never as decimal points.
_AMOUNT_RE = re.compile(
    r"(\d+(?:[.,]\d+)*)\s*(thousand|million|mln|mld|tyś|tys|ml|k|m)?",
    re.IGNORECASE,
)

_AMOUNT_SCALES = {
    "k": 1e3,
    "tys": 1e3,
    "tyś": 1e3,
    "thousand": 1e3,
    "m": 1e6,
    "ml": 1e6,
    "mln": 1e6,
    "mld": 1e6,
    "million": 1e6,
}

# A range connector between two amounts: "200k - 400k", "200k do 400k".
_RANGE_JOIN_RE = re.compile(r"[-–—~]")

# A budget phrase and the side it puts the amount on.
#
# The marker that comes LAST before the amount decides. A negation makes a
# "more than" a CEILING: "I don't want to spend more than 500k" is the exact
# opposite of "more than 500k", and reading it as a floor inverts the buyer's
# words. The negated forms are written out in full so that they win over the
# bare "more than" they contain.
_BUDGET_SIDE_MARKERS: tuple[tuple[re.Pattern[str], str], ...] = (
    # --- CEILINGS ---------------------------------------------------------
    # A negated "more than" - the buyer refuses to go above the amount.
    (
        re.compile(
            r"\b(?:do\s+not|don['’]?t|dont|never)\s+want\s+"
            r"(?:to\s+(?:spend|pay|go)\s+)?(?:more|over|above)(?:\s+than)?\b"
        ),
        "max",
    ),
    (re.compile(r"\bnot\s+more\s+than\b"), "max"),
    (re.compile(r"\bno\s+more\s+than\b"), "max"),
    (re.compile(r"\bless\s+than\b"), "max"),
    (re.compile(r"\bat\s+most\b"), "max"),
    (re.compile(r"\bup\s+to\b"), "max"),
    (re.compile(r"\bmaximum\b"), "max"),
    (re.compile(r"\bunder\b"), "max"),
    (re.compile(r"\bbelow\b"), "max"),
    (re.compile(r"\bmaksymalnie\b"), "max"),
    (re.compile(r"\bponizej\b"), "max"),
    (re.compile(r"\bno\s+more\b"), "max"),
    (re.compile(r"\bbudgetceiling\b"), "max"),
    # A plain budget with no keyword is a ceiling: "my budget is 500k".
    (re.compile(r"\bbudget\b"), "max"),
    (re.compile(r"\bbudzet\b"), "max"),
    # --- FLOORS -----------------------------------------------------------
    (re.compile(r"\bnot\s+less\s+than\b"), "min"),
    (re.compile(r"\bno\s+less\s+than\b"), "min"),
    (re.compile(r"\bat\s+least\b"), "min"),
    (re.compile(r"\bminimum\b"), "min"),
    (re.compile(r"\bstarting\s+from\b"), "min"),
    (re.compile(r"\bmore\s+than\b"), "min"),
    (re.compile(r"\bover\b"), "min"),
    (re.compile(r"\babove\b"), "min"),
    (re.compile(r"\bfrom\b"), "min"),
    (re.compile(r"\bco\s+najmniej\b"), "min"),
    (re.compile(r"\bpowyzej\b"), "min"),
    (re.compile(r"\bod\b"), "min"),
    (re.compile(r"\bbudgetfloor\b"), "min"),
)

# "no more than" / "not less than" carry a negation that would otherwise be
# read as the opposite keyword ("more than" inside "no more than").
_NEGATED_BUDGET_RE = re.compile(r"\b(?:no|not)\s+(more|less)\s+than\b")

# A ruled-out area may be written as a negation ("no Kraków"). The negation
# is not part of the place name, so it is stripped before the place is matched.
_RULE_OUT_NEGATIONS = frozenset(
    {"no", "not", "without", "avoid", "skip", "exclude", "nie", "bez", "omit"}
)

# How much a DECLARED like adds - a liked feature weighs like a favourite.
DECLARED_LIKE_CITY_BOOST = 0.2
DECLARED_LIKE_TYPE_BOOST = 0.2
DECLARED_LIKE_AMENITY_BOOST = 0.1


def _normalise_text(text: str) -> str:
    """Lowercase a text and drop its accents, so "Kraków" and "Krakow" match."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return without_marks.casefold()


def _token_sequence(text: str) -> list[str]:
    """Split a text into lowercase word tokens IN ORDER, accents dropped.

    A trailing plural "s" is dropped, so "apartments" and "apartment" are the
    same token. Both sides of every comparison go through this, so the
    comparison stays consistent.
    """
    tokens = re.findall(r"[a-z0-9]+", _normalise_text(text))
    return [t[:-1] if len(t) > 3 and t.endswith("s") else t for t in tokens]


def _text_tokens(text: str) -> set[str]:
    """The tokens of a text, as a set - order is not kept."""
    return set(_token_sequence(text))


def _place_name(value: Any) -> str:
    """The place name of a property field, without its trailing region."""
    return str(value or "").split(",")[0].strip()


def _place_sequence(content: str) -> tuple[str, ...]:
    """
    The words of a place the buyer named, in order.

    A leading negation ("no Kraków") is not part of the place name and is
    dropped - the buyer ruled the place out, whatever the phrasing.
    """
    tokens = _token_sequence(content)
    while tokens and tokens[0] in _RULE_OUT_NEGATIONS:
        tokens = tokens[1:]
    return tuple(tokens)


def _contains_sequence(tokens: list[str], sequence: tuple[str, ...]) -> bool:
    """Tell whether ``sequence`` appears in ``tokens`` as a contiguous run."""
    if not sequence or len(sequence) > len(tokens):
        return False
    first = sequence[0]
    for start in range(len(tokens) - len(sequence) + 1):
        if tokens[start] == first and tuple(tokens[start : start + len(sequence)]) == sequence:
            return True
    return False


def _scale_amount(number: str, suffix: Optional[str]) -> Optional[float]:
    """
    Read an amount out of a number written by a buyer.

    European thousands separators are understood: "1.500.000" is one million
    five hundred thousand, not one thousand five hundred. A separator that is
    followed by exactly three digits is a thousands separator; anything else
    is a decimal point. A number that cannot be read unambiguously (a date
    like "12.05.2024") is NOT guessed at - it returns None.

    Returns:
        The amount, or None when the number cannot be read.
    """
    parts = re.split(r"[.,]", number.strip())
    if len(parts) == 1:
        digits = parts[0]
    else:
        tails = parts[1:]
        if all(len(tail) == 3 and tail.isdigit() for tail in tails):
            # "1.500.000" and "500.000" - thousands separators.
            digits = "".join(parts)
        elif len(parts) == 2:
            # "500,50" and "500.50" - a decimal point.
            digits = parts[0] + "." + tails[0]
        else:
            # "12.05.2024" - a date, or anything else ambiguous.
            return None

    try:
        amount = float(digits)
    except ValueError:
        return None

    if suffix:
        amount *= _AMOUNT_SCALES.get(suffix.lower(), 1.0)
    return amount


def _is_range_fragment(fragment: str) -> bool:
    """Tell a range ("200k - 400k") from two separate amounts."""
    if "between" in fragment:
        return True
    if _RANGE_JOIN_RE.search(fragment):
        return True
    if re.search(
        r"\b(?:up\s+to|no\s+more\s+than|at\s+most|less\s+than|under|below"
        r"|more\s+than|over|above|minimum|maximum)\b",
        fragment,
    ):
        return False
    return bool(re.search(r"\b(?:to|and|or|od|do)\b", fragment))


def _budget_side(text: str, position: int) -> str:
    """Tell whether the amount before ``position`` is a floor or a ceiling."""
    window = text[max(0, position - 80) : position]
    best_end = -1
    best_length = -1
    best_side = "max"

    for pattern, side in _BUDGET_SIDE_MARKERS:
        for match in pattern.finditer(window):
            end = match.end()
            length = len(match.group(0))
            # The marker that comes last wins; on a tie the longer one wins,
            # so "don't want to spend more than" beats the "more than" in it.
            if end > best_end or (end == best_end and length > best_length):
                best_end = end
                best_length = length
                best_side = side

    # A budget with no keyword is a ceiling: "my budget is 500k".
    return best_side


def _parse_budget(content: str) -> tuple[Optional[float], Optional[float]]:
    """
    Read a price range out of a free-text budget fact.

    Args:
        content: The fact in the buyer's own words ("up to 500k").

    Returns:
        (minimum, maximum). Either may be None. Never raises.
    """
    text = _normalise_text(content or "")
    if not text:
        return None, None

    text = _CURRENCY_RE.sub(" ", text)
    text = _DIGIT_GAP_RE.sub("", text)

    def _mask_negation(match: re.Match) -> str:
        return " budgetfloor " if match.group(1) == "less" else " budgetceiling "

    text = _NEGATED_BUDGET_RE.sub(_mask_negation, text)

    amounts: list[tuple[int, float]] = []
    for match in _AMOUNT_RE.finditer(text):
        amount = _scale_amount(match.group(1), match.group(2))
        if amount is None or amount < 1000:
            # Below a thousand this is not a price - it is a room count, a
            # year or a house number. Ignore it rather than guess.
            continue
        amounts.append((match.start(), amount))

    if not amounts:
        return None, None

    if len(amounts) >= 2 and amounts[0][1] <= amounts[1][1]:
        fragment = text[amounts[0][0] : amounts[1][0]]
        if _is_range_fragment(fragment):
            return amounts[0][1], amounts[1][1]

    minimum: Optional[float] = None
    maximum: Optional[float] = None
    for position, amount in amounts:
        if _budget_side(text, position) == "min":
            minimum = amount if minimum is None else max(minimum, amount)
        else:
            maximum = amount if maximum is None else min(maximum, amount)

    return minimum, maximum


@dataclass
class DeclaredPreferences:
    """
    What the buyer SAID, parsed out of the free text of their memory.

    The behavioural profile says what the buyer clicked; these facts say what
    the buyer asked for. They are kept apart because they behave differently:
    a declared budget narrows the price range, a declared ruled-out area
    removes the area outright, and a declared liked feature adds weight.
    """

    # The price the buyer stated. Either bound may be None.
    price_min: Optional[float] = None
    price_max: Optional[float] = None

    # The token sequences of the areas the buyer ruled out, in the order the
    # buyer wrote them.
    ruled_out_areas: list[tuple[str, ...]] = field(default_factory=list)

    # The token sets of the features the buyer liked.
    liked_features: list[frozenset[str]] = field(default_factory=list)

    @property
    def is_active(self) -> bool:
        """True when the buyer declared anything at all."""
        return bool(
            self.price_min is not None
            or self.price_max is not None
            or self.ruled_out_areas
            or self.liked_features
        )

    @classmethod
    def from_facts(cls, facts: Iterable[Any]) -> "DeclaredPreferences":
        """
        Build the declared preferences out of the buyer's memory facts.

        A fact that cannot be parsed is ignored - it never makes the whole
        memory unreadable.

        Args:
            facts: The buyer's facts. Anything with ``kind`` and ``content``.

        Returns:
            The parsed DeclaredPreferences.
        """
        declared = cls()

        for fact in facts or []:
            kind = getattr(fact, "kind", "")
            content = getattr(fact, "content", "") or ""

            if kind == "budget":
                minimum, maximum = _parse_budget(content)
                if minimum is not None:
                    declared.price_min = (
                        minimum if declared.price_min is None else max(declared.price_min, minimum)
                    )
                if maximum is not None:
                    declared.price_max = (
                        maximum if declared.price_max is None else min(declared.price_max, maximum)
                    )
            elif kind == "ruled_out_area":
                tokens = _place_sequence(content)
                if tokens:
                    declared.ruled_out_areas.append(tokens)
            elif kind == "liked":
                tokens = _text_tokens(content)
                if tokens:
                    declared.liked_features.append(frozenset(tokens))

        return declared

    def excludes_property(self, property_data: dict[str, Any]) -> bool:
        """
        Tell whether the buyer ruled this property's area out.

        A ruled-out area is a FILTER, not a weight: it removes the area
        outright, where a weight could be outvoted by other signals.

        The place the buyer named must appear in the property's place as a
        CONTIGUOUS run of words, not as a bag of words: "Nowe Miasto" does
        not rule out the district "Miasto", it rules out "Nowe Miasto".
        """
        if not self.ruled_out_areas:
            return False

        for key in ("city", "district", "area", "neighborhood"):
            place = _place_name(property_data.get(key))
            if not place:
                continue
            tokens = _token_sequence(place)
            if tokens and any(_contains_sequence(tokens, area) for area in self.ruled_out_areas):
                return True
        return False

    def liked_boost(self, property_data: dict[str, Any]) -> tuple[float, float, float]:
        """
        The weight a declared like adds - like a favourite does.

        Returns:
            (city_boost, type_boost, amenity_boost).
        """
        if not self.liked_features:
            return 0.0, 0.0, 0.0

        city_boost = 0.0
        type_boost = 0.0
        amenity_boost = 0.0

        place = _place_name(property_data.get("city"))
        if place:
            tokens = _text_tokens(place)
            if tokens and any(tokens <= like for like in self.liked_features):
                city_boost = DECLARED_LIKE_CITY_BOOST

        property_type = property_data.get("property_type")
        if property_type:
            tokens = _text_tokens(str(property_type))
            if tokens and any(tokens <= like for like in self.liked_features):
                type_boost = DECLARED_LIKE_TYPE_BOOST

        amenities = property_data.get("amenities") or []
        if isinstance(amenities, (list, tuple, set)):
            for amenity in amenities:
                tokens = _text_tokens(str(amenity))
                if tokens and any(tokens <= like for like in self.liked_features):
                    amenity_boost += DECLARED_LIKE_AMENITY_BOOST
        amenity_boost = min(0.3, amenity_boost)

        return city_boost, type_boost, amenity_boost


@dataclass
class UserPreferences:
    """Extracted user preferences for ranking."""

    user_id: str

    # Location preferences
    preferred_cities: dict[str, float] = field(default_factory=dict)

    # Price preferences
    preferred_price_min: Optional[float] = None
    preferred_price_max: Optional[float] = None

    # Property attributes
    preferred_rooms: list[int] = field(default_factory=list)
    preferred_property_types: list[str] = field(default_factory=list)

    # Amenities
    amenity_weights: dict[str, float] = field(default_factory=dict)

    # Embedding for semantic similarity
    preference_embedding: Optional[bytes] = None

    # Statistics
    view_count: int = 0
    favorite_count: int = 0

    @classmethod
    def from_model(cls, profile: UserPreferenceProfile) -> "UserPreferences":
        """Create UserPreferences from a UserPreferenceProfile model."""
        # Convert list of {"city": x, "weight": y} to dict {city: weight}
        cities_dict: dict[str, float] = {}
        if profile.preferred_cities:
            for item in profile.preferred_cities:
                if isinstance(item, dict) and "city" in item and "weight" in item:
                    cities_dict[item["city"]] = float(item["weight"])

        return cls(
            user_id=str(profile.user_id),
            preferred_cities=cities_dict,
            preferred_price_min=profile.preferred_price_min,
            preferred_price_max=profile.preferred_price_max,
            preferred_rooms=profile.preferred_rooms or [],
            preferred_property_types=profile.preferred_property_types or [],
            amenity_weights=profile.amenity_weights or {},
            preference_embedding=profile.preference_embedding,
            view_count=profile.view_count,
            favorite_count=profile.favorite_count,
        )


@dataclass
class PersonalizationBoost:
    """Personalization boost for a single property."""

    property_id: str
    total_boost: float

    # Component breakdown
    city_boost: float = 0.0
    price_boost: float = 0.0
    rooms_boost: float = 0.0
    type_boost: float = 0.0
    amenity_boost: float = 0.0
    semantic_boost: float = 0.0
    declared_boost: float = 0.0


class PersonalizationService:
    """Service for personalized search ranking."""

    # Weight for favorites vs views in preference aggregation
    FAVORITE_WEIGHT = 2.0
    VIEW_WEIGHT = 1.0

    # Minimum interactions before personalization activates
    MIN_INTERACTIONS = 3

    def __init__(self, session: AsyncSession, memory_service: Optional[BuyerMemoryService] = None):
        self.session = session
        # The buyer's memory is the source of the DECLARED facts. It is a
        # dependency, not a global, so the service stays testable and the
        # memory is read through the one service that owns the table.
        self.memory_service = memory_service or BuyerMemoryService(session)

    async def get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """
        Get the preference profile for a user.

        Args:
            user_id: The user ID.

        Returns:
            UserPreferences or None if not found.
        """
        result = await self.session.execute(
            select(UserPreferenceProfile).where(UserPreferenceProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        if profile:
            return UserPreferences.from_model(profile)
        return None

    async def get_or_create_preferences(self, user_id: str) -> UserPreferences:
        """
        Get or create a preference profile for a user.

        Args:
            user_id: The user ID.

        Returns:
            UserPreferences (creates new if not exists).
        """
        prefs = await self.get_user_preferences(user_id)

        if prefs:
            return prefs

        # Create new profile
        profile = UserPreferenceProfile(user_id=user_id)
        self.session.add(profile)
        await self.session.commit()
        await self.session.refresh(profile)

        return UserPreferences.from_model(profile)

    async def get_declared_preferences(self, user_id: str) -> DeclaredPreferences:
        """
        Get the facts the buyer DECLARED - their budget, the areas they ruled
        out and the features they liked.

        The behavioural profile says what the buyer clicked; this says what the
        buyer asked for. A memory that cannot be read is treated as no memory:
        the ranking then falls back to the behavioural profile.

        Args:
            user_id: The user ID.

        Returns:
            The parsed DeclaredPreferences - empty when the buyer said nothing.
        """
        try:
            facts = await self.memory_service.recall_for_user(user_id, limit=50)
        except Exception:  # noqa: BLE001 - the memory must never break ranking
            logger.warning(
                "Buyer memory unavailable for %s, falling back to behaviour",
                sanitize_for_log(user_id),
            )
            return DeclaredPreferences()

        return DeclaredPreferences.from_facts(facts)

    async def update_preferences_from_interaction(
        self,
        user_id: str,
        property_data: dict[str, Any],
        interaction_type: str,
    ) -> UserPreferences:
        """
        Update user preferences based on a property interaction.

        Args:
            user_id: The user ID.
            property_data: Property metadata (city, price, rooms, etc.).
            interaction_type: Type of interaction ("view", "favorite", "contact").

        Returns:
            Updated UserPreferences.
        """
        prefs = await self.get_or_create_preferences(user_id)

        # Get current profile
        result = await self.session.execute(
            select(UserPreferenceProfile).where(UserPreferenceProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            return prefs

        # Determine weight based on interaction type
        weight = self.VIEW_WEIGHT
        if interaction_type == "favorite":
            weight = self.FAVORITE_WEIGHT
            profile.favorite_count += 1
        elif interaction_type == "contact":
            weight = self.FAVORITE_WEIGHT * 1.5  # Contact is strongest signal
        else:
            profile.view_count += 1

        # Update city preference
        city = property_data.get("city")
        if city:
            cities = profile.preferred_cities or {}
            current_weight = cities.get(city, 0.0)
            cities[city] = min(1.0, current_weight + weight * 0.1)  # Cap at 1.0
            profile.preferred_cities = cities

        # Update price range
        price = property_data.get("price")
        if price:
            price_float = float(price)
            if profile.preferred_price_min is None:
                profile.preferred_price_min = price_float
            else:
                # Slowly adjust range
                profile.preferred_price_min = profile.preferred_price_min * 0.9 + price_float * 0.1
            if profile.preferred_price_max is None:
                profile.preferred_price_max = price_float
            else:
                profile.preferred_price_max = profile.preferred_price_max * 0.9 + price_float * 0.1

        # Update rooms preference
        rooms = property_data.get("rooms")
        if rooms is not None:
            rooms_int = int(rooms)
            preferred_rooms = profile.preferred_rooms or []
            if rooms_int not in preferred_rooms:
                preferred_rooms.append(rooms_int)
            profile.preferred_rooms = preferred_rooms

        # Update property type preference
        property_type = property_data.get("property_type")
        if property_type:
            preferred_types = profile.preferred_property_types or []
            if property_type not in preferred_types:
                preferred_types.append(property_type)
            profile.preferred_property_types = preferred_types

        # Update amenity weights
        amenities = property_data.get("amenities", [])
        if amenities:
            amenity_weights = profile.amenity_weights or {}
            for amenity in amenities:
                current = amenity_weights.get(amenity, 0.0)
                amenity_weights[amenity] = min(1.0, current + weight * 0.1)
            profile.amenity_weights = amenity_weights

        await self.session.commit()
        await self.session.refresh(profile)

        return UserPreferences.from_model(profile)

    def calculate_personalization_boost(
        self,
        property_data: dict[str, Any],
        preferences: UserPreferences,
        personalization_weight: float = 0.2,
        declared: Optional[DeclaredPreferences] = None,
    ) -> PersonalizationBoost:
        """
        Calculate personalization boost for a property.

        The behavioural profile and the DECLARED facts are learned side by
        side. The declared facts arrive as an optional argument rather than
        through UserPreferences, because they come from the buyer's memory -
        an async read - while this method is synchronous and its existing
        callers pass the behavioural profile alone. With no declared facts the
        result is exactly what it was before.

        Args:
            property_data: Property metadata.
            preferences: User preferences (the behavioural profile).
            personalization_weight: Overall weight for personalization (0-0.5).
            declared: The facts the buyer declared. Optional.

        Returns:
            PersonalizationBoost with boost components.
        """
        property_id = str(property_data.get("id", ""))

        boost = PersonalizationBoost(
            property_id=property_id,
            total_boost=0.0,
        )

        if declared is None:
            declared = DeclaredPreferences()

        # Check if we have enough data for personalization. A buyer who SAID
        # what they want does not need a click history for that to count.
        total_interactions = preferences.view_count + preferences.favorite_count
        if total_interactions < self.MIN_INTERACTIONS and not declared.is_active:
            return boost

        # City boost
        city = property_data.get("city", "")
        if city and city in preferences.preferred_cities:
            boost.city_boost = preferences.preferred_cities[city] * 0.3

        # Price range boost. A stated budget is the buyer's own words: it
        # wins outright. It is never diluted by the behavioural range, and it
        # never collapses into an empty range - a buyer who says "up to 500k"
        # gets that ceiling enforced, whatever they clicked before.
        price = property_data.get("price")
        price_float = self._as_float(price)
        behavioural_min = preferences.preferred_price_min or None
        behavioural_max = preferences.preferred_price_max or None

        declared_min = declared.price_min
        declared_max = declared.price_max

        if declared_min is None and declared_max is None:
            # Nothing was stated - the behavioural range is all there is.
            price_min, price_max = behavioural_min, behavioural_max
            strict_min = strict_max = False
        else:
            strict_min = declared_min is not None
            strict_max = declared_max is not None
            price_max = declared_max
            if price_max is None and behavioural_max is not None:
                # The behavioural ceiling only survives when it does not
                # contradict the stated floor.
                price_max = behavioural_max if behavioural_max >= declared_min else None
            price_min = declared_min
            if price_min is None and behavioural_min is not None:
                # The behavioural floor only survives when it does not
                # contradict the stated ceiling.
                price_min = behavioural_min if behavioural_min <= declared_max else None
            if price_min is not None and price_max is not None and price_min > price_max:
                # A contradictory pair of stated bounds: keep the ceiling,
                # which is the one the buyer refuses to cross.
                price_min = None

        if price and price_float is not None and (price_min is not None or price_max is not None):
            if price_min is not None and price_max is not None:
                if price_min <= price_float <= price_max:
                    boost.price_boost = 0.2
                else:
                    # Penalize if too far outside range
                    range_center = (price_min + price_max) / 2
                    range_size = (price_max - price_min) / 2
                    if range_size > 0:
                        deviation = abs(price_float - range_center) / range_size
                        boost.price_boost = max(-0.3, 0.2 - deviation * 0.2)
                    elif strict_min or strict_max:
                        # A stated single price: anything else is out.
                        deviation = abs(price_float - price_min) / max(price_min, 1.0)
                        boost.price_boost = max(-0.3, -0.3 * deviation)
            elif price_max is not None:
                # A one-sided ceiling ("up to 500k") still tells us where the
                # ceiling is.
                if price_float > price_max:
                    deviation = (price_float - price_max) / max(price_max, 1.0)
                    if strict_max:
                        # A stated ceiling is enforced: above it the boost is
                        # negative, not merely smaller.
                        boost.price_boost = max(-0.3, -0.3 * deviation)
                    else:
                        boost.price_boost = max(-0.3, 0.2 - deviation * 0.2)
                else:
                    boost.price_boost = 0.2
            elif price_min is not None:
                if price_float < price_min:
                    deviation = (price_min - price_float) / max(price_min, 1.0)
                    if strict_min:
                        boost.price_boost = max(-0.3, -0.3 * deviation)
                    else:
                        boost.price_boost = max(-0.3, 0.2 - deviation * 0.2)
                else:
                    boost.price_boost = 0.2

        # Rooms boost
        rooms = property_data.get("rooms")
        if rooms is not None and int(rooms) in preferences.preferred_rooms:
            boost.rooms_boost = 0.15

        # Property type boost
        property_type = property_data.get("property_type")
        if property_type and property_type in preferences.preferred_property_types:
            boost.type_boost = 0.2

        # Amenity boost
        amenities = property_data.get("amenities", [])
        if amenities and preferences.amenity_weights:
            amenity_match = sum(preferences.amenity_weights.get(a, 0.0) for a in amenities)
            boost.amenity_boost = min(0.3, amenity_match * 0.1)

        # A declared like weighs like a favourite: it adds weight, it never
        # removes anything.
        like_city, like_type, like_amenity = declared.liked_boost(property_data)
        boost.city_boost += like_city
        boost.type_boost += like_type
        boost.amenity_boost = min(0.3, boost.amenity_boost + like_amenity)
        boost.declared_boost = like_city + like_type + like_amenity

        # Calculate total boost with weight
        raw_boost = (
            boost.city_boost
            + boost.price_boost
            + boost.rooms_boost
            + boost.type_boost
            + boost.amenity_boost
        )

        # Apply personalization weight
        boost.total_boost = raw_boost * personalization_weight

        return boost

    @staticmethod
    def _as_float(value: Any) -> Optional[float]:
        """Read a number out of a property field, or None when it is not one."""
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    async def calculate_preference_embedding(
        self,
        user_id: str,
        property_embeddings: dict[str, bytes],
    ) -> Optional[bytes]:
        """
        Calculate user preference embedding from property embeddings.

        The preference embedding is a weighted average of property embeddings
        from viewed and favorited properties.

        Args:
            user_id: The user ID.
            property_embeddings: Dict mapping property_id to embedding bytes.

        Returns:
            Preference embedding as bytes, or None if not enough data.
        """
        # This would need to join with interaction data to get viewed/favorited
        # properties. For now, we'll leave this as a placeholder.
        # In a full implementation, this would:
        # 1. Get all viewed/favorited property IDs for the user
        # 2. Get their embeddings
        # 3. Compute weighted average (favorites weighted more)
        # 4. Store the result

        logger.debug(
            "Preference embedding calculation not implemented for %s", sanitize_for_log(user_id)
        )
        return None

    async def apply_personalization_to_results(
        self,
        results: list[tuple[Any, float]],
        user_id: str,
        personalization_weight: float = 0.2,
    ) -> list[tuple[Any, float]]:
        """
        Apply personalization boosts to search results.

        Args:
            results: List of (document, score) tuples.
            user_id: The user ID.
            personalization_weight: Weight for personalization (0-0.5).

        Returns:
            Re-ranked results with personalization applied. A result in an
            area the buyer ruled out is not in the returned list at all.
        """
        preferences = await self.get_user_preferences(user_id)
        declared = await self.get_declared_preferences(user_id)

        if not preferences and not declared.is_active:
            return results

        if preferences is None:
            preferences = UserPreferences(user_id=user_id)

        personalized = []
        for doc, score in results:
            # Extract property data from document metadata
            property_data = doc.metadata if hasattr(doc, "metadata") else {}

            # A ruled-out area is a filter, not a weight: the result is
            # removed outright instead of being pushed down the list.
            if declared.excludes_property(property_data):
                continue

            boost = self.calculate_personalization_boost(
                property_data, preferences, personalization_weight, declared
            )

            # Apply boost
            new_score = score * (1.0 + boost.total_boost)
            personalized.append((doc, new_score))

        # Re-sort by new scores
        personalized.sort(key=lambda x: x[1], reverse=True)

        return personalized


# Dependency injection helper
def get_personalization_service(session: AsyncSession) -> PersonalizationService:
    """Get a PersonalizationService instance."""
    return PersonalizationService(session)
