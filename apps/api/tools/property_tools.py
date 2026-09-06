"""
Property-specific tools for the agent.

This module provides backward-compatible re-exports of all property tools
that have been decomposed into domain-focused modules:
- mortgage_tools: Mortgage calculator
- tco_tools: TCO calculator, TCO comparison, Rent vs Buy
- investment_tools: Investment analyzer, Advanced investment analyzer
- comparison_tools: Property comparison, price analysis, location analysis, commute tools
- neighborhood_tools: Neighborhood quality index
- commute_tool: OSRM-based commute analysis (free, no API key required)
- negotiation_tool: Negotiation helper with price band analysis and outreach emails

The create_property_tools() factory function remains here for convenience.
"""

from typing import Any, List

from langchain_core.tools import BaseTool

# Re-export OSRM commute tools (Task #114)
from tools.commute_tool import (  # noqa: F401
    CommuteAnalysisInput,
    CommuteTool,
    MultiCommuteInput,
    MultiOriginCommuteTool,
    OSRMCommuteClient,
    calculate_commute,
    get_osrm_client,
)

# Re-export comparison tools
from tools.comparison_tools import (  # noqa: F401
    CommuteRankingInput,
    CommuteRankingTool,
    CommuteTimeAnalysisTool,
    CommuteTimeInput,
    LocationAnalysisInput,
    LocationAnalysisTool,
    PriceAnalysisInput,
    PriceAnalysisTool,
    PropertyComparisonInput,
    PropertyComparisonTool,
)

# Re-export investment tools
from tools.investment_tools import (  # noqa: F401
    AdvancedInvestmentInput,
    AdvancedInvestmentResult,
    AdvancedInvestmentTool,
    InvestmentAnalysisInput,
    InvestmentAnalysisResult,
    InvestmentCalculatorTool,
)

# Import AI listing generator tools (TASK-023)
from tools.listing_generator_tools import (
    HeadlineGeneratorTool,
    PropertyDescriptionGeneratorTool,
    SocialMediaContentGeneratorTool,
)

# Re-export mortgage tools
from tools.mortgage_tools import (  # noqa: F401
    MortgageCalculatorTool,
    MortgageInput,
    MortgageResult,
)

# Re-export negotiation tools (Task #115)
from tools.negotiation_tool import (  # noqa: F401
    NegotiationInput,
    NegotiationTool,
)

# Re-export AI neighborhood one-liner (v5.1)
from tools.neighborhood_summary import (  # noqa: F401
    NeighborhoodSummaryInput,
    NeighborhoodSummaryTool,
)

# Re-export neighborhood tools
from tools.neighborhood_tools import (  # noqa: F401
    NeighborhoodQualityIndexTool,
    NeighborhoodQualityInput,
    NeighborhoodQualityResult,
)

# Re-export AI price forecast tool (v5.1)
from tools.price_forecast_tools import (  # noqa: F401
    ForecastPoint,
    PriceForecastInput,
    PriceForecastResult,
    PriceForecastTool,
)

# Re-export TCO tools
from tools.tco_tools import (  # noqa: F401
    EnhancedTCOResult,
    RentVsBuyCalculatorTool,
    RentVsBuyInput,
    RentVsBuyResult,
    TCOCalculatorTool,
    TCOComparisonInput,
    TCOComparisonResult,
    TCOComparisonTool,
    TCOInput,
    TCOLocationDefaults,
    TCOProjection,
    TCOResult,
    YearlyBreakdown,
)


# Factory function to create all tools
def create_property_tools(vector_store: Any = None) -> List[BaseTool]:
    """
    Create all property-related tools.

    Args:
        vector_store: Optional vector store for data access.
                      Required for comparison, price, and location tools.

    Returns:
        List of initialized tool instances
    """
    return [
        MortgageCalculatorTool(),
        TCOCalculatorTool(),
        InvestmentCalculatorTool(),
        AdvancedInvestmentTool(),  # Task #39: Advanced analytics
        RentVsBuyCalculatorTool(),  # Task #42: Rent vs Buy Calculator
        NeighborhoodQualityIndexTool(),
        PropertyComparisonTool(vector_store=vector_store),
        PriceAnalysisTool(vector_store=vector_store),
        LocationAnalysisTool(vector_store=vector_store),
        # TASK-021: Commute Time Analysis
        CommuteTimeAnalysisTool(vector_store=vector_store),
        CommuteRankingTool(vector_store=vector_store),
        # Task #114: OSRM-based commute analysis (free, no API key)
        CommuteTool(),
        MultiOriginCommuteTool(),
        # Task #115: Negotiation helper with price band analysis
        NegotiationTool(vector_store=vector_store),
        # TASK-023: AI Listing Generator
        PropertyDescriptionGeneratorTool(),
        HeadlineGeneratorTool(),
        SocialMediaContentGeneratorTool(),
        # v5.1: AI Price Forecast with multi-year projection
        PriceForecastTool(vector_store=vector_store),
        # v5.1: AI Neighborhood One-Liner
        NeighborhoodSummaryTool(),
    ]
