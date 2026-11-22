"""The tool that answers what a flat is worth from the official register.

The register of notarial prices is the only price source in this project that
is not an asking price and not an estimate: it is what people actually paid,
written down by a notary. When the assistant is asked what a flat is worth,
this is the tool that answers — and it answers with the sales it stands on,
because a number without them is a guess wearing a suit.
"""

from typing import Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from agents.services.valuation import ValuationOutcome
from tools.async_bridge import run_detached


class RcnValuationInput(BaseModel):
    """What is needed to value a flat against the register."""

    city: str = Field(description="The city the flat is in, for example Kraków.")
    street: str = Field(
        default="",
        description="The street the flat is on, when it is known.",
    )
    area_sqm: Optional[float] = Field(
        default=None,
        description="The usable area of the flat in square metres.",
    )
    rooms: Optional[int] = Field(
        default=None,
        description="The number of rooms, when it is known.",
    )


def _run_detached(coroutine: Any) -> Any:
    """Run a coroutine to the end, whatever loop the caller is in."""
    return run_detached(coroutine)


async def _value(
    city: str,
    street: str,
    area_sqm: Optional[float],
    rooms: Optional[int],
) -> ValuationOutcome:
    """Value an address from the stored register."""
    from agents.services.valuation import RcnValuationProvider
    from db.database import standalone_session

    async with standalone_session() as session:
        provider = RcnValuationProvider(session)
        return await provider.outcome(
            {"city": city, "street": street, "area_sqm": area_sqm, "rooms": rooms}
        )


def _format(outcome: ValuationOutcome) -> str:
    """Say what the flat is worth, and what the answer rests on."""
    if outcome.estimated_value is None:
        reason = outcome.notes[0] if outcome.notes else "no comparable sale was found."
        return f"No estimate for this address: {reason}"

    lines = [
        f"Estimated value: {outcome.estimated_value:,.0f} {outcome.currency}"
        f" (median {outcome.price_per_sqm_median:,.0f} PLN/m²)."
        if outcome.price_per_sqm_median
        else f"Estimated value: {outcome.estimated_value:,.0f} {outcome.currency}.",
        f"Comparison area: {outcome.comparison_area}.",
    ]
    if outcome.period_start and outcome.period_end:
        lines.append(
            f"Based on {outcome.sample_size} registered sale(s) between "
            f"{outcome.period_start.isoformat()} and {outcome.period_end.isoformat()}."
        )
    if outcome.low is not None and outcome.high is not None:
        lines.append(f"Range: {outcome.low:,.0f} – {outcome.high:,.0f} {outcome.currency}.")
    lines.append(f"Confidence: {outcome.confidence}.")

    if outcome.comparables:
        lines.append("The sales it stands on:")
        for comparable in outcome.comparables[:5]:
            lines.append(
                f"- {comparable['address']}: {comparable['area_sqm']:,.1f} m², "
                f"{comparable['price']:,.0f} PLN "
                f"({comparable['price_per_sqm']:,.0f} PLN/m²), "
                f"sold {comparable['transaction_date']}"
                + (
                    f", deed {comparable['deed_reference']}"
                    if comparable.get("deed_reference")
                    else ""
                )
            )

    for note in outcome.notes:
        lines.append(f"Note: {note}")

    return "\n".join(lines)


class RcnValuationTool(BaseTool):
    """Value a flat from the prices people actually paid."""

    name: str = "rcn_property_valuation"
    description: str = (
        "Value a flat in Poland from the official register of notarial prices — the "
        "prices people actually paid for comparable flats, with the sales and the "
        "period they cover. Use it when the user asks what a flat is worth, what a "
        "square metre costs in a city, or for a price estimate from real sales. It "
        "answers for Poland only, and it says how much evidence the number rests on."
    )
    args_schema: Type[RcnValuationInput] = RcnValuationInput

    def _run(
        self,
        city: str,
        street: str = "",
        area_sqm: Optional[float] = None,
        rooms: Optional[int] = None,
    ) -> str:
        """Value a flat, from synchronous code."""
        try:
            outcome = _run_detached(_value(city, street, area_sqm, rooms))
        except Exception as exc:  # pragma: no cover - the network is not always there
            return f"The official price register could not be read: {exc}"
        return _format(outcome)

    async def _arun(
        self,
        city: str,
        street: str = "",
        area_sqm: Optional[float] = None,
        rooms: Optional[int] = None,
    ) -> str:
        """Value a flat, from the event loop."""
        try:
            outcome = await _value(city, street, area_sqm, rooms)
        except Exception as exc:  # pragma: no cover - the network is not always there
            return f"The official price register could not be read: {exc}"
        return _format(outcome)
