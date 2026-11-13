"""
The extractor that reads a buyer's turn into durable facts (Task #78).

A buyer memory only pays off if it holds facts the buyer would not repeat
tomorrow. This module is the strictest filter in the chain: it asks the model
for the durable facts of a turn and then throws away everything that is not
one. A prose answer yields ZERO facts.

Two rules define the failure policy:

* A malformed payload yields zero facts and a log line, never an exception.
* The LLM is injected. The module never resolves a provider, never reads a key
  and never calls ``get_llm``.

Call it like this (the wiring is Task #79's job)::

    facts = await extract_buyer_facts(
        messages=messages,
        answer=answer,
        listings=listings,
        llm=llm,          # any LangChain BaseChatModel
    )

The returned facts are plain dataclasses. The write path
(``services.buyer_memory_service.py``) owns persisting them.
"""

import asyncio
import json
import logging
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)

# The closed set of kinds a fact can carry. It mirrors
# services.buyer_memory_service.VALID_KINDS - a fact whose kind is outside the
# set is dropped, never coerced.
FACT_KINDS = frozenset(
    {
        "budget",
        "ruled_out_area",
        "liked",
        "disliked",
        "requirement",
        "note",
    }
)

# The kinds that are about one listing and therefore need a listing id.
_LISTING_KINDS = frozenset({"liked", "disliked"})

# How many facts one turn may contribute. A turn carries a handful of durable
# facts; a longer list is the model padding, not the buyer talking.
MAX_FACTS = 20

# How many messages of the transcript go into the prompt.
MAX_TRANSCRIPT_MESSAGES = 12


@dataclass(frozen=True)
class Fact:
    """One durable fact read out of a buyer's turn.

    Attributes:
        kind: One of FACT_KINDS.
        content: The fact in the buyer's own words, normalised.
        listing_id: The listing the fact is about, when it is about one.
        confidence: How sure the extractor was (0-1).
        budget_min: The lower bound of a budget, when the fact is a budget.
        budget_max: The upper bound of a budget, when the fact is a budget.
    """

    kind: str
    content: str
    listing_id: Optional[str] = None
    confidence: float = 1.0
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None


# --------------------------------------------------------------------------------------
# The prompt
# --------------------------------------------------------------------------------------

_EXTRACTION_PROMPT = """\
You are the buyer-memory extractor of a property search assistant.

TASK
Read the buyer's turn and the assistant's answer and return the DURABLE facts
about this buyer: the things the buyer would not need to say again tomorrow.

RULES
1. Only durable facts - a lasting budget, an area the buyer ruled out, a lasting
   requirement, a lasting preference. A one-off reference ("that one", "as
   before", "the second one" without a listing) is NOT a fact.
2. No questions, no small talk, no pleasantries, no facts about the assistant.
3. A reference to a listing is only a fact when you can name its listing id.
   Without a listing id, drop it.
4. A budget range is normalised into min and max numbers: "between 300k and 450k
   PLN" becomes 300000-450000 PLN.
5. "not X" ("I don't want Krakow", "no Krakow", "avoid Krakow") is kind
   "ruled_out_area" and carries the negated value alone ("Krakow"). It is never
   a preference FOR that value. A negated BUDGET ("I do not want to spend more
   than 500k") and a negated REQUIREMENT ("no parking") keep their own kind.
6. The kind set is closed - use one of: budget, ruled_out_area, liked, disliked,
   requirement, note. "liked" and "disliked" are about one listing and carry its
   listing id.
7. If the turn holds nothing durable, return an empty array.

OUTPUT
A strict JSON array and nothing else - no prose, no explanation, no markdown
fence. Each element is an object:
{"kind": "<kind>", "content": "<the fact>", "listing_id": "<id or null>",
 "confidence": <number between 0 and 1>}
"""


def build_extraction_prompt(
    messages: Sequence[Any],
    answer: Any,
    listings: Sequence[Any] = (),
) -> str:
    """Build the extraction prompt for one turn.

    Args:
        messages: The conversation so far - dicts or objects with a role and content.
        answer: The assistant's answer for this turn.
        listings: The listings that were shown in this turn.

    Returns:
        The prompt string. The caller sends it to the LLM.
    """
    lines = [_EXTRACTION_PROMPT]

    transcript = [_message_text(message) for message in _tail(messages)]
    transcript = [line for line in transcript if line]
    lines.append("CONVERSATION")
    lines.extend(transcript or ["(empty)"])

    answer_text = _as_text(answer)
    lines.append("ASSISTANT ANSWER")
    lines.append(answer_text or "(empty)")

    listing_lines = [_listing_line(listing) for listing in listings or ()]
    listing_lines = [line for line in listing_lines if line]
    lines.append("LISTINGS SHOWN")
    lines.extend(listing_lines or ["(none)"])

    return "\n".join(lines)


# --------------------------------------------------------------------------------------
# Reading the model's answer
# --------------------------------------------------------------------------------------


def _as_text(value: Any) -> str:
    """Read a value as text without ever raising."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    try:
        return str(value).strip()
    except Exception:  # pragma: no cover - str() of an exotic object
        return ""


def _message_text(message: Any) -> str:
    """Render one conversation message as "role: content"."""
    if isinstance(message, dict):
        role = message.get("role")
        content = message.get("content")
    else:
        role = getattr(message, "role", None)
        content = getattr(message, "content", None)

    text = _as_text(content)
    if not text:
        return ""
    return f"{_as_text(role) or 'user'}: {text}"


def _listing_line(listing: Any) -> str:
    """Render one listing as a single line the model can map a reference onto."""
    if isinstance(listing, dict):

        def get(key: str, default: Any = None) -> Any:
            return listing.get(key, default)

    else:

        def get(key: str, default: Any = None) -> Any:
            return getattr(listing, key, default)

    listing_id = get("id") or get("listing_id")
    if not listing_id:
        return ""

    title = _as_text(get("title"))
    city = _as_text(get("city"))
    district = _as_text(get("district"))
    price = get("price")
    currency = _as_text(get("currency"))

    parts = [f"listing_id={listing_id}"]
    if title:
        parts.append(f"title={title}")
    location = ", ".join(part for part in (city, district) if part)
    if location:
        parts.append(f"location={location}")
    if price is not None:
        parts.append(f"price={price} {currency}".strip())
    return " | ".join(parts)


def _tail(messages: Sequence[Any]) -> list[Any]:
    """The last messages of the transcript."""
    items = list(messages or ())
    return items[-MAX_TRANSCRIPT_MESSAGES:]


def _strip_code_fence(text: str) -> str:
    """Remove a markdown code fence, if the answer carries one."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    # The first line is the fence opener ("```json"), the last one the closer.
    body = lines[1:]
    if body and body[-1].strip().startswith("```"):
        body = body[:-1]
    return "\n".join(body).strip()


def _parse_payload(raw: str) -> Optional[list]:
    """Parse the model's answer into a JSON array, or None when it is not one.

    Only a strict JSON array is accepted. Prose - even prose with a bracket in
    it - yields None, and the caller turns that into zero facts.
    """
    text = _strip_code_fence(raw)
    if not text or not text.startswith("[") or not text.endswith("]"):
        return None
    try:
        payload = json.loads(text)
    except (ValueError, TypeError) as exc:
        logger.warning("Buyer memory extraction: malformed JSON payload (%s)", exc)
        return None
    if not isinstance(payload, list):
        logger.warning("Buyer memory extraction: payload is not an array, no facts extracted")
        return None
    return payload


# --------------------------------------------------------------------------------------
# Building one fact
# --------------------------------------------------------------------------------------

# Negations that rule a place out. The longer phrases come first.
_NEGATION_PHRASES = (
    "i don't want to live in",
    "i don't want",
    "i dont want",
    "i do not want",
    "i'm not interested in",
    "i am not interested in",
    "not interested in",
    "no interest in",
    "i don't like",
    "i dont like",
    "not a fan of",
    "stay away from",
    "ruled out",
    "rule out",
    "don't want",
    "dont want",
    "do not want",
    "exclude",
    "avoid",
    "never",
)
# The short generic negations are weaker: they only reclassify a fact when
# what remains is a single word ("no Krakow"), so that "no deposit needed"
# stays a requirement.
_WEAK_NEGATIONS = ("not ", "no ")

_ORDINAL_REFERENCE_RE = re.compile(
    r"\b(?:the\s+)?(?:first|second|third|fourth|fifth|next|last|other|same)\s+"
    r"(?:one|ones|apartment|flat|house|listing|property|option|place|room|ad)\b",
    re.IGNORECASE,
)
_ONE_OFF_REFERENCE_RE = re.compile(
    r"\b(?:as before|as mentioned|as you said|same as (?:before|last time)|"
    r"like (?:before|last time)|the same as usual)\b",
    re.IGNORECASE,
)

_AMOUNT_RE = re.compile(
    r"(?<![\w.])(\d{1,3}(?:[ ,.]\d{3})+|\d+(?:[.,]\d+)?)\s*(k|m)?(?![a-zA-Z])",
    re.IGNORECASE,
)
_CURRENCY_RE = re.compile(
    r"\b(pln|zloty|zł|eur|euro|usd|dollar|gbp)\b|€|\$|£",
    re.IGNORECASE,
)
_CURRENCY_CODES = {
    "pln": "PLN",
    "zloty": "PLN",
    "zł": "PLN",
    "eur": "EUR",
    "euro": "EUR",
    "€": "EUR",
    "usd": "USD",
    "dollar": "USD",
    "$": "USD",
    "gbp": "GBP",
    "£": "GBP",
}


def _strip_negation(content: str) -> Optional[tuple[str, bool]]:
    """Split a leading negation off a content.

    Returns (remainder, is_weak) or None when the content carries no negation.
    A weak negation is the short generic one ("no ", "not "); it only reclassifies
    a fact when what remains is a single word.
    """
    lowered = content.lower()
    for phrase in _NEGATION_PHRASES:
        if lowered.startswith(phrase):
            return content[len(phrase) :].strip(" .,:;-—"), False
    for phrase in _WEAK_NEGATIONS:
        if lowered.startswith(phrase):
            return content[len(phrase) :].strip(" .,:;-—"), True
    return None


# How many words a place name may have. "New York", "Krakow" and "Zakopane
# district" read as places; a phrase like "ance of fees" does not.
_PLACE_MAX_WORDS = 3


def _looks_like_a_place(text: str) -> bool:
    """Whether a text reads like a place name.

    A place name starts with an uppercase letter, carries no digit and is short.
    A model that lowercases everything is then left with the fact unclassified,
    which is the conservative outcome: the ranking must not filter on a place
    we could not read.
    """
    if not text or not text[0].isupper():
        return False
    if any(char.isdigit() for char in text):
        return False
    return len(text.split()) <= _PLACE_MAX_WORDS


def _is_one_off_reference(content: str) -> bool:
    """Whether the content points at something outside this turn."""
    return bool(_ORDINAL_REFERENCE_RE.search(content) or _ONE_OFF_REFERENCE_RE.search(content))


_NUMBER_GROUP_RE = re.compile(r"[,.]")


def _parse_number(text: str) -> Optional[float]:
    """Read a number whose separators may be thousands separators or a decimal point.

    A separator followed by exactly three digits is a thousands separator
    ("500,000" is 500000); any other separator is a decimal point ("500,50" is
    500.5). When several separators appear, the digits are grouped from the
    right in threes ("1.500.000" is 1500000).
    """
    groups = [group for group in _NUMBER_GROUP_RE.split(text) if group]
    if not groups:
        return None
    if len(groups) == 1:
        try:
            return float(groups[0])
        except (TypeError, ValueError):
            return None

    tail = groups[-1]
    head = groups[:-1]
    # Every group between the first and the last is a thousands group; the
    # first one may be shorter ("1.500.000").
    if len(tail) == 3 and all(len(group) == 3 for group in head[1:]):
        try:
            return float("".join(groups))
        except (TypeError, ValueError):
            return None
    # The last separator is the decimal point.
    try:
        return float("".join(head) + "." + tail)
    except (TypeError, ValueError):
        return None


def _parse_amount(raw: str) -> Optional[float]:
    """Read a number that may carry a k/m suffix and European separators."""
    text = raw.replace(" ", "").replace(" ", "")
    return _parse_number(text)


def _parse_budget(content: str) -> tuple[Optional[float], Optional[float]]:
    """Read the min and max of a budget range out of its content."""
    amounts: list[float] = []
    for match in _AMOUNT_RE.finditer(content):
        value = _parse_amount(match.group(1))
        if value is None:
            continue
        suffix = (match.group(2) or "").lower()
        if suffix == "k":
            value *= 1_000
        elif suffix == "m":
            value *= 1_000_000
        amounts.append(value)

    if not amounts:
        return None, None
    if len(amounts) == 1:
        return amounts[0], amounts[0]
    return min(amounts), max(amounts)


def _budget_currency(content: str) -> Optional[str]:
    """The currency of a budget, when the content names one."""
    match = _CURRENCY_RE.search(content)
    if not match:
        return None
    return _CURRENCY_CODES.get(match.group(0).lower())


def _normalise_budget(fact: Fact) -> Fact:
    """Normalise a budget fact into a min/max range."""
    minimum, maximum = _parse_budget(fact.content)
    if minimum is None or maximum is None:
        return fact
    currency = _budget_currency(fact.content)
    low = int(minimum)
    high = int(maximum)
    content = f"{low}-{high}" if low != high else str(low)
    if currency:
        content = f"{content} {currency}"
    return Fact(
        kind=fact.kind,
        content=content,
        listing_id=fact.listing_id,
        confidence=fact.confidence,
        budget_min=minimum,
        budget_max=maximum,
    )


def _with_content(fact: Fact, content: str) -> Fact:
    """The same fact with another content."""
    return Fact(
        kind=fact.kind,
        content=content,
        listing_id=fact.listing_id,
        confidence=fact.confidence,
        budget_min=fact.budget_min,
        budget_max=fact.budget_max,
    )


def _apply_negation(fact: Fact) -> Optional[Fact]:
    """Turn a negated content into a ruled-out area, or None when it is not one.

    "I don't want Krakow" is a ruled-out area carrying "Krakow" - never a
    preference for Krakow. A negated budget or requirement keeps its own kind:
    "I do not want to spend more than 500k" is a budget, not an area.
    """
    split = _strip_negation(fact.content)
    if split is None:
        return fact
    remainder, weak = split
    if not remainder:
        return None

    if fact.kind in ("budget", "requirement"):
        # A negated budget or a negated requirement is never an area.
        return fact

    if fact.kind == "ruled_out_area":
        # The model already classified it; only the negation is stripped.
        return _with_content(fact, remainder)

    if fact.kind == "note":
        # Only a note that reads like a PLACE NAME becomes a ruled-out area.
        if not _looks_like_a_place(remainder):
            return fact
        # A weak negation only reclassifies when what remains is one word, so
        # that "no deposit needed" stays a note.
        if weak and len(remainder.split()) != 1:
            return fact
        return Fact(
            kind="ruled_out_area",
            content=remainder,
            listing_id=fact.listing_id,
            confidence=fact.confidence,
            budget_min=fact.budget_min,
            budget_max=fact.budget_max,
        )

    # liked and disliked keep their kind and only lose the negation.
    return _with_content(fact, remainder)


def _known_listing_ids(listings: Sequence[Any]) -> set[str]:
    """The ids of the listings that were shown."""
    known: set[str] = set()
    for listing in listings or ():
        if isinstance(listing, dict):
            listing_id = listing.get("id") or listing.get("listing_id")
        else:
            listing_id = getattr(listing, "id", None) or getattr(listing, "listing_id", None)
        if listing_id:
            known.add(str(listing_id))
    return known


def _read_confidence(item: dict) -> Optional[float]:
    """Read the confidence of a payload element, or None when it is malformed.

    A missing confidence is 1.0 - the model said nothing about it. A numeric
    one is clamped to [0, 1]. A numeric string ("0.8") is parsed. Anything else
    (null, a bool, "high", a dict) is a malformed confidence: the fact is
    dropped rather than promoted to certainty.
    """
    if "confidence" not in item:
        return 1.0

    raw = item["confidence"]
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        value = float(raw)
    elif isinstance(raw, str):
        try:
            value = float(raw.strip())
        except (TypeError, ValueError):
            return None
    else:
        return None

    if not math.isfinite(value):
        return None
    return min(max(value, 0.0), 1.0)


def _read_listing_id(item: dict) -> tuple[Optional[str], bool]:
    """Read the listing id of a payload element.

    Returns (listing_id, ok). The ids are compared as strings, so a numeric
    id is read as its string form rather than dropped as malformed.
    """
    raw = item.get("listing_id")
    if raw is None:
        return None, True
    if isinstance(raw, bool):
        return None, False
    if isinstance(raw, int):
        return str(raw), True
    if isinstance(raw, float):
        if not math.isfinite(raw) or not raw.is_integer():
            return None, False
        return str(int(raw)), True
    if not isinstance(raw, str) or not raw.strip():
        return None, False
    return raw.strip(), True


def _build_fact(item: Any, known_ids: set[str]) -> Optional[Fact]:
    """Turn one element of the payload into a fact, or None when it is noise."""
    if not isinstance(item, dict):
        logger.warning("Buyer memory extraction: dropping a payload element that is not an object")
        return None

    kind = item.get("kind")
    if not isinstance(kind, str) or kind not in FACT_KINDS:
        logger.warning("Buyer memory extraction: dropping a fact with an unknown kind %r", kind)
        return None

    content = item.get("content")
    if not isinstance(content, str) or not content.strip():
        logger.warning("Buyer memory extraction: dropping a fact without content")
        return None
    content = content.strip()

    listing_id, ok = _read_listing_id(item)
    if not ok:
        logger.warning("Buyer memory extraction: dropping a fact with a malformed listing id")
        return None
    if listing_id is not None and known_ids and listing_id not in known_ids:
        logger.warning("Buyer memory extraction: dropping a fact about an unknown listing")
        return None

    confidence = _read_confidence(item)
    if confidence is None:
        logger.warning("Buyer memory extraction: dropping a fact with a malformed confidence")
        return None

    fact = Fact(
        kind=kind,
        content=content,
        listing_id=listing_id,
        confidence=confidence,
    )

    if kind in _LISTING_KINDS and not fact.listing_id:
        logger.warning("Buyer memory extraction: dropping a %s fact without a listing", kind)
        return None

    if _is_one_off_reference(fact.content) and not fact.listing_id:
        logger.warning("Buyer memory extraction: dropping a one-off reference")
        return None

    fact = _apply_negation(fact)
    if fact is None:
        return None

    if fact.kind == "budget":
        fact = _normalise_budget(fact)

    return fact


# --------------------------------------------------------------------------------------
# The extractor
# --------------------------------------------------------------------------------------


async def extract_buyer_facts(
    messages: Sequence[Any],
    answer: Any,
    listings: Sequence[Any] = (),
    llm: Optional[Any] = None,
) -> list[Fact]:
    """Read a buyer's turn into durable facts.

    Args:
        messages: The conversation so far - dicts or objects with a role and content.
        answer: The assistant's answer for this turn.
        listings: The listings that were shown in this turn.
        llm: The chat model to use, injected by the caller (Task #79 resolves it
            and passes it in). The module never resolves a provider itself.
            Without an LLM there are no facts.

    Returns:
        The durable facts of the turn. A prose answer, a malformed payload or a
        missing LLM yields an empty list - never an exception.
    """
    if llm is None:
        logger.debug("Buyer memory extraction: no LLM, no facts extracted")
        return []

    prompt = build_extraction_prompt(messages, answer, listings)

    try:
        # The model call is blocking, and this function is async. The house
        # pattern (api/routers/chat.py) runs a blocking call in a thread, so
        # the event loop is not stalled while the provider thinks.
        response = await asyncio.to_thread(llm.invoke, prompt)
    except Exception as exc:
        logger.warning("Buyer memory extraction: the model call failed (%s)", exc)
        return []

    raw = getattr(response, "content", None)
    if not isinstance(raw, str):
        raw = _as_text(response)

    payload = _parse_payload(raw)
    if payload is None:
        logger.warning(
            "Buyer memory extraction: the answer is not a JSON array, no facts extracted"
        )
        return []

    known_ids = _known_listing_ids(listings)
    facts: list[Fact] = []
    seen: set[tuple[str, str]] = set()

    for item in payload:
        fact = _build_fact(item, known_ids)
        if fact is None:
            continue
        key = (fact.kind, fact.content.lower())
        if key in seen:
            continue
        seen.add(key)
        facts.append(fact)
        if len(facts) >= MAX_FACTS:
            logger.warning("Buyer memory extraction: the turn carried more facts than kept")
            break

    logger.debug("Buyer memory extraction: %d durable facts", len(facts))
    return facts
