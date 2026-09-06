"""
AI neighborhood one-liner tool.

Generates a short 2-3 sentence natural-language summary of a neighborhood
for a property detail page. Uses a single LLM call — no external data
sources required, which keeps the feature working in demo mode.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

from config.settings import settings
from models.provider_factory import ModelProviderFactory

logger = logging.getLogger(__name__)


class NeighborhoodSummaryInput(BaseModel):
    """Input for the neighborhood one-liner tool."""

    city: Optional[str] = Field(default=None, description="City name")
    neighborhood: Optional[str] = Field(
        default=None, description="Neighborhood or district name"
    )
    property_type: Optional[str] = Field(default=None, description="apartment, house, etc.")
    rooms: Optional[float] = Field(default=None, description="Number of rooms")
    area_sqm: Optional[float] = Field(default=None, description="Area in sqm")
    language: str = Field(default="en", description="Output language code (en, pl, etc.)")
    max_sentences: int = Field(default=3, ge=1, le=5)


_LANG_NAMES = {
    "en": "English",
    "pl": "Polish",
    "ru": "Russian",
    "de": "German",
    "es": "Spanish",
    "fr": "French",
    "it": "Italian",
    "pt": "Portuguese",
    "tr": "Turkish",
    "uk": "Ukrainian",
}


_NEIGHBORHOOD_INSTRUCTIONS = """You are a local real-estate expert. In {language},
write a {max_sentences}-sentence description of the neighborhood for a property
listing. Cover lifestyle, character, and accessibility. Avoid invented
statistics. If a piece of context is missing, make a hedged statement
("generally known for…", "often described as…"). Return only the prose,
no labels or bullet points.

City: {city}
Neighborhood: {neighborhood}
Property type: {property_type}
Size: {size_text}

Write the description now:"""


class NeighborhoodSummaryTool(BaseTool):
    """Tool that returns a 2-3 sentence AI summary of a neighborhood."""

    name: str = "neighborhood_summary"
    description: str = (
        "Generate a short AI summary of a neighborhood for a property. "
        "Input: city, neighborhood, property_type, rooms, area_sqm, language. "
        "Returns: 2-3 sentence plain-English description suitable for a "
        "property detail page."
    )
    args_schema: type[NeighborhoodSummaryInput] = NeighborhoodSummaryInput

    _llm: BaseChatModel | None = PrivateAttr(default=None)

    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        if llm is not None:
            self._llm = llm
        else:
            try:
                self._llm = ModelProviderFactory.create_model(
                    model_id=settings.default_model or "gpt-4o-mini",
                    provider_name=settings.default_provider,
                    temperature=0.6,
                    max_tokens=300,
                )
            except Exception as e:
                logger.warning(
                    "Failed to create LLM for neighborhood summary: %s", e
                )
                self._llm = None

    @staticmethod
    def _format_size(rooms: Optional[float], area_sqm: Optional[float]) -> str:
        bits = []
        if rooms is not None:
            try:
                bits.append(f"{float(rooms):g}-room")
            except (TypeError, ValueError):
                pass
        if area_sqm is not None:
            try:
                bits.append(f"{float(area_sqm):g} sqm")
            except (TypeError, ValueError):
                pass
        return ", ".join(bits) if bits else "unspecified size"

    @staticmethod
    def _postprocess(text: str, max_sentences: int) -> str:
        text = (text or "").strip()
        # Strip code fences FIRST (they often contain quotes inside)
        if text.startswith("```"):
            text = text.strip("`").strip()
            # Remove a leading "json" tag if present after fence
            if text.lower().startswith("json"):
                text = text[4:].lstrip()
        # Strip surrounding quotes the LLM sometimes adds
        if len(text) >= 2 and text.startswith('"') and text.endswith('"'):
            text = text[1:-1].strip()
        # Truncate to N sentences (best effort on '.', '!', '?')
        if max_sentences <= 0:
            return text
        kept: list[str] = []
        buf: list[str] = []
        for ch in text:
            buf.append(ch)
            if ch in ".!?" and len(kept) < max_sentences:
                kept.append("".join(buf).strip())
                buf = []
        if buf and len(kept) < max_sentences:
            tail = "".join(buf).strip()
            if tail:
                kept.append(tail)
        out = " ".join(s for s in kept if s)
        return out or text

    def summarize(self, args: Dict[str, Any]) -> str:
        """Compute the summary. Public for testability."""
        if self._llm is None:
            return self._fallback(args)
        language = (args.get("language") or "en").lower()
        language_name = _LANG_NAMES.get(language, "English")
        max_sentences = int(args.get("max_sentences") or 3)
        prompt = _NEIGHBORHOOD_INSTRUCTIONS.format(
            language=language_name,
            max_sentences=max_sentences,
            city=args.get("city") or "unknown",
            neighborhood=args.get("neighborhood") or "unknown",
            property_type=args.get("property_type") or "residential",
            size_text=self._format_size(args.get("rooms"), args.get("area_sqm")),
        )
        try:
            response = self._llm.invoke(prompt)
            raw = response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            logger.warning("Neighborhood summary LLM call failed: %s", e)
            return self._fallback(args)
        return self._postprocess(str(raw), max_sentences)

    @staticmethod
    def _fallback(args: Dict[str, Any]) -> str:
        city = args.get("city") or "the city"
        nbh = args.get("neighborhood") or "this area"
        return (
            f"{nbh} is a residential pocket of {city}. The area combines "
            f"everyday amenities with easy access to public transport, "
            f"making it a practical choice for most buyers."
        )

    def _run(
        self,
        city: Optional[str] = None,
        neighborhood: Optional[str] = None,
        property_type: Optional[str] = None,
        rooms: Optional[float] = None,
        area_sqm: Optional[float] = None,
        language: str = "en",
        max_sentences: int = 3,
        **_kwargs: Any,
    ) -> str:
        return self.summarize(
            {
                "city": city,
                "neighborhood": neighborhood,
                "property_type": property_type,
                "rooms": rooms,
                "area_sqm": area_sqm,
                "language": language,
                "max_sentences": max_sentences,
            }
        )

    async def _arun(
        self,
        city: Optional[str] = None,
        neighborhood: Optional[str] = None,
        property_type: Optional[str] = None,
        rooms: Optional[float] = None,
        area_sqm: Optional[float] = None,
        language: str = "en",
        max_sentences: int = 3,
        **_kwargs: Any,
    ) -> str:
        return self._run(
            city=city,
            neighborhood=neighborhood,
            property_type=property_type,
            rooms=rooms,
            area_sqm=area_sqm,
            language=language,
            max_sentences=max_sentences,
        )