"""Unit tests for the v5.1 NeighborhoodSummaryTool.

LLM is always mocked so tests are deterministic and provider-free.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from tools.neighborhood_summary import NeighborhoodSummaryTool


def _llm_returning(text: str) -> MagicMock:
    llm = MagicMock()
    response = MagicMock()
    response.content = text
    llm.invoke.return_value = response
    return llm


def test_format_size_combines_rooms_and_area():
    text = NeighborhoodSummaryTool._format_size(3, 80)
    assert "3-room" in text
    assert "80 sqm" in text


def test_format_size_handles_missing_values():
    assert NeighborhoodSummaryTool._format_size(None, 50) == "50 sqm"
    assert NeighborhoodSummaryTool._format_size(2, None) == "2-room"
    assert NeighborhoodSummaryTool._format_size(None, None) == "unspecified size"


def test_postprocess_truncates_to_max_sentences():
    text = "First sentence. Second sentence. Third sentence. Fourth sentence."
    out = NeighborhoodSummaryTool._postprocess(text, max_sentences=2)
    assert out.count(".") == 2


def test_postprocess_strips_quotes_and_fences():
    text = '```"Hello there. Another line."```'
    out = NeighborhoodSummaryTool._postprocess(text, max_sentences=3)
    assert "Hello there." in out
    assert "```" not in out
    assert not out.startswith('"')


def test_summarize_returns_llm_output_truncated():
    llm = _llm_returning(
        "It's a quiet pocket. Loved by young families. Close to the metro. "
        "Has a big park too."
    )
    tool = NeighborhoodSummaryTool()
    tool._llm = llm  # type: ignore[assignment]
    out = tool.summarize(
        {
            "city": "Madrid",
            "neighborhood": "Salamanca",
            "property_type": "apartment",
            "rooms": 3,
            "area_sqm": 90,
            "language": "en",
            "max_sentences": 3,
        }
    )
    assert out.count(".") == 3
    assert "Salamanca" not in out  # LLM mocked, doesn't follow prompt


def test_summarize_falls_back_when_llm_missing():
    tool = NeighborhoodSummaryTool()
    tool._llm = None  # type: ignore[assignment]
    out = tool.summarize(
        {"city": "Warsaw", "neighborhood": "Mokotow", "language": "en"}
    )
    assert "Mokotow" in out
    assert "Warsaw" in out


def test_summarize_handles_llm_exception_with_fallback():
    llm = MagicMock()
    llm.invoke.side_effect = RuntimeError("provider down")
    tool = NeighborhoodSummaryTool()
    tool._llm = llm  # type: ignore[assignment]
    out = tool.summarize(
        {"city": "Krakow", "neighborhood": "Kazimierz", "language": "en"}
    )
    assert "Kazimierz" in out
    assert "Krakow" in out


def test_tool_metadata_and_run_format():
    tool = NeighborhoodSummaryTool()
    assert tool.name == "neighborhood_summary"
    out = tool._run(city="Warsaw", neighborhood="Wola", language="en", max_sentences=2)
    assert isinstance(out, str)
    assert len(out) > 0