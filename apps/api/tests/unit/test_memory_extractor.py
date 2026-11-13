"""Tests for the buyer-memory extractor (Task #78)."""

import inspect
from unittest.mock import MagicMock

import pytest

from agents import memory_extractor
from agents.memory_extractor import Fact, build_extraction_prompt, extract_buyer_facts


def make_llm(payload: str) -> MagicMock:
    """A stub LLM that answers with a fixed string."""
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content=payload)
    return llm


MESSAGES = [
    {"role": "user", "content": "I am looking in Krakow, budget around 400k PLN"},
    {"role": "assistant", "content": "Here are three flats in Krakow."},
]

LISTINGS = [
    {
        "id": "listing-1",
        "title": "Flat on Orla",
        "city": "Krakow",
        "price": 390000,
        "currency": "PLN",
    },
    {
        "id": "listing-2",
        "title": "Flat in Nowa Huta",
        "city": "Krakow",
        "price": 310000,
        "currency": "PLN",
    },
]


class TestExtraction:
    @pytest.mark.asyncio
    async def test_json_payload_yields_exactly_the_parsed_facts(self):
        payload = (
            '[{"kind": "requirement", "content": "needs a balcony", "confidence": 0.9},'
            ' {"kind": "liked", "content": "the balcony flat", "listing_id": "listing-1",'
            ' "confidence": 0.8}]'
        )
        llm = make_llm(payload)

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert facts == [
            Fact(kind="requirement", content="needs a balcony", confidence=0.9),
            Fact(
                kind="liked",
                content="the balcony flat",
                listing_id="listing-1",
                confidence=0.8,
            ),
        ]

    @pytest.mark.asyncio
    async def test_prose_yields_no_facts(self):
        llm = make_llm("Sure! I found a few flats in Krakow that fit your budget.")

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert facts == []

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "payload",
        [
            "not json at all",
            '{"kind": "budget", "content": "400000"}',
            "[1, 2, 3]",
            '[{"kind": "budget"}]',
            '[{"content": "400000"}]',
            '[{"kind": "unknown_kind", "content": "400000"}]',
            "[{",
        ],
    )
    async def test_malformed_payload_yields_no_facts_and_does_not_raise(self, payload):
        llm = make_llm(payload)

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert facts == []

    @pytest.mark.asyncio
    async def test_a_numeric_string_confidence_is_parsed(self):
        llm = make_llm('[{"kind": "note", "content": "buying alone", "confidence": "0.8"}]')

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert facts == [Fact(kind="note", content="buying alone", confidence=0.8)]

    @pytest.mark.asyncio
    async def test_a_missing_confidence_is_full_confidence(self):
        llm = make_llm('[{"kind": "note", "content": "buying alone"}]')

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert facts == [Fact(kind="note", content="buying alone", confidence=1.0)]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("raw", ["null", "true", '"high"', "{}", "[]"])
    async def test_a_malformed_confidence_drops_the_fact(self, raw):
        llm = make_llm(f'[{{"kind": "note", "content": "buying alone", "confidence": {raw}}}]')

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert facts == []

    @pytest.mark.asyncio
    async def test_a_failing_model_call_yields_no_facts(self):
        llm = MagicMock()
        llm.invoke.side_effect = RuntimeError("provider is down")

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert facts == []

    @pytest.mark.asyncio
    async def test_no_llm_yields_no_facts(self):
        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=None)

        assert facts == []


class TestTheNoiseGuards:
    @pytest.mark.asyncio
    async def test_a_kind_outside_the_closed_set_is_dropped(self):
        llm = make_llm(
            '[{"kind": "location", "content": "Krakow"},'
            ' {"kind": "requirement", "content": "needs a balcony"}]'
        )

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert [fact.kind for fact in facts] == ["requirement"]

    @pytest.mark.asyncio
    async def test_a_negated_requirement_keeps_its_kind(self):
        llm = make_llm('[{"kind": "requirement", "content": "I don\'t want Krakow"}]')

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert facts == [Fact(kind="requirement", content="I don't want Krakow")]

    @pytest.mark.asyncio
    async def test_a_ruled_out_area_loses_its_negation(self):
        llm = make_llm('[{"kind": "ruled_out_area", "content": "I don\'t want Krakow"}]')

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert facts == [Fact(kind="ruled_out_area", content="Krakow")]

    @pytest.mark.asyncio
    async def test_a_budget_range_is_normalised_into_min_and_max(self):
        llm = make_llm('[{"kind": "budget", "content": "between 300k and 450k PLN"}]')

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert len(facts) == 1
        fact = facts[0]
        assert fact.kind == "budget"
        assert fact.budget_min == 300000
        assert fact.budget_max == 450000
        assert fact.content == "300000-450000 PLN"

    @pytest.mark.asyncio
    async def test_a_one_off_reference_without_a_listing_is_dropped(self):
        llm = make_llm('[{"kind": "requirement", "content": "the second one"}]')

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert facts == []

    @pytest.mark.asyncio
    async def test_a_listing_fact_without_a_listing_id_is_dropped(self):
        llm = make_llm('[{"kind": "liked", "content": "the balcony flat"}]')

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert facts == []

    @pytest.mark.asyncio
    async def test_a_listing_fact_about_an_unknown_listing_is_dropped(self):
        llm = make_llm(
            '[{"kind": "liked", "content": "the balcony flat", "listing_id": "listing-99"}]'
        )

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert facts == []

    @pytest.mark.asyncio
    async def test_repeated_facts_are_kept_once(self):
        llm = make_llm(
            '[{"kind": "requirement", "content": "needs a balcony"},'
            ' {"kind": "requirement", "content": "needs a balcony"}]'
        )

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert len(facts) == 1


class TestTheInjection:
    @pytest.mark.asyncio
    async def test_the_llm_is_the_only_model_the_module_uses(self):
        llm = make_llm('[{"kind": "note", "content": "buying alone"}]')

        await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        llm.invoke.assert_called_once()
        prompt = llm.invoke.call_args.args[0]
        assert "buying alone" not in prompt
        assert "Krakow" in prompt

    def test_the_module_never_resolves_a_provider(self):
        source = inspect.getsource(memory_extractor)

        assert "provider_factory" not in source
        assert "get_llm(" not in source
        assert not hasattr(memory_extractor, "get_llm")

    def test_the_prompt_carries_the_rules(self):
        prompt = build_extraction_prompt(MESSAGES, "Here are three flats.", LISTINGS)

        assert "ruled_out_area" in prompt
        assert "JSON array" in prompt
        for kind in memory_extractor.FACT_KINDS:
            assert kind in prompt


class TestTheKindSet:
    def test_the_closed_set_matches_the_service(self):
        from services.buyer_memory_service import VALID_KINDS

        assert memory_extractor.FACT_KINDS == VALID_KINDS


class TestTheAmounts:
    """A thousands separator is not a decimal point."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("500,000", 500000.0),
            ("1.500.000", 1500000.0),
            ("500.000", 500000.0),
            ("500,50", 500.5),
            ("500.5", 500.5),
            ("500", 500.0),
            ("1,5", 1.5),
        ],
    )
    def test_every_spelling_is_read_as_one_number(self, raw, expected):
        assert memory_extractor._parse_amount(raw) == expected

    @pytest.mark.asyncio
    async def test_a_thousands_separator_keeps_the_budget_whole(self):
        llm = make_llm('[{"kind": "budget", "content": "up to 500,000 PLN"}]')

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert len(facts) == 1
        assert facts[0].budget_max == 500000.0
        assert facts[0].budget_min is None

    @pytest.mark.asyncio
    async def test_a_grouped_amount_keeps_the_budget_whole(self):
        llm = make_llm('[{"kind": "budget", "content": "up to 1.500.000 PLN"}]')

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert len(facts) == 1
        assert facts[0].budget_max == 1500000.0


class TestTheSideOfTheBudget:
    """A floor stays a floor and a ceiling stays a ceiling.

    The content is the only channel a stored fact has to the ranking, so the
    side of the budget has to survive the normalisation. When it did not, the
    ranking read "at least 300k" as a ceiling and enforced the buyer's own
    words backwards.
    """

    @pytest.mark.asyncio
    async def test_a_floor_stays_a_floor(self):
        llm = make_llm('[{"kind": "budget", "content": "at least 300k PLN"}]')

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert len(facts) == 1
        assert facts[0].budget_min == 300000.0
        assert facts[0].budget_max is None
        assert facts[0].content == "at least 300000 PLN"

    @pytest.mark.asyncio
    async def test_a_ceiling_stays_a_ceiling(self):
        llm = make_llm('[{"kind": "budget", "content": "up to 300k PLN"}]')

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert len(facts) == 1
        assert facts[0].budget_max == 300000.0
        assert facts[0].budget_min is None
        assert facts[0].content == "300000 PLN"

    @pytest.mark.asyncio
    async def test_a_negated_more_than_is_a_ceiling(self):
        llm = make_llm('[{"kind": "budget", "content": "I do not want to spend more than 500k"}]')

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert len(facts) == 1
        assert facts[0].budget_max == 500000.0
        assert facts[0].budget_min is None

    @pytest.mark.asyncio
    async def test_a_range_carries_both_bounds(self):
        llm = make_llm('[{"kind": "budget", "content": "between 300k and 450k PLN"}]')

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert len(facts) == 1
        assert facts[0].budget_min == 300000.0
        assert facts[0].budget_max == 450000.0
        assert facts[0].content == "300000-450000 PLN"

    @pytest.mark.asyncio
    async def test_a_floor_and_a_ceiling_of_the_same_amount_are_two_facts(self):
        floor = await extract_buyer_facts(
            MESSAGES,
            "Here are three flats.",
            LISTINGS,
            llm=make_llm('[{"kind": "budget", "content": "at least 300k PLN"}]'),
        )
        ceiling = await extract_buyer_facts(
            MESSAGES,
            "Here are three flats.",
            LISTINGS,
            llm=make_llm('[{"kind": "budget", "content": "up to 300k PLN"}]'),
        )

        assert floor[0].content != ceiling[0].content


class TestTheNegation:
    """A negation is not a place name."""

    @pytest.mark.asyncio
    async def test_a_negated_budget_is_never_reclassified(self):
        llm = make_llm('[{"kind": "budget", "content": "I do not want to spend more than 500k"}]')

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert len(facts) == 1
        assert facts[0].kind == "budget"
        assert facts[0].budget_max == 500000.0

    @pytest.mark.asyncio
    async def test_a_negated_requirement_is_never_reclassified(self):
        llm = make_llm('[{"kind": "requirement", "content": "no parking"}]')

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert facts == [Fact(kind="requirement", content="no parking")]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "content",
        [
            "never mind",
            "avoidance of fees",
        ],
    )
    async def test_a_note_that_is_not_a_place_stays_a_note(self, content):
        llm = make_llm(f'[{{"kind": "note", "content": "{content}"}}]')

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert facts == [Fact(kind="note", content=content)]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("content", "expected"),
        [
            ("I don't want Krakow", "Krakow"),
            ("no Krakow", "Krakow"),
            ("I don't like Kraków", "Kraków"),
        ],
    )
    async def test_a_note_that_reads_like_a_place_becomes_a_ruled_out_area(self, content, expected):
        llm = make_llm(f'[{{"kind": "note", "content": "{content}"}}]')

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert facts == [Fact(kind="ruled_out_area", content=expected)]


class TestTheFailurePaths:
    """A malformed answer yields zero facts and never an exception."""

    @pytest.mark.asyncio
    async def test_trailing_text_after_the_array_yields_no_facts(self):
        llm = make_llm('[{"kind": "note", "content": "buying alone"}] and that is all')

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert facts == []

    @pytest.mark.asyncio
    async def test_prose_with_a_json_fragment_yields_no_facts(self):
        llm = make_llm('Here you go: [{"kind": "note", "content": "buying alone"}]')

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert facts == []

    @pytest.mark.asyncio
    async def test_a_model_that_returns_nothing_yields_no_facts(self):
        llm = MagicMock()
        llm.invoke.return_value = None

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert facts == []

    @pytest.mark.asyncio
    async def test_a_model_that_returns_an_object_without_content_yields_no_facts(self):
        class Bare:
            pass

        llm = MagicMock()
        llm.invoke.return_value = Bare()

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert facts == []


class TestTheListingIds:
    """The ids are compared as strings, so a numeric id is a valid id."""

    NUMERIC_LISTINGS = [
        {
            "id": 123,
            "title": "Flat on Orla",
            "city": "Krakow",
            "price": 390000,
            "currency": "PLN",
        }
    ]

    @pytest.mark.asyncio
    async def test_a_numeric_listing_id_is_kept(self):
        llm = make_llm('[{"kind": "liked", "content": "the balcony flat", "listing_id": 123}]')

        facts = await extract_buyer_facts(
            MESSAGES, "Here are three flats.", self.NUMERIC_LISTINGS, llm=llm
        )

        assert facts == [
            Fact(kind="liked", content="the balcony flat", listing_id="123", confidence=1.0)
        ]

    @pytest.mark.asyncio
    async def test_a_numeric_listing_id_that_was_not_shown_is_dropped(self):
        llm = make_llm('[{"kind": "liked", "content": "the balcony flat", "listing_id": 999}]')

        facts = await extract_buyer_facts(
            MESSAGES, "Here are three flats.", self.NUMERIC_LISTINGS, llm=llm
        )

        assert facts == []

    @pytest.mark.asyncio
    async def test_a_listing_fact_is_dropped_when_no_listing_was_shown(self):
        """No listing shown means every id is unknown.

        The guard used to be skipped on an empty set, so a model could name
        any id at all and the fact was stored.
        """
        llm = make_llm(
            '[{"kind": "liked", "content": "the balcony flat", "listing_id": "totally-made-up-id"}]'
        )

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", (), llm=llm)

        assert facts == []


class TestTheScaleWords:
    """The scale words the ranking reads are read here too.

    A budget the extractor cannot read is a budget the ranking never sees:
    "300 thousand" used to be stored as "300", which the ranking ignores.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("content", "expected"),
        [
            ("300 thousand PLN", 300000.0),
            ("500 tys PLN", 500000.0),
            ("1.5 million PLN", 1500000.0),
            ("2 mln PLN", 2000000.0),
            ("500k PLN", 500000.0),
        ],
    )
    async def test_the_scale_is_read(self, content, expected):
        llm = make_llm(f'[{{"kind": "budget", "content": "{content}"}}]')

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert len(facts) == 1
        assert facts[0].budget_max == expected
        assert facts[0].content == f"{int(expected)} PLN"

    @pytest.mark.asyncio
    async def test_a_number_that_is_not_a_price_is_left_alone(self):
        """Three rooms is not a budget, and it is not turned into one."""
        llm = make_llm('[{"kind": "budget", "content": "3 rooms"}]')

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert facts[0].content == "3 rooms"
        assert facts[0].budget_min is None
        assert facts[0].budget_max is None
