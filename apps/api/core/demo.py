"""Demo mode utilities: mock LLM and sample data for no-auth staging."""

from __future__ import annotations

import logging
import random
from typing import Any, List, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

logger = logging.getLogger(__name__)

DEMO_RESPONSES: list[str] = [
    (
        "I found several properties matching your criteria. "
        "Here are some highlights:\n\n"
        "1. **Modern Apartment in Krakow City Center** — 65 m², 2 bedrooms, "
        "650,000 PLN\n"
        "2. **Renovated Flat in Kazimierz** — 52 m², 1 bedroom, "
        "520,000 PLN\n"
        "3. **New Development in Podgórze** — 78 m², 3 bedrooms, "
        "780,000 PLN\n\n"
        "Would you like more details on any of these properties?"
    ),
    (
        "Based on current market analysis for Warsaw:\n\n"
        "- **Average price/m²**: 12,500 PLN (Mokotów district)\n"
        "- **Price trend**: +3.2% over last quarter\n"
        "- **Popular areas**: Mokotów, Żoliborz, Ursynów\n\n"
        "The market is currently favorable for buyers with a slight "
        "increase in inventory. Shall I search for specific listings?"
    ),
    (
        "Here's a comparison of the neighborhoods you asked about:\n\n"
        "| Feature | Krakow | Warsaw | Gdansk |\n"
        "|---------|--------|--------|--------|\n"
        "| Avg price/m² | 10,800 | 12,500 | 9,200 |\n"
        "| Public transit | Excellent | Excellent | Good |\n"
        "| Green areas | High | Medium | High |\n"
        "| Investment potential | High | High | Medium |\n\n"
        "Would you like me to dive deeper into any specific city?"
    ),
    (
        "For mortgage estimation on a 500,000 PLN property:\n\n"
        "- **Down payment (20%)**: 100,000 PLN\n"
        "- **Loan amount**: 400,000 PLN\n"
        "- **Monthly payment (25yr, 7.5%)**: ~2,955 PLN\n"
        "- **Total interest**: ~486,500 PLN\n\n"
        "Note: This is an estimate. Actual rates vary by bank and your "
        "credit profile. Want me to compare different loan terms?"
    ),
]


class MockLLM(BaseChatModel):
    """LangChain-compatible chat model that returns pre-written demo responses.

    Used when DEMO_LLM_MODE=true to avoid calling real LLM APIs on staging.
    DEMO_MODE is only the umbrella fallback for the demo flags, so a
    deployment that sets DEMO_LLM_MODE=false answers with a real model
    even while DEMO_MODE is on.
    """

    response_selector: str = "random"  # random | sequential
    _call_count: int = 0

    @property
    def _llm_type(self) -> str:
        return "demo-mock"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        if self.response_selector == "sequential":
            idx = self._call_count % len(DEMO_RESPONSES)
            self._call_count += 1
        else:
            idx = random.randint(0, len(DEMO_RESPONSES) - 1)

        text = DEMO_RESPONSES[idx]
        message = AIMessage(content=text)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"model": "demo-mock", "response_selector": self.response_selector}


def get_demo_llm() -> MockLLM:
    """Create a MockLLM instance for demo mode."""
    logger.info("Demo mode active — using MockLLM (no real API calls)")
    return MockLLM()
