"""
Pytest configuration and shared fixtures.
"""

import pytest
from pathlib import Path
import pandas as pd
from langchain_community.llms.fake import FakeListLLM
from langchain_core.documents import Document

from agents.query_analyzer import QueryAnalyzer
from data.schemas import Property, PropertyCollection
from vector_store.reranker import PropertyReranker


@pytest.fixture
def query_analyzer():
    """Fixture for query analyzer."""
    return QueryAnalyzer()


@pytest.fixture
def sample_properties():
    """Fixture for sample property data."""
    properties = [
        Property(
            id="prop1",
            city="Krakow",
            rooms=2,
            bathrooms=1,
            price=950,
            area_sqm=55,
            has_parking=True,
            has_garden=False,
            property_type="apartment",
            source_url="http://example.com/1"
        ),
        Property(
            id="prop2",
            city="Krakow",
            rooms=2,
            bathrooms=1,
            price=890,
            area_sqm=48,
            has_parking=False,
            has_garden=True,
            property_type="apartment",
            source_url="http://example.com/2"
        ),
        Property(
            id="prop3",
            city="Warsaw",
            rooms=3,
            bathrooms=2,
            price=1350,
            area_sqm=75,
            has_parking=True,
            has_garden=False,
            property_type="apartment",
            source_url="http://example.com/3"
        ),
        Property(
            id="prop4",
            city="Krakow",
            rooms=1,
            bathrooms=1,
            price=650,
            area_sqm=35,
            has_parking=False,
            has_garden=False,
            property_type="studio",
            source_url="http://example.com/4"
        ),
        Property(
            id="prop5",
            city="Warsaw",
            rooms=2,
            bathrooms=1,
            price=1100,
            area_sqm=60,
            has_parking=True,
            has_garden=True,
            property_type="apartment",
            source_url="http://example.com/5"
        ),
    ]
    return PropertyCollection(properties=properties, total_count=5)


@pytest.fixture
def sample_documents(sample_properties):
    """Fixture for sample documents from properties."""
    documents = []
    for prop in sample_properties.properties:
        doc = Document(
            page_content=prop.to_search_text(),
            metadata=prop.to_dict()
        )
        documents.append(doc)
    return documents


@pytest.fixture
def reranker():
    """Fixture for property reranker."""
    return PropertyReranker()


@pytest.fixture
def fake_llm():
    """Fixture for fake LLM for testing."""
    responses = [
        "Here are some apartments in Krakow that match your criteria.",
        "The monthly mortgage payment would be approximately $730.",
        "Comparing Warsaw and Krakow, Warsaw is more expensive.",
    ]
    return FakeListLLM(responses=responses)
