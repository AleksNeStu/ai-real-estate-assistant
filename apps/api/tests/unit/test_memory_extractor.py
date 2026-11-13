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
    async def test_non_numeric_confidence_falls_back_to_one(self):
        llm = make_llm('[{"kind": "note", "content": "buying alone", "confidence": "high"}]')

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert facts == [Fact(kind="note", content="buying alone", confidence=1.0)]

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
    async def test_a_negated_value_becomes_a_ruled_out_area(self):
        llm = make_llm('[{"kind": "requirement", "content": "I don\'t want Krakow"}]')

        facts = await extract_buyer_facts(MESSAGES, "Here are three flats.", LISTINGS, llm=llm)

        assert facts == [Fact(kind="ruled_out_area", content="Krakow")]

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
