"""
The proof that the demo's answer comes from a real model, not the local mock.

Task #97 says the headline claim of the public demo - "the demo answers with a
real model" - is not proven by any test. The e2e suite mocks the provider at
the browser boundary, and the one suite that talks to a running backend still
selects the local `MockLLM`, so a green pipeline says nothing about the
provider.

This module is that proof, and it is a proof in both directions:

* against a backend that PROMISES a real provider, the arithmetic probe
  answers with the computed value and with nothing the mock could have said;
* the negative control runs in the ordinary in-process suite and shows that the
  SAME assertions cannot pass under `MockLLM` - the discriminator discriminates
  by construction, without any service being swapped.

The two gates the live proof needs:

``E2E_BASE_URL``
    the backend to talk to. Empty means the suite runs in-process with the LLM
    mocked, so there is no provider to prove - the module skips (TaskMaster
    #97's third acceptance criterion: the pull-request suite stays green with
    no key present).

``E2E_REQUIRE_REAL_PROVIDER``
    the promise that this backend answers with a real model. It is what makes
    the proof a proof: the deployment is asserted, not asked whether it feels
    like asserting anything. The pipeline's own `compose-stack` job runs the
    MOCK stack and sets `E2E_BASE_URL` against it, so it does not make the
    promise and the live tests skip there; the `make e2e-real-provider` target
    brings a stack up with a real provider and makes it.

A deployment that promised a provider and then answered with the mock fails
the live proof - that is the whole point of the promise.
"""

from __future__ import annotations

import json
import os
import re

import pytest

# The canned answers the mock serves live in the module that defines them.
# This suite's import root is apps/api (pytest.ini's `pythonpath = . ../..`),
# so the module is `core.demo` here - the same way the sibling unit test
# imports it. `apps.api.core.demo` would load a second copy of the module
# under a different name, and the copy would drift from the one the mock
# actually serves.
from core.demo import DEMO_RESPONSES, MockLLM

# The switch the suite already uses (see conftest.py): empty means the suite
# runs in-process with the LLM mocked, set means it talks to a real backend.
E2E_BASE_URL = os.environ.get("E2E_BASE_URL", "").strip()

# The promise that the backend answers with a real model. See the module
# docstring: the pipeline's mock stack does not make it.
REQUIRE_REAL_PROVIDER = os.environ.get("E2E_REQUIRE_REAL_PROVIDER", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# A question the mock cannot answer: `MockLLM` picks a random index into the
# four canned strings and ignores the question entirely.
ARITHMETIC_QUESTION = "What is 17 plus 25? Reply with the number only."
EXPECTED_ANSWER = 42

requires_real_provider = pytest.mark.skipif(
    not E2E_BASE_URL or not REQUIRE_REAL_PROVIDER,
    reason=(
        "the live proof runs only where a real provider is promised: E2E_BASE_URL "
        "(the backend to talk to) and E2E_REQUIRE_REAL_PROVIDER=1 (the promise "
        "that this backend answers with a real model) must both be set"
    ),
)


def _numbers_in(text: str) -> set[int]:
    """Every whole number the text carries.

    A reply may say "42", "42." or "17 + 25 = 42", so the check reads the
    numbers rather than matching one whole string. Thousands separators are
    removed, so "1,234" reads as 1234 and not as 1 and 234, and "42,000" reads
    as 42000 - a price is not the answer. A decimal is not a whole number, so
    "3.2%" carries neither 3 nor 2.
    """
    values: set[int] = set()
    for raw in re.findall(r"\d[\d,]*(?:\.\d+)?", text):
        value = float(raw.replace(",", ""))
        if value.is_integer():
            values.add(int(value))
    return values


def _carries_the_computed_value(text: str) -> bool:
    """Whether the text carries the answer the arithmetic has."""
    if EXPECTED_ANSWER in _numbers_in(text):
        return True
    # A model may spell the number out. Rare, but it must not fail the proof.
    lowered = text.lower()
    return "forty-two" in lowered or "forty two" in lowered


def _assert_a_real_model_answered(answer: str) -> None:
    """
    The assertions that tell a real model's answer from the mock's.

    They are one function on purpose: the live test runs them against the
    backend's answer, and the negative control runs the SAME function against
    the mock's answers and requires it to reject them. A discriminator that
    only exists in the live test could be weakened without anyone noticing.
    """
    assert answer.strip(), "the answer is empty"
    # The mock answers with one of the four canned strings, verbatim.
    canned = {text.strip() for text in DEMO_RESPONSES}
    assert answer.strip() not in canned, "the answer is one of the mock's canned answers"
    # And the mock can never carry the computed value.
    assert _carries_the_computed_value(answer), (
        f"the answer does not carry {EXPECTED_ANSWER}: {answer[:200]!r}"
    )


def _answer_from_sse(body: str) -> str:
    """The answer a text/event-stream body carries.

    The chat endpoint answers in SSE when the request asks for a stream. Each
    `data:` line is either the agent's chunk (a JSON envelope with a
    ``content`` key) or plain prose; both are collected, and the ``[DONE]``
    sentinel ends the body.
    """
    parts: list[str] = []
    for line in body.splitlines():
        if not line.startswith("data:"):
            continue
        payload = line[len("data:") :].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            parsed = json.loads(payload)
        except ValueError:
            parsed = None
        if isinstance(parsed, dict):
            content = parsed.get("content")
            if isinstance(content, str):
                parts.append(content)
            # An envelope without the answer in it - the metrics, the
            # listings - is not the answer, and nothing in it may satisfy
            # the proof.
            continue
        parts.append(payload)
    return "".join(parts)


async def _ask(client, headers: dict[str, str], question: str) -> str:
    """Ask the chat endpoint and return the answer's text.

    The non-streaming path is the default one and answers with a JSON body
    carrying the answer in `response`. A deployment that answers in SSE is
    read as SSE instead, so the proof does not depend on the transport.
    """
    resp = await client.post(
        "/api/v1/chat",
        json={"message": question, "stream": False},
        headers=headers,
    )
    assert resp.status_code == 200, (
        f"the chat endpoint answered {resp.status_code}: {resp.text[:500]}"
    )
    if "text/event-stream" in resp.headers.get("content-type", ""):
        return _answer_from_sse(resp.text)
    data = resp.json()
    return str(data.get("response") or data.get("answer") or "")


@requires_real_provider
@pytest.mark.asyncio
class TestTheDemoAnswersWithARealModel:
    """The live proof - it runs only where a real provider is promised."""

    async def test_the_capabilities_report_a_provider_and_not_the_mock(
        self, e2e_client, api_headers
    ):
        resp = await e2e_client.get("/api/v1/capabilities", headers=api_headers)
        assert resp.status_code == 200, f"capabilities answered {resp.status_code}"

        llm = resp.json()["llm"]
        # "provider" means a real model answers; "local-model" means the
        # canned answers do.
        assert llm["mode"] == "provider", llm
        assert llm["provider"] not in {"demo", "mock"}, llm
        assert llm["provider"], llm

    async def test_the_answer_is_the_model_s_own(self, e2e_client, api_headers):
        answer = await _ask(e2e_client, api_headers, ARITHMETIC_QUESTION)

        _assert_a_real_model_answered(answer)


def test_the_mock_cannot_answer_the_arithmetic_question():
    """
    The negative control - no backend needed, so it runs in the ordinary suite.

    This is #97's "it fails when the provider is swapped back to MockLLM"
    criterion, met as a property rather than as a second CI run: the mock's
    answers are the four canned strings, none of them carries the computed
    value, and the assertions the live proof runs REJECT every one of them.
    """
    mock = MockLLM(response_selector="sequential")
    canned = {text.strip() for text in DEMO_RESPONSES}

    seen: set[str] = set()
    for _ in range(len(DEMO_RESPONSES)):
        answer = mock.invoke(ARITHMETIC_QUESTION).content
        # The mock always stores a string; narrowing it here keeps the rest of
        # the assertions type-safe and documents the contract it keeps.
        assert isinstance(answer, str), "the mock answers with a string"

        # The mock ignores the question: every answer is one of the four.
        assert answer.strip() in canned
        seen.add(answer.strip())
        # And none of them carries the computed value.
        assert not _carries_the_computed_value(answer)
        assert EXPECTED_ANSWER not in _numbers_in(answer)
        # The live proof's own assertions reject every one of them - the same
        # function, so a weakened discriminator would fail here too.
        with pytest.raises(AssertionError):
            _assert_a_real_model_answered(answer)

    # The control saw every canned answer, not four copies of one of them.
    assert seen == canned
