from unittest.mock import MagicMock

import pytest
from langchain_core.documents import Document

from tools.comparison_tools import (
    CommuteRankingTool,
    CommuteTimeAnalysisTool,
    LocationAnalysisTool,
    PriceAnalysisTool,
    PropertyComparisonTool,
)
from tools.investment_tools import AdvancedInvestmentTool, InvestmentCalculatorTool
from tools.listing_generator_tools import (
    HeadlineGeneratorTool,
    PropertyDescriptionGeneratorTool,
    SocialMediaContentGeneratorTool,
)
from tools.mortgage_tools import MortgageCalculatorTool
from tools.neighborhood_tools import NeighborhoodQualityIndexTool
from tools.property_tools import create_property_tools
from tools.tco_tools import RentVsBuyCalculatorTool, TCOCalculatorTool


@pytest.fixture
def mock_vector_store():
    store = MagicMock()

    # Mock get_properties_by_ids
    def get_by_ids(ids):
        docs = []
        for pid in ids:
            if pid == "prop1":
                docs.append(
                    Document(
                        page_content="Prop 1 Desc",
                        metadata={
                            "id": "prop1",
                            "price": 500000,
                            "city": "Madrid",
                            "lat": 40.4168,
                            "lon": -3.7038,
                        },
                    )
                )
            elif pid == "prop2":
                docs.append(
                    Document(
                        page_content="Prop 2 Desc",
                        metadata={
                            "id": "prop2",
                            "price": 600000,
                            "city": "Madrid",
                            "lat": 40.4200,
                            "lon": -3.7000,
                        },
                    )
                )
        return docs

    store.get_properties_by_ids.side_effect = get_by_ids

    # Mock search
    def search(query, k=5):
        return [
            (
                Document(
                    page_content="D1", metadata={"price": 100000, "property_type": "Apartment"}
                ),
                0.9,
            ),
            (
                Document(page_content="D2", metadata={"price": 200000, "property_type": "House"}),
                0.8,
            ),
            (
                Document(
                    page_content="D3", metadata={"price": 150000, "property_type": "Apartment"}
                ),
                0.7,
            ),
        ]

    store.search.side_effect = search

    return store


def test_create_property_tools(mock_vector_store):
    tools = create_property_tools(mock_vector_store)
    # Task #114: Added CommuteTool, MultiOriginCommuteTool
    # Task #115: Added NegotiationTool
    # v5.1: Added PriceForecastTool and NeighborhoodSummaryTool
    assert len(tools) == 19
    assert isinstance(tools[0], MortgageCalculatorTool)
    assert isinstance(tools[1], TCOCalculatorTool)
    assert isinstance(tools[2], InvestmentCalculatorTool)
    assert isinstance(tools[3], AdvancedInvestmentTool)  # Task #39
    assert isinstance(tools[4], RentVsBuyCalculatorTool)  # Task #42
    assert isinstance(tools[5], NeighborhoodQualityIndexTool)
    assert isinstance(tools[6], PropertyComparisonTool)
    assert isinstance(tools[7], PriceAnalysisTool)
    assert isinstance(tools[8], LocationAnalysisTool)
    # TASK-021: Commute tools
    assert isinstance(tools[9], CommuteTimeAnalysisTool)
    assert isinstance(tools[10], CommuteRankingTool)
    # Task #114: OSRM-based commute tools
    from tools.commute_tool import CommuteTool, MultiOriginCommuteTool
    from tools.negotiation_tool import NegotiationTool

    assert isinstance(tools[11], CommuteTool)
    assert isinstance(tools[12], MultiOriginCommuteTool)
    # Task #115: Negotiation helper
    assert isinstance(tools[13], NegotiationTool)
    # TASK-023: AI Listing Generator tools
    assert isinstance(tools[14], PropertyDescriptionGeneratorTool)
    assert isinstance(tools[15], HeadlineGeneratorTool)
    assert isinstance(tools[16], SocialMediaContentGeneratorTool)


def test_mortgage_tool():
    tool = MortgageCalculatorTool()
    # Test valid calculation
    result = tool._run(
        property_price=100000, down_payment_percent=20, interest_rate=5, loan_years=30
    )
    assert "Mortgage Calculation for $100,000.00" in result
    assert "Monthly Payment: $" in result

    # Test invalid input
    result_err = tool._run(property_price=-100)
    assert "Error:" in result_err


def test_comparison_tool(mock_vector_store):
    tool = PropertyComparisonTool(vector_store=mock_vector_store)
    result = tool._run("prop1, prop2")

    assert "Property Comparison:" in result
    assert "prop1" in result
    assert "prop2" in result
    assert "$500,000" in result
    assert "$600,000" in result
    assert "Price difference: $100,000" in result


def test_price_analysis_tool(mock_vector_store):
    tool = PriceAnalysisTool(vector_store=mock_vector_store)
    result = tool._run("apartments in madrid")

    assert "Price Analysis for 'apartments in madrid'" in result
    assert "Average: $150,000.00" in result  # (100+200+150)/3
    assert "Median: $150,000.00" in result
    assert "Min: $100,000.00" in result
    assert "Max: $200,000.00" in result
    assert "Apartment: 2" in result
    assert "House: 1" in result


def test_location_analysis_tool(mock_vector_store):
    tool = LocationAnalysisTool(vector_store=mock_vector_store)
    result = tool._run("prop1")

    assert "Location Analysis for Property prop1" in result
    assert "City: Madrid" in result
    assert "Coordinates: 40.4168, -3.7038" in result


def test_tco_calculator_tool():
    tool = TCOCalculatorTool()
    # Test valid calculation with all optional costs
    result = tool._run(
        property_price=300000,
        down_payment_percent=20,
        interest_rate=4.5,
        loan_years=30,
        monthly_hoa=200,
        annual_property_tax=3600,
        annual_insurance=1200,
        monthly_utilities=150,
        monthly_internet=50,
        monthly_parking=100,
        maintenance_percent=1.0,
    )

    assert "Total Cost of Ownership" in result
    assert "Monthly Costs" in result
    assert "Mortgage Payment:" in result
    assert "Property Tax:" in result
    assert "Home Insurance:" in result
    assert "HOA Fees:" in result
    assert "Utilities:" in result
    assert "Internet/Cable:" in result
    assert "Parking:" in result
    assert "MONTHLY TCO:" in result
    assert "Annual Costs" in result
    assert "ANNUAL TCO:" in result

    # Test with minimal inputs (just mortgage)
    result_minimal = tool._run(
        property_price=200000,
        down_payment_percent=15,
        interest_rate=5.0,
        loan_years=20,
    )

    assert "Total Cost of Ownership" in result_minimal
    assert "$200,000" in result_minimal

    # Test invalid input
    result_err = tool._run(property_price=-100)
    assert "Error:" in result_err
