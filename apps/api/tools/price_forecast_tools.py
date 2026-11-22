"""
AI Property Valuation with Multi-Year Price Forecast.

Provides a LangChain tool that estimates current market value and projects
future value at 1y/3y/5y horizons, using:
- Property features from the vector store
- Comparable sales (top-N similar listings)
- City/neighborhood median price-per-sqm
- The official register of notarial prices, when it holds the place
- LLM-based structured output with a confidence band

No external paid APIs are required; the LLM alone produces the estimate and
projection. This makes the feature work in demo mode out of the box. When the
register holds the place, the forecast stands on the prices people actually
paid — including the rate those prices moved at, which is measured rather than
assumed.
"""

from __future__ import annotations

import json
import logging
import statistics
from typing import Any, Callable, Dict, List, Optional, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

from agents.services.valuation import RegisterContext
from tools.llm_resolution import resolve_tool_llm

logger = logging.getLogger(__name__)

# The rate a forecast falls back to when nothing was measured. It is an
# assumption, and the result says so.
ASSUMED_ANNUAL_RATE = 0.03


# ---------------------------------------------------------------------------
# Input / output models
# ---------------------------------------------------------------------------


class PriceForecastInput(BaseModel):
    """Input for the price forecast tool.

    Either provide a property_id (resolved from the vector store) or pass
    free-form property_features for hypothetical scenarios.
    """

    property_id: Optional[str] = Field(
        default=None,
        description=(
            "Optional ID of an existing property in the vector store. "
            "If provided, features and comparables are loaded automatically."
        ),
    )
    property_features: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Free-form property features when property_id is not available. "
            "Expected keys: area_sqm, rooms, year_built, property_type, city, "
            "neighborhood, country, asking_price, latitude, longitude."
        ),
    )
    horizon_years: List[int] = Field(
        default_factory=lambda: [1, 3, 5],
        description="Forecast horizons in years (each must be in [1, 10]).",
    )


class ForecastPoint(BaseModel):
    """Single point in the forecast curve."""

    years_ahead: int = Field(..., ge=1, le=10)
    estimated_value: float = Field(..., ge=0)
    lower_bound: float = Field(..., ge=0)
    upper_bound: float = Field(..., ge=0)


class PriceForecastResult(BaseModel):
    """Structured output of the forecast tool."""

    current_estimate: float = Field(..., ge=0)
    currency: str = "EUR"
    horizon_years: List[int]
    forecast: List[ForecastPoint]
    confidence: float = Field(..., ge=0.0, le=1.0)
    drivers: List[str] = Field(default_factory=list)
    explanation: str
    comparables_used: int = 0
    median_price_per_sqm: Optional[float] = None
    neighborhood_median_price_per_sqm: Optional[float] = None
    disclaimer: str = (
        "AI estimate, not a formal appraisal. Forecasts are scenario-based "
        "and depend on market conditions that may change."
    )


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------


_FORECAST_INSTRUCTIONS = """You are a real estate valuation analyst. Produce a
strictly-formatted JSON object (no prose, no markdown) estimating current value
and a multi-year price forecast for the property described below.

Constraints:
- All numeric fields MUST be positive numbers in the listing currency.
- "current_estimate" is your best estimate of fair market value today.
- For each horizon in `horizon_years`, populate a forecast entry with
  estimated_value, lower_bound (-1 std dev), upper_bound (+1 std dev).
- "confidence" is 0..1 reflecting data quality (more comparables = higher).
- "drivers" is an array of up to 3 short strings naming the main value
  drivers (e.g. "below-median price per sqm", "new-build premium",
  "strong transit access").
- "explanation" is one short paragraph (max 60 words) summarising the
  estimate and forecast rationale for a non-expert reader.
- Do NOT include any text outside the JSON object.

Property features:
{features}

Comparable sales (top {n_comps} by similarity):
{comparables}

Market context:
{market_context}
"""


class PriceForecastTool(BaseTool):
    """Tool that estimates current value and projects future value 1-5 years out.

    Args schema is intentionally permissive; either property_id OR
    property_features must be provided by the caller.
    """

    name: str = "price_forecast"
    description: str = (
        "Estimate a property's current market value and forecast its value "
        "at 1y, 3y, and 5y horizons. Use when the user asks 'how much will "
        "this property be worth in N years' or 'is this a fair price'. "
        "Input: property_id OR free-form property_features. "
        "Returns: structured JSON with current_estimate, forecast points, "
        "confidence, drivers, and an explanation."
    )
    args_schema: type[PriceForecastInput] = PriceForecastInput

    _llm: BaseChatModel | None = PrivateAttr(default=None)
    _vector_store: Any = PrivateAttr(default=None)
    _register_reader: Optional[Callable[[str, str], Optional[RegisterContext]]] = PrivateAttr(
        default=None
    )

    def __init__(
        self,
        vector_store: Any = None,
        llm: Optional[BaseChatModel] = None,
        register_reader: Optional[Callable[[str, str], Optional[RegisterContext]]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        # The model comes from the application - the injected one, or the
        # mock model of a demo deployment. A tool that builds its own model
        # dies on a deployment without a provider key.
        self._llm = resolve_tool_llm(
            llm,
            task_type="price forecast",
            temperature=0.2,  # low temperature for numeric stability
            max_tokens=800,
        )
        self._vector_store = vector_store
        # The register is read through an injected reader so a test can answer
        # for it and a deployment without it simply forecasts without it.
        self._register_reader = register_reader

    # ---- public helpers used by tests and the router -----------------------

    @staticmethod
    def _coerce_features(args: Dict[str, Any]) -> Dict[str, Any]:
        """Coerce and validate the input payload into a normalized feature dict."""
        features = dict(args.get("property_features") or {})
        if args.get("property_id"):
            features.setdefault("id", args["property_id"])
        return features

    @staticmethod
    def _sanitize_horizon(years: List[int]) -> List[int]:
        """Filter horizons to valid range, deduplicate, and sort."""
        if not years:
            return [1, 3, 5]
        seen: set[int] = set()
        out: List[int] = []
        for y in years:
            try:
                iy = int(y)
            except (TypeError, ValueError):
                continue
            if 1 <= iy <= 10 and iy not in seen:
                seen.add(iy)
                out.append(iy)
        return sorted(out) if out else [1, 3, 5]

    @staticmethod
    def _extract_comparables(
        vector_store: Any, features: Dict[str, Any], k: int = 5
    ) -> List[Dict[str, Any]]:
        """Pull top-k similar properties from the vector store, best effort."""
        if vector_store is None:
            return []
        try:
            query_text = " ".join(
                str(v)
                for v in (
                    features.get("city"),
                    features.get("neighborhood"),
                    features.get("property_type"),
                    features.get("rooms"),
                    features.get("area_sqm"),
                )
                if v not in (None, "")
            )
            if not query_text:
                return []
            results = vector_store.search(query_text, k=k)
        except Exception as e:
            logger.warning("Comparable lookup failed: %s", e)
            return []
        comps: List[Dict[str, Any]] = []
        for entry in results or []:
            try:
                doc, _score = entry
            except (TypeError, ValueError):
                continue
            md = getattr(doc, "metadata", None) or {}
            comp = {
                "id": md.get("id"),
                "city": md.get("city"),
                "neighborhood": md.get("neighborhood"),
                "price": md.get("price"),
                "price_per_sqm": md.get("price_per_sqm"),
                "area_sqm": md.get("area_sqm"),
                "rooms": md.get("rooms"),
                "year_built": md.get("year_built"),
                "property_type": md.get("property_type"),
            }
            comps.append({k: v for k, v in comp.items() if v is not None})
        return comps

    @staticmethod
    def _median_price_per_sqm(comparables: List[Dict[str, Any]]) -> Optional[float]:
        values = [
            float(c["price_per_sqm"]) for c in comparables if c.get("price_per_sqm") is not None
        ]
        if not values:
            return None
        return float(statistics.median(values))

    @staticmethod
    def _neighborhood_median_price_per_sqm(
        comparables: List[Dict[str, Any]], neighborhood: Optional[str]
    ) -> Optional[float]:
        if not neighborhood:
            return None
        values = [
            float(c["price_per_sqm"])
            for c in comparables
            if c.get("price_per_sqm") is not None
            and isinstance(c.get("neighborhood"), str)
            and c["neighborhood"].lower() == neighborhood.lower()
        ]
        if not values:
            return None
        return float(statistics.median(values))

    @staticmethod
    def _build_market_context(
        features: Dict[str, Any],
        comparables: List[Dict[str, Any]],
        median_ppsm: Optional[float],
        nbh_median_ppsm: Optional[float],
        register: Optional[RegisterContext] = None,
    ) -> str:
        parts: List[str] = []
        if median_ppsm is not None:
            parts.append(f"City median price-per-sqm: {median_ppsm:.0f}")
        if nbh_median_ppsm is not None and nbh_median_ppsm != median_ppsm:
            parts.append(f"Neighborhood median price-per-sqm: {nbh_median_ppsm:.0f}")
        if features.get("price") is not None:
            try:
                parts.append(f"Listing asking price: {float(features['price']):.0f}")
            except (TypeError, ValueError):
                pass
        if comparables:
            parts.append(f"Comparables used: {len(comparables)}")
        if register is not None and register.has_data:
            if register.median_price_per_sqm is not None:
                parts.append(
                    f"Official register median price-per-sqm ({register.comparison_area}): "
                    f"{register.median_price_per_sqm:.0f} "
                    f"({register.sample_size} registered sales)"
                )
            if register.trend is not None:
                parts.append(
                    f"Registered price change: {register.trend.annual_rate * 100:+.1f}% a year "
                    f"({register.trend.sample_size} sales between "
                    f"{register.trend.period_start.isoformat()} and "
                    f"{register.trend.period_end.isoformat()})"
                )
        return "\n".join(parts) if parts else "No additional market context."

    @staticmethod
    def _parse_llm_json(raw: str) -> Dict[str, Any]:
        """Tolerantly parse the LLM JSON output."""
        if not raw:
            return {}
        text = raw.strip()
        # strip code fences if present
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            return cast(Dict[str, Any], json.loads(text))
        except json.JSONDecodeError:
            # try to find a JSON object within the text
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                try:
                    return cast(Dict[str, Any], json.loads(text[start : end + 1]))
                except json.JSONDecodeError:
                    return {}
        return {}

    def _generate(
        self,
        features: Dict[str, Any],
        comparables: List[Dict[str, Any]],
        horizons: List[int],
        register: Optional[RegisterContext] = None,
    ) -> Dict[str, Any]:
        if self._llm is None:
            return {}
        prompt = _FORECAST_INSTRUCTIONS.format(
            features=json.dumps(features, default=str, indent=2),
            n_comps=len(comparables),
            comparables=json.dumps(comparables, default=str, indent=2),
            market_context=self._build_market_context(
                features,
                comparables,
                self._median_price_per_sqm(comparables),
                self._neighborhood_median_price_per_sqm(comparables, features.get("neighborhood")),
                register,
            ),
        )
        try:
            response = self._llm.invoke(prompt)
            raw = response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            logger.error("LLM invoke failed in price forecast: %s", e)
            return {}
        parsed = self._parse_llm_json(str(raw))
        # Make sure we only keep entries for horizons the caller asked for
        allowed = set(horizons)
        pruned: List[Dict[str, Any]] = []
        for entry in parsed.get("forecast") or []:
            try:
                yrs = int(entry.get("years_ahead"))
            except (TypeError, ValueError):
                continue
            if yrs in allowed:
                pruned.append(entry)
        parsed["forecast"] = pruned
        return parsed

    @staticmethod
    def _build_fallback(
        features: Dict[str, Any],
        horizons: List[int],
        median_ppsm: Optional[float],
        nbh_median_ppsm: Optional[float],
        n_comps: int,
        register: Optional[RegisterContext] = None,
    ) -> PriceForecastResult:
        """The forecast when the model could not answer.

        The degradation is to the transaction data, not to a constant: when the
        official register holds the place, the estimate is anchored on the
        median price per square metre of the sales that happened there, and
        the projection follows the rate those sales actually moved at. Only
        when nothing was measured does the flat assumption remain — and then
        the result says that the rate is an assumption.
        """
        register_median = register.median_price_per_sqm if register else None
        trend = register.trend if register else None
        anchor = register_median or nbh_median_ppsm or median_ppsm
        try:
            area = float(features["area_sqm"]) if features.get("area_sqm") else None
        except (TypeError, ValueError):
            area = None
        try:
            asking = float(features["price"]) if features.get("price") else None
        except (TypeError, ValueError):
            asking = None

        if anchor is not None and area is not None:
            current = anchor * area
        elif asking is not None:
            current = asking
        else:
            current = 0.0

        rate = trend.annual_rate if trend else ASSUMED_ANNUAL_RATE
        forecast: List[ForecastPoint] = []
        for y in horizons:
            mid = current * ((1 + rate) ** y)
            forecast.append(
                ForecastPoint(
                    years_ahead=y,
                    estimated_value=round(mid, 0),
                    lower_bound=round(mid * 0.92, 0),
                    upper_bound=round(mid * 1.08, 0),
                )
            )

        if trend is not None:
            confidence = 0.6 if trend.sample_size >= 20 else 0.5
            drivers = [
                f"measured appreciation from {trend.sample_size} registered sale(s)",
            ]
            if anchor:
                drivers.append(f"median {anchor:.0f} PLN/m² from the official register")
            explanation = (
                f"Projected from the official register: {trend.describe()} "
                f"The estimate is the median price per square metre of the sales it "
                f"stands on, multiplied by the area."
            )
        elif register is not None and register.has_data:
            confidence = 0.35 if n_comps >= 3 else 0.25
            drivers = ["official register prices — the yearly change could not be measured"]
            explanation = (
                "Estimate from the official register of notarial prices. The yearly "
                "change could not be measured from the sales available, so the "
                f"projection uses a flat {ASSUMED_ANNUAL_RATE * 100:.0f}% per year "
                "assumption."
            )
        else:
            confidence = 0.35 if n_comps >= 3 else 0.2
            drivers = ["fallback estimate — LLM unavailable"]
            explanation = (
                "Fallback estimate based on median price-per-sqm and a "
                f"flat {ASSUMED_ANNUAL_RATE * 100:.0f}% per year appreciation assumption."
            )

        # The register records prices in złoty, so an estimate taken from it
        # is in złoty whatever the catalogue said.
        currency = str(features.get("currency") or ("PLN" if register_median else "EUR"))

        return PriceForecastResult(
            current_estimate=round(current, 0),
            currency=currency,
            horizon_years=horizons,
            forecast=forecast,
            confidence=confidence,
            drivers=drivers,
            explanation=explanation,
            comparables_used=(register.sample_size if register and register.has_data else n_comps),
            median_price_per_sqm=register_median or median_ppsm,
            neighborhood_median_price_per_sqm=nbh_median_ppsm,
        )

    def _register_context(self, features: Dict[str, Any]) -> Optional[RegisterContext]:
        """What the official register holds for the place being forecast.

        The register is a source of truth, not a decoration: when it holds the
        place, the forecast is anchored on it and its measured rate.
        """
        if self._register_reader is None:
            return None
        city = str(features.get("city") or "").strip()
        if not city:
            return None
        street = str(features.get("street") or "").strip()
        try:
            return self._register_reader(city, street)
        except Exception as exc:  # pragma: no cover - the store may be absent
            logger.warning("The official price register could not be read: %s", exc)
            return None

    def forecast(self, args: Dict[str, Any]) -> PriceForecastResult:
        """Compute a forecast for the given input. Public for testability."""
        features = self._coerce_features(args)
        horizons = self._sanitize_horizon(args.get("horizon_years") or [1, 3, 5])
        comparables = self._extract_comparables(self._vector_store, features)
        median_ppsm = self._median_price_per_sqm(comparables)
        nbh_median_ppsm = self._neighborhood_median_price_per_sqm(
            comparables, features.get("neighborhood")
        )
        register = self._register_context(features)
        parsed = self._generate(features, comparables, horizons, register)
        if parsed and parsed.get("current_estimate") is not None:
            forecast_points: List[ForecastPoint] = []
            for entry in parsed.get("forecast") or []:
                try:
                    forecast_points.append(
                        ForecastPoint(
                            years_ahead=int(entry["years_ahead"]),
                            estimated_value=float(entry["estimated_value"]),
                            lower_bound=float(entry.get("lower_bound", entry["estimated_value"])),
                            upper_bound=float(entry.get("upper_bound", entry["estimated_value"])),
                        )
                    )
                except (KeyError, TypeError, ValueError):
                    continue
            try:
                confidence = float(parsed.get("confidence", 0.5))
            except (TypeError, ValueError):
                confidence = 0.5
            try:
                current = float(parsed["current_estimate"])
            except (TypeError, ValueError):
                return self._build_fallback(
                    features, horizons, median_ppsm, nbh_median_ppsm, len(comparables), register
                )
            drivers = [str(d) for d in (parsed.get("drivers") or [])][:3]
            explanation = str(parsed.get("explanation") or "").strip()
            if not forecast_points:
                # The model returned no curve: project the estimate with the
                # rate that was measured, or with the assumption if none was.
                rate = register.trend.annual_rate if register and register.trend else None
                if rate is None:
                    rate = ASSUMED_ANNUAL_RATE
                for y in horizons:
                    forecast_points.append(
                        ForecastPoint(
                            years_ahead=y,
                            estimated_value=round(current * ((1 + rate) ** y), 0),
                            lower_bound=round(current * ((1 + rate * 0.5) ** y), 0),
                            upper_bound=round(current * ((1 + rate * 1.5) ** y), 0),
                        )
                    )
            return PriceForecastResult(
                current_estimate=round(current, 0),
                currency=str(
                    features.get("currency")
                    or ("PLN" if register and register.median_price_per_sqm else "EUR")
                ),
                horizon_years=horizons,
                forecast=forecast_points,
                confidence=max(0.0, min(1.0, confidence)),
                drivers=drivers,
                explanation=explanation or "Estimate based on property features and comparables.",
                comparables_used=(
                    register.sample_size if register and register.has_data else len(comparables)
                ),
                median_price_per_sqm=(
                    register.median_price_per_sqm
                    if register and register.median_price_per_sqm
                    else median_ppsm
                ),
                neighborhood_median_price_per_sqm=nbh_median_ppsm,
            )
        # No LLM or no parseable output — use deterministic fallback
        return self._build_fallback(
            features, horizons, median_ppsm, nbh_median_ppsm, len(comparables), register
        )

    # ---- BaseTool overrides -----------------------------------------------

    def _run(
        self,
        property_id: Optional[str] = None,
        property_features: Optional[Dict[str, Any]] = None,
        horizon_years: Optional[List[int]] = None,
        **_kwargs: Any,
    ) -> str:
        result = self.forecast(
            {
                "property_id": property_id,
                "property_features": property_features,
                "horizon_years": horizon_years or [1, 3, 5],
            }
        )
        return result.model_dump_json()

    async def _arun(
        self,
        property_id: Optional[str] = None,
        property_features: Optional[Dict[str, Any]] = None,
        horizon_years: Optional[List[int]] = None,
        **_kwargs: Any,
    ) -> str:
        return self._run(
            property_id=property_id,
            property_features=property_features,
            horizon_years=horizon_years,
        )
