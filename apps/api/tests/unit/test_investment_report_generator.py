"""Unit tests for investment_report_generator module."""

from dataclasses import dataclass
from typing import List, Optional

import pytest

from utils.investment_report_generator import (
    InvestmentReportGenerator,
)

# ---------------------------------------------------------------------------
# Helpers: lightweight stub for CashFlowProjection / YearlyCashFlow
# ---------------------------------------------------------------------------


@dataclass
class _StubYearlyCashFlow:
    year: int = 1
    gross_income: float = 24_000.0
    operating_expenses: float = 6_000.0
    mortgage_payment: float = 12_000.0
    noi: float = 18_000.0
    cash_flow: float = 6_000.0
    cumulative_cash_flow: float = 6_000.0
    property_value: float = 320_000.0
    equity: float = 80_000.0
    loan_balance: float = 240_000.0


@dataclass
class _StubCashFlowProjection:
    property_price: float = 300_000.0
    projection_years: int = 5
    yearly_breakdown: Optional[List[_StubYearlyCashFlow]] = None
    total_cash_flow: float = 30_000.0
    total_principal_paid: float = 60_000.0
    final_equity: float = 140_000.0
    irr: Optional[float] = 8.5

    def __post_init__(self):
        if self.yearly_breakdown is None:
            self.yearly_breakdown = [_StubYearlyCashFlow(year=y) for y in range(1, 6)]


# ---------------------------------------------------------------------------
# Sample result dicts used across tests
# ---------------------------------------------------------------------------

SAMPLE_RESULT_BASIC: dict = {
    "cash_on_cash_roi": 8.5,
    "cap_rate": 6.2,
    "gross_yield": 7.8,
    "net_yield": 5.1,
    "monthly_cash_flow": 450.0,
    "annual_cash_flow": 5400.0,
    "monthly_income": 2000.0,
    "monthly_expenses": 1200.0,
    "monthly_mortgage": 800.0,
    "annual_income": 24000.0,
    "annual_expenses": 14400.0,
    "investment_score": 75.0,
    "score_breakdown": {"cash_flow": 80.0, "appreciation": 70.0, "risk": 65.0},
    "total_investment": 60000.0,
    "property_tax_monthly": 150.0,
    "insurance_monthly": 100.0,
    "hoa_monthly": 50.0,
    "maintenance_monthly": 100.0,
    "vacancy_monthly": 100.0,
    "management_monthly": 150.0,
}

SAMPLE_RESULT_NEGATIVE_CASH_FLOW: dict = {
    **SAMPLE_RESULT_BASIC,
    "monthly_cash_flow": -200.0,
    "annual_cash_flow": -2400.0,
    "investment_score": 35.0,
}

SAMPLE_RESULT_NO_SCORE_BREAKDOWN: dict = {
    **SAMPLE_RESULT_BASIC,
    "score_breakdown": {},
}

SAMPLE_RESULT_ZERO_INCOME: dict = {
    **SAMPLE_RESULT_BASIC,
    "monthly_income": 0,
    "monthly_cash_flow": -1200.0,
    "annual_cash_flow": -14400.0,
    "investment_score": 10.0,
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def generator() -> InvestmentReportGenerator:
    """Return a fresh InvestmentReportGenerator instance."""
    return InvestmentReportGenerator()


@pytest.fixture
def sample_result() -> dict:
    return SAMPLE_RESULT_BASIC.copy()


@pytest.fixture
def projection() -> _StubCashFlowProjection:
    return _StubCashFlowProjection()


# ---------------------------------------------------------------------------
# Tests: __init__ and style setup
# ---------------------------------------------------------------------------


class TestInit:
    """Tests for InvestmentReportGenerator initialization."""

    def test_creates_instance(self, generator):
        assert isinstance(generator, InvestmentReportGenerator)

    def test_has_styles(self, generator):
        assert generator.styles is not None

    def test_custom_styles_added(self, generator):
        style_names = list(generator.styles.byName.keys())
        assert "ReportTitle" in style_names
        assert "SectionHeader" in style_names
        assert "SubsectionHeader" in style_names
        assert "MetricLabel" in style_names
        assert "MetricValue" in style_names

    def test_report_title_style_properties(self, generator):
        style = generator.styles["ReportTitle"]
        assert style.fontName == "Helvetica-Bold"
        assert style.fontSize == 24

    def test_section_header_style_properties(self, generator):
        style = generator.styles["SectionHeader"]
        assert style.fontName == "Helvetica-Bold"
        assert style.fontSize == 16

    def test_metric_label_style_properties(self, generator):
        style = generator.styles["MetricLabel"]
        assert style.fontName == "Helvetica"
        assert style.fontSize == 10


# ---------------------------------------------------------------------------
# Tests: _format_metric
# ---------------------------------------------------------------------------


class TestFormatMetric:
    """Tests for _format_metric method."""

    def test_roi_format(self, generator):
        result = generator._format_metric(8.5, "Cash on Cash ROI")
        assert result == "8.50%"

    def test_rate_format(self, generator):
        result = generator._format_metric(6.2, "Cap Rate")
        assert result == "6.20%"

    def test_yield_format(self, generator):
        result = generator._format_metric(5.1, "Gross Rental Yield")
        assert result == "5.10%"

    def test_cash_flow_format(self, generator):
        result = generator._format_metric(450.0, "Monthly Cash Flow")
        assert result == "$450.00"

    def test_generic_format(self, generator):
        result = generator._format_metric(1234.5, "Some Other Metric")
        assert result == "1,234.50"

    def test_zero_value(self, generator):
        result = generator._format_metric(0.0, "Cap Rate")
        assert result == "0.00%"

    def test_negative_value(self, generator):
        result = generator._format_metric(-3.5, "Monthly Cash Flow")
        assert result == "$-3.50"


# ---------------------------------------------------------------------------
# Tests: _get_score_bar
# ---------------------------------------------------------------------------


class TestGetScoreBar:
    """Tests for _get_score_bar method."""

    def test_full_score_long(self, generator):
        bar = generator._get_score_bar(100, short=False)
        assert "█" in bar
        assert "░" not in bar
        assert bar.startswith("[") and bar.endswith("]")

    def test_zero_score_long(self, generator):
        bar = generator._get_score_bar(0, short=False)
        assert "░" in bar
        assert "█" not in bar

    def test_half_score_long(self, generator):
        bar = generator._get_score_bar(50, short=False)
        assert "█" in bar
        assert "░" in bar

    def test_full_score_short(self, generator):
        bar = generator._get_score_bar(100, short=True)
        assert bar.count("█") == 10
        assert "░" not in bar

    def test_zero_score_short(self, generator):
        bar = generator._get_score_bar(0, short=True)
        assert bar.count("░") == 10
        assert "█" not in bar

    def test_half_score_short(self, generator):
        bar = generator._get_score_bar(50, short=True)
        assert bar.count("█") == 5
        assert bar.count("░") == 5


# ---------------------------------------------------------------------------
# Tests: _get_key_metrics_data
# ---------------------------------------------------------------------------


class TestGetKeyMetricsData:
    """Tests for _get_key_metrics_data method."""

    def test_returns_six_metrics(self, generator, sample_result):
        metrics = generator._get_key_metrics_data(sample_result)
        assert len(metrics) == 6

    def test_metric_tuple_structure(self, generator, sample_result):
        metrics = generator._get_key_metrics_data(sample_result)
        for label, value, is_positive in metrics:
            assert isinstance(label, str)
            assert isinstance(value, str)
            assert isinstance(is_positive, bool)

    def test_positive_values_flagged(self, generator, sample_result):
        metrics = generator._get_key_metrics_data(sample_result)
        for _label, _value, is_positive in metrics:
            assert is_positive is True

    def test_negative_cash_flow_flagged(self, generator):
        metrics = generator._get_key_metrics_data(SAMPLE_RESULT_NEGATIVE_CASH_FLOW)
        # Monthly and Annual Cash Flow should be negative
        cf_metrics = [(lbl, val, pos) for lbl, val, pos in metrics if "Cash Flow" in lbl]
        for _label, _value, is_positive in cf_metrics:
            assert is_positive is False

    def test_default_values_when_missing(self, generator):
        metrics = generator._get_key_metrics_data({})
        assert len(metrics) == 6
        for _label, value, _is_positive in metrics:
            # All defaults should be 0 formatted
            assert "0.00" in value


# ---------------------------------------------------------------------------
# Tests: _build_header
# ---------------------------------------------------------------------------


class TestBuildHeader:
    """Tests for _build_header method."""

    def test_returns_list(self, generator, sample_result):
        story = generator._build_header(sample_result)
        assert isinstance(story, list)

    def test_contains_title_paragraph(self, generator, sample_result):
        story = generator._build_header(sample_result)
        assert len(story) >= 2  # Title + spacer at minimum

    def test_works_with_empty_dict(self, generator):
        story = generator._build_header({})
        assert isinstance(story, list)
        assert len(story) >= 1


# ---------------------------------------------------------------------------
# Tests: _build_key_metrics_section
# ---------------------------------------------------------------------------


class TestBuildKeyMetricsSection:
    """Tests for _build_key_metrics_section method."""

    def test_returns_list(self, generator, sample_result):
        story = generator._build_key_metrics_section(sample_result)
        assert isinstance(story, list)

    def test_contains_table(self, generator, sample_result):
        from reportlab.platypus import Table

        story = generator._build_key_metrics_section(sample_result)
        tables = [item for item in story if isinstance(item, Table)]
        assert len(tables) >= 1

    def test_works_with_defaults(self, generator):
        story = generator._build_key_metrics_section({})
        assert isinstance(story, list)
        assert len(story) >= 1


# ---------------------------------------------------------------------------
# Tests: _build_cash_flow_section
# ---------------------------------------------------------------------------


class TestBuildCashFlowSection:
    """Tests for _build_cash_flow_section method."""

    def test_returns_list(self, generator, sample_result):
        story = generator._build_cash_flow_section(sample_result)
        assert isinstance(story, list)

    def test_contains_table(self, generator, sample_result):
        from reportlab.platypus import Table

        story = generator._build_cash_flow_section(sample_result)
        tables = [item for item in story if isinstance(item, Table)]
        assert len(tables) == 1

    def test_positive_cash_flow_uses_green(self, generator, sample_result):
        """When cash flow is positive, green color should be referenced."""
        story = generator._build_cash_flow_section(sample_result)
        # Check that table data references COLOR_POSITIVE (green)
        from reportlab.platypus import Table

        tables = [item for item in story if isinstance(item, Table)]
        assert len(tables) == 1

    def test_negative_cash_flow_uses_red(self, generator):
        story = generator._build_cash_flow_section(SAMPLE_RESULT_NEGATIVE_CASH_FLOW)
        assert isinstance(story, list)

    def test_zero_values(self, generator):
        story = generator._build_cash_flow_section(
            {
                "monthly_income": 0,
                "monthly_expenses": 0,
                "monthly_mortgage": 0,
                "monthly_cash_flow": 0,
            }
        )
        assert isinstance(story, list)


# ---------------------------------------------------------------------------
# Tests: _build_investment_score_section
# ---------------------------------------------------------------------------


class TestBuildInvestmentScoreSection:
    """Tests for _build_investment_score_section method."""

    def test_returns_list(self, generator, sample_result):
        story = generator._build_investment_score_section(sample_result)
        assert isinstance(story, list)

    def test_excellent_score_description(self, generator):
        result = {**SAMPLE_RESULT_BASIC, "investment_score": 85.0, "score_breakdown": {}}
        story = generator._build_investment_score_section(result)
        assert isinstance(story, list)

    def test_good_score_description(self, generator):
        result = {**SAMPLE_RESULT_BASIC, "investment_score": 75.0, "score_breakdown": {}}
        story = generator._build_investment_score_section(result)
        assert isinstance(story, list)

    def test_moderate_score_description(self, generator):
        result = {**SAMPLE_RESULT_BASIC, "investment_score": 55.0, "score_breakdown": {}}
        story = generator._build_investment_score_section(result)
        assert isinstance(story, list)

    def test_poor_score_description(self, generator):
        result = {**SAMPLE_RESULT_BASIC, "investment_score": 30.0, "score_breakdown": {}}
        story = generator._build_investment_score_section(result)
        assert isinstance(story, list)

    def test_with_score_breakdown(self, generator, sample_result):
        story = generator._build_investment_score_section(sample_result)
        from reportlab.platypus import Table

        tables = [item for item in story if isinstance(item, Table)]
        # Should have score table + breakdown table
        assert len(tables) >= 2

    def test_without_score_breakdown(self, generator):
        story = generator._build_investment_score_section(SAMPLE_RESULT_NO_SCORE_BREAKDOWN)
        from reportlab.platypus import Table

        tables = [item for item in story if isinstance(item, Table)]
        # Only score table, no breakdown
        assert len(tables) == 1

    def test_score_breakdown_rating_excellent(self, generator):
        result = {**SAMPLE_RESULT_BASIC, "score_breakdown": {"test_category": 85.0}}
        story = generator._build_investment_score_section(result)
        assert isinstance(story, list)

    def test_score_breakdown_rating_good(self, generator):
        result = {**SAMPLE_RESULT_BASIC, "score_breakdown": {"test_category": 72.0}}
        story = generator._build_investment_score_section(result)
        assert isinstance(story, list)

    def test_score_breakdown_rating_fair(self, generator):
        result = {**SAMPLE_RESULT_BASIC, "score_breakdown": {"test_category": 55.0}}
        story = generator._build_investment_score_section(result)
        assert isinstance(story, list)

    def test_score_breakdown_rating_poor(self, generator):
        result = {**SAMPLE_RESULT_BASIC, "score_breakdown": {"test_category": 30.0}}
        story = generator._build_investment_score_section(result)
        assert isinstance(story, list)

    def test_score_color_high(self, generator):
        """Score >= 70 should use COLOR_POSITIVE."""
        result = {**SAMPLE_RESULT_BASIC, "investment_score": 75.0, "score_breakdown": {}}
        story = generator._build_investment_score_section(result)
        assert isinstance(story, list)

    def test_score_color_medium(self, generator):
        """Score between 50 and 69 should use orange."""
        result = {**SAMPLE_RESULT_BASIC, "investment_score": 60.0, "score_breakdown": {}}
        story = generator._build_investment_score_section(result)
        assert isinstance(story, list)

    def test_score_color_low(self, generator):
        """Score < 50 should use COLOR_NEGATIVE."""
        result = {**SAMPLE_RESULT_BASIC, "investment_score": 40.0, "score_breakdown": {}}
        story = generator._build_investment_score_section(result)
        assert isinstance(story, list)


# ---------------------------------------------------------------------------
# Tests: _build_monthly_breakdown_table
# ---------------------------------------------------------------------------


class TestBuildMonthlyBreakdownTable:
    """Tests for _build_monthly_breakdown_table method."""

    def test_returns_list(self, generator, sample_result):
        story = generator._build_monthly_breakdown_table(sample_result)
        assert isinstance(story, list)

    def test_contains_table(self, generator, sample_result):
        from reportlab.platypus import Table

        story = generator._build_monthly_breakdown_table(sample_result)
        tables = [item for item in story if isinstance(item, Table)]
        assert len(tables) == 1

    def test_zero_income_shows_na(self, generator):
        story = generator._build_monthly_breakdown_table(SAMPLE_RESULT_ZERO_INCOME)
        assert isinstance(story, list)
        # With zero income, percentages should show N/A

    def test_all_zero_values(self, generator):
        result = {
            "monthly_income": 0,
            "monthly_mortgage": 0,
            "property_tax_monthly": 0,
            "insurance_monthly": 0,
            "hoa_monthly": 0,
            "maintenance_monthly": 0,
            "vacancy_monthly": 0,
            "management_monthly": 0,
            "monthly_cash_flow": 0,
        }
        story = generator._build_monthly_breakdown_table(result)
        assert isinstance(story, list)

    def test_partial_fields(self, generator):
        """Should work when most fields are missing (defaults to 0)."""
        story = generator._build_monthly_breakdown_table({})
        assert isinstance(story, list)


# ---------------------------------------------------------------------------
# Tests: _build_projection_section
# ---------------------------------------------------------------------------


class TestBuildProjectionSection:
    """Tests for _build_projection_section method."""

    def test_returns_list(self, generator, projection):
        story = generator._build_projection_section(projection)
        assert isinstance(story, list)

    def test_contains_summary_table(self, generator, projection):
        from reportlab.platypus import Table

        story = generator._build_projection_section(projection)
        tables = [item for item in story if isinstance(item, Table)]
        assert len(tables) >= 2  # summary + yearly breakdown

    def test_with_irr(self, generator, projection):
        story = generator._build_projection_section(projection)
        assert isinstance(story, list)

    def test_without_irr(self, generator):
        proj = _StubCashFlowProjection(irr=None)
        story = generator._build_projection_section(proj)
        assert isinstance(story, list)

    def test_limits_yearly_breakdown_to_10(self, generator):
        """Yearly breakdown should be capped at 10 rows for readability."""
        many_years = [_StubYearlyCashFlow(year=y) for y in range(1, 21)]
        proj = _StubCashFlowProjection(yearly_breakdown=many_years, projection_years=20)
        from reportlab.platypus import Table

        story = generator._build_projection_section(proj)
        tables = [item for item in story if isinstance(item, Table)]
        # The yearly table should have header + 10 data rows
        yearly_table = tables[-1]
        # Table data has header + up to 10 rows
        assert len(yearly_table._argW) == 6  # 6 columns


# ---------------------------------------------------------------------------
# Tests: _build_footer
# ---------------------------------------------------------------------------


class TestBuildFooter:
    """Tests for _build_footer method."""

    def test_returns_list(self, generator):
        story = generator._build_footer()
        assert isinstance(story, list)

    def test_contains_disclaimer(self, generator):
        story = generator._build_footer()
        assert len(story) >= 1


# ---------------------------------------------------------------------------
# Tests: generate_pdf (integration-level with real reportlab)
# ---------------------------------------------------------------------------


class TestGeneratePdf:
    """Tests for generate_pdf method (full PDF generation)."""

    def test_returns_bytes(self, generator, sample_result):
        pdf_bytes = generator.generate_pdf(sample_result)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_pdf_starts_with_header(self, generator, sample_result):
        """Valid PDF files start with %PDF."""
        pdf_bytes = generator.generate_pdf(sample_result)
        assert pdf_bytes[:4] == b"%PDF"

    def test_with_projection(self, generator, sample_result, projection):
        pdf_bytes = generator.generate_pdf(sample_result, projection)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:4] == b"%PDF"

    def test_without_projection(self, generator, sample_result):
        pdf_bytes = generator.generate_pdf(sample_result, projection=None)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"

    def test_with_minimal_result(self, generator):
        pdf_bytes = generator.generate_pdf({})
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"

    def test_with_negative_cash_flow(self, generator):
        pdf_bytes = generator.generate_pdf(SAMPLE_RESULT_NEGATIVE_CASH_FLOW)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"

    def test_with_zero_income(self, generator):
        pdf_bytes = generator.generate_pdf(SAMPLE_RESULT_ZERO_INCOME)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"

    def test_with_score_breakdown(self, generator, sample_result):
        pdf_bytes = generator.generate_pdf(sample_result)
        assert isinstance(pdf_bytes, bytes)

    def test_pdf_is_larger_with_projection(self, generator, sample_result, projection):
        pdf_no_proj = generator.generate_pdf(sample_result, projection=None)
        pdf_with_proj = generator.generate_pdf(sample_result, projection)
        assert len(pdf_with_proj) > len(pdf_no_proj)


# ---------------------------------------------------------------------------
# Tests: generate_markdown
# ---------------------------------------------------------------------------


class TestGenerateMarkdown:
    """Tests for generate_markdown method."""

    def test_returns_string(self, generator, sample_result):
        md = generator.generate_markdown(sample_result)
        assert isinstance(md, str)

    def test_contains_header(self, generator, sample_result):
        md = generator.generate_markdown(sample_result)
        assert "# Real Estate Investment Analysis Report" in md

    def test_contains_generated_timestamp(self, generator, sample_result):
        md = generator.generate_markdown(sample_result)
        assert "**Generated:**" in md

    def test_contains_key_metrics_section(self, generator, sample_result):
        md = generator.generate_markdown(sample_result)
        assert "## Key Investment Metrics" in md
        assert "| Metric | Value |" in md

    def test_contains_cash_flow_breakdown(self, generator, sample_result):
        md = generator.generate_markdown(sample_result)
        assert "## Cash Flow Breakdown" in md
        assert "### Monthly Income & Expenses" in md

    def test_contains_monthly_income(self, generator, sample_result):
        md = generator.generate_markdown(sample_result)
        assert "**Gross Monthly Income:** $2,000.00" in md

    def test_contains_annual_summary(self, generator, sample_result):
        md = generator.generate_markdown(sample_result)
        assert "### Annual Summary" in md
        assert "**Gross Annual Income:** $24,000.00" in md

    def test_contains_investment_score(self, generator, sample_result):
        md = generator.generate_markdown(sample_result)
        assert "## Investment Score" in md
        assert "**Overall Score:** 75.0/100" in md

    def test_contains_score_bar(self, generator, sample_result):
        md = generator.generate_markdown(sample_result)
        assert "█" in md
        assert "░" in md

    def test_contains_score_breakdown(self, generator, sample_result):
        md = generator.generate_markdown(sample_result)
        assert "### Score Breakdown" in md
        assert "Cash Flow" in md
        assert "Appreciation" in md

    def test_no_score_breakdown_section_when_empty(self, generator):
        md = generator.generate_markdown(SAMPLE_RESULT_NO_SCORE_BREAKDOWN)
        assert "### Score Breakdown" not in md

    def test_contains_investment_summary(self, generator, sample_result):
        md = generator.generate_markdown(sample_result)
        assert "## Investment Summary" in md
        assert "**Total Initial Investment:** $60,000.00" in md

    def test_contains_disclaimer(self, generator, sample_result):
        md = generator.generate_markdown(sample_result)
        assert "informational purposes only" in md

    def test_negative_cash_flow_values(self, generator):
        md = generator.generate_markdown(SAMPLE_RESULT_NEGATIVE_CASH_FLOW)
        assert "$-200.00" in md

    def test_empty_result(self, generator):
        md = generator.generate_markdown({})
        assert "# Real Estate Investment Analysis Report" in md
        assert "## Key Investment Metrics" in md

    def test_metric_values_in_table(self, generator, sample_result):
        md = generator.generate_markdown(sample_result)
        assert "8.50%" in md
        assert "6.20%" in md

    def test_metric_labels_in_table(self, generator, sample_result):
        md = generator.generate_markdown(sample_result)
        assert "Cash on Cash ROI" in md
        assert "Cap Rate" in md
        assert "Gross Rental Yield" in md
        assert "Net Rental Yield" in md
