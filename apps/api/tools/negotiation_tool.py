"""
Negotiation helper tool for property price analysis and outreach.

Provides a LangChain BaseTool that:
- Analyzes a property's market position using comparable listings
- Suggests a realistic price band (lower / mid / upper)
- Recommends an opening offer and key negotiation arguments
- Generates an outreach email or message based on user tone preference
- Includes a legal disclaimer in every output
"""

import statistics
from typing import Any, Dict, List, Optional

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

LEGAL_DISCLAIMER = (
    "\n\n---\n"
    "**Disclaimer:** This negotiation analysis is for informational purposes only "
    "and does not constitute legal, financial, or real-estate advice. "
    "Consult a licensed professional before making any binding decisions."
)

VALID_TONES = {"formal", "friendly", "assertive"}

# --------------------------------------------------------------------------- #
# Input / Output schemas
# --------------------------------------------------------------------------- #


class NegotiationInput(BaseModel):
    """Input for the negotiation helper tool."""

    property_identifier: str = Field(
        description=(
            "Property address or property ID to analyze. "
            "If it looks like an ID (no spaces, short), it is treated as an ID; "
            "otherwise it is treated as an address / search query."
        ),
        min_length=1,
    )
    user_budget: Optional[float] = Field(
        default=None,
        description="Buyer's maximum budget (same currency as property listing).",
        gt=0,
    )
    tone: str = Field(
        default="formal",
        description="Tone for the outreach template: 'formal', 'friendly', or 'assertive'.",
    )


# --------------------------------------------------------------------------- #
# Tool implementation
# --------------------------------------------------------------------------- #


class NegotiationTool(BaseTool):
    """Analyse a property's market position and suggest a negotiation strategy."""

    name: str = "negotiation_helper"
    description: str = (
        "Analyse market data for a specific property and suggest a negotiation "
        "strategy with a realistic price band. Generates an outreach email or "
        "message based on the chosen tone (formal / friendly / assertive). "
        "Input: property address or ID, optional buyer budget, tone preference."
    )
    args_schema: type[NegotiationInput] = NegotiationInput

    _vector_store: Any = PrivateAttr()

    def __init__(self, vector_store: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._vector_store = vector_store

    # ------------------------------------------------------------------ #
    # Public helper (used by the FastAPI endpoint as well)
    # ------------------------------------------------------------------ #

    @staticmethod
    def analyse(
        *,
        target: Dict[str, Any],
        comparables: List[Dict[str, Any]],
        user_budget: Optional[float] = None,
        tone: str = "formal",
    ) -> Dict[str, Any]:
        """Pure-logic negotiation analysis — no I/O, easy to unit-test.

        Args:
            target: Metadata dict of the subject property.
            comparables: List of metadata dicts for nearby / similar listings.
            user_budget: Optional buyer maximum budget.
            tone: One of ``formal``, ``friendly``, ``assertive``.

        Returns:
            Dict with keys: price_band, opening_offer, arguments, email_template,
            disclaimer.
        """
        tone = tone.lower()
        if tone not in VALID_TONES:
            tone = "formal"

        asking_price = _safe_float(target.get("price"))
        area = _safe_float(target.get("area_sqm"))
        city = target.get("city", "the area")
        ptype = target.get("property_type", "property")
        rooms = target.get("rooms")

        # ------ Comparable prices ------ #
        comp_prices = [p for p in (_safe_float(c.get("price")) for c in comparables) if p and p > 0]
        comp_ppsqm = [
            p for p in (_safe_float(c.get("price_per_sqm")) for c in comparables) if p and p > 0
        ]

        if not comp_prices:
            # Fallback: derive from target itself with conservative band
            if asking_price and asking_price > 0:
                lower: Optional[float] = round(asking_price * 0.90, -2)
                mid: Optional[float] = round(asking_price * 0.95, -2)
                upper: Optional[float] = round(asking_price * 0.98, -2)
            else:
                lower = mid = upper = None
        else:
            avg_price = statistics.mean(comp_prices)
            std_price = statistics.stdev(comp_prices) if len(comp_prices) >= 2 else avg_price * 0.05

            lower = round(max(avg_price - 1.0 * std_price, 0), -2)
            mid = round(avg_price, -2)
            upper = round(avg_price + 0.5 * std_price, -2)

        # Adjust for per-sqm if available
        if comp_ppsqm and area and area > 0:
            avg_ppsqm = statistics.mean(comp_ppsqm)
            implied_price = round(avg_ppsqm * area, -2)
            if mid is None:
                mid = implied_price
            else:
                mid = round((mid + implied_price) / 2, -2)
            if lower is None:
                lower = round(implied_price * 0.92, -2)
            if upper is None:
                upper = round(implied_price * 1.03, -2)

        # ------ Opening offer ------ #
        if mid and asking_price and asking_price > 0:
            # Suggest 3-7 % below asking, capped by the lower band
            raw_offer = asking_price * 0.95
            opening_offer = round(min(raw_offer, lower or raw_offer), -2)
        elif mid:
            opening_offer = round(mid * 0.95, -2)
        else:
            opening_offer = None

        # If user_budget is provided, cap the opening offer
        if opening_offer and user_budget and user_budget > 0:
            opening_offer = min(opening_offer, round(user_budget * 0.97, -2))

        # ------ Negotiation arguments ------ #
        arguments: List[str] = []

        if comp_prices and asking_price and asking_price > 0:
            avg_comp = statistics.mean(comp_prices)
            if asking_price > avg_comp * 1.05:
                arguments.append(
                    f"Asking price is {((asking_price / avg_comp) - 1) * 100:.1f}% above "
                    f"the comparable average (${avg_comp:,.0f})."
                )

        if comp_ppsqm and area and area > 0:
            target_ppsqm = asking_price / area if asking_price and asking_price > 0 else None
            avg_ppsqm = statistics.mean(comp_ppsqm)
            if target_ppsqm and target_ppsqm > avg_ppsqm * 1.05:
                arguments.append(
                    f"Price per m² (${target_ppsqm:,.0f}) exceeds the area average "
                    f"(${avg_ppsqm:,.0f}/m²)."
                )

        if target.get("year_built"):
            try:
                year = int(float(target["year_built"]))
                if year < 2000:
                    arguments.append(
                        f"Property built in {year} -- potential renovation costs to negotiate."
                    )
            except (TypeError, ValueError):
                pass

        if target.get("days_on_market"):
            try:
                dom = int(float(target["days_on_market"]))
                if dom > 60:
                    arguments.append(f"Listed for {dom} days -- seller may be motivated to close.")
            except (TypeError, ValueError):
                pass

        if not arguments:
            arguments.append(
                "Market data is limited; consider commissioning an independent appraisal."
            )

        # ------ Email template ------ #
        email_template = _build_email(
            tone=tone,
            city=city,
            ptype=ptype,
            rooms=rooms,
            asking_price=asking_price,
            opening_offer=opening_offer,
            arguments=arguments,
        )

        # ------ Assemble result ------ #
        price_band: Dict[str, Optional[float]] = {"lower": lower, "mid": mid, "upper": upper}
        if user_budget:
            price_band["user_budget"] = user_budget

        return {
            "property": {
                "id": target.get("id"),
                "city": city,
                "property_type": ptype,
                "rooms": rooms,
                "area_sqm": area,
                "asking_price": asking_price,
            },
            "price_band": price_band,
            "opening_offer": opening_offer,
            "arguments": arguments,
            "email_template": email_template,
            "disclaimer": LEGAL_DISCLAIMER.strip(),
        }

    # ------------------------------------------------------------------ #
    # LangChain interface
    # ------------------------------------------------------------------ #

    def _run(
        self,
        property_identifier: str,
        user_budget: Optional[float] = None,
        tone: str = "formal",
    ) -> str:
        """Synchronous execution."""
        try:
            target, comparables = self._fetch_property_and_comps(property_identifier)
            result = self.analyse(
                target=target,
                comparables=comparables,
                user_budget=user_budget,
                tone=tone,
            )
            return _format_result(result)
        except Exception as exc:
            return f"Negotiation analysis error: {exc}"

    async def _arun(
        self,
        property_identifier: str,
        user_budget: Optional[float] = None,
        tone: str = "formal",
    ) -> str:
        """Async execution."""
        return self._run(
            property_identifier=property_identifier,
            user_budget=user_budget,
            tone=tone,
        )

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _fetch_property_and_comps(
        self, identifier: str
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Retrieve the target property and comparable listings.

        Returns:
            Tuple of (target_metadata, list_of_comparable_metadata_dicts).
        """
        if self._vector_store is None:
            return {"id": identifier}, []

        # Try as ID first (short, no spaces)
        looks_like_id = " " not in identifier.strip() and len(identifier.strip()) <= 64
        target_md: Optional[Dict[str, Any]] = None

        if looks_like_id and hasattr(self._vector_store, "get_properties_by_ids"):
            docs = self._vector_store.get_properties_by_ids([identifier.strip()])
            if docs:
                target_md = docs[0].metadata or {}

        # Fallback: treat as search query
        if target_md is None and hasattr(self._vector_store, "search"):
            results = self._vector_store.search(identifier, k=10)
            if results:
                target_md = results[0][0].metadata or {}
                # The rest are comparables
                early_comps = [doc.metadata or {} for doc, _ in results[1:]]
                return target_md, early_comps

        if target_md is None:
            return {"id": identifier}, []

        # Fetch comparables by searching in the same city
        city = target_md.get("city", "")
        comp_mds: List[Dict[str, Any]] = []
        if city and hasattr(self._vector_store, "search"):
            comp_results = self._vector_store.search(
                f"{target_md.get('property_type', 'property')} in {city}", k=10
            )
            for doc, _ in comp_results:
                md = doc.metadata or {}
                # Exclude the target itself
                if md.get("id") != target_md.get("id"):
                    comp_mds.append(md)

        return target_md, comp_mds


# --------------------------------------------------------------------------- #
# Private helpers
# --------------------------------------------------------------------------- #


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_email(
    *,
    tone: str,
    city: str,
    ptype: str,
    rooms: Any,
    asking_price: Optional[float],
    opening_offer: Optional[float],
    arguments: List[str],
) -> str:
    """Generate an outreach email template based on tone."""
    rooms_txt = f"{rooms}-room " if rooms else ""
    prop_label = f"{rooms_txt}{ptype}".strip() or "property"

    if tone == "friendly":
        greeting = "Hi there,"
        closing = "Looking forward to hearing from you!\n\nBest regards"
    elif tone == "assertive":
        greeting = "Dear Seller,"
        closing = (
            "I trust you will give this offer fair consideration. "
            "I am ready to proceed swiftly upon agreement.\n\n"
            "Sincerely"
        )
    else:  # formal
        greeting = "Dear Sir or Madam,"
        closing = "Thank you for your time and consideration.\n\nKind regards"

    price_ref = f" (${asking_price:,.0f})" if asking_price else ""
    offer_ref = f" ${opening_offer:,.0f}" if opening_offer else " a competitive figure"

    lines = [
        f"{greeting}",
        "",
        f"I am writing to express my interest in the {prop_label} located in {city}{price_ref}.",
        "",
    ]

    if arguments:
        lines.append("Based on my research:")
        for arg in arguments[:4]:
            lines.append(f"  - {arg}")
        lines.append("")

    lines.append(
        f"I would like to propose an offer of{offer_ref} and am open to discussing "
        "the terms at your earliest convenience."
    )
    lines.append("")
    lines.append(closing)

    return "\n".join(lines)


def _format_result(result: Dict[str, Any]) -> str:
    """Render the analysis dict as a human-readable string for the agent."""
    sections: List[str] = []

    prop = result.get("property", {})
    sections.append(
        f"Negotiation Analysis for {prop.get('property_type', 'Property')}"
        f" in {prop.get('city', 'Unknown')}"
    )
    if prop.get("asking_price"):
        sections.append(f"Asking Price: ${prop['asking_price']:,.0f}")

    band = result.get("price_band", {})
    if any(band.get(k) for k in ("lower", "mid", "upper")):
        sections.append("")
        sections.append("Suggested Price Band:")
        if band.get("lower") is not None:
            sections.append(f"  Lower:  ${band['lower']:,.0f}")
        if band.get("mid") is not None:
            sections.append(f"  Mid:    ${band['mid']:,.0f}")
        if band.get("upper") is not None:
            sections.append(f"  Upper:  ${band['upper']:,.0f}")

    offer = result.get("opening_offer")
    if offer is not None:
        sections.append(f"\nRecommended Opening Offer: ${offer:,.0f}")

    args = result.get("arguments", [])
    if args:
        sections.append("\nKey Negotiation Arguments:")
        for a in args:
            sections.append(f"  - {a}")

    email = result.get("email_template")
    if email:
        sections.append("\nSuggested Outreach Message:\n")
        sections.append(email)

    disclaimer = result.get("disclaimer")
    if disclaimer:
        sections.append(disclaimer)

    return "\n".join(sections)
