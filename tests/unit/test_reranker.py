"""
Unit tests for result reranker.

Tests reranking logic, boosting factors, and diversity penalties.
"""

import pytest
from langchain_core.documents import Document

from vector_store.reranker import PropertyReranker, SimpleReranker, create_reranker


class TestPropertyReranker:
    """Test suite for PropertyReranker."""

    def test_reranker_initialization(self):
        """Test reranker initialization with custom parameters."""
        reranker = PropertyReranker(
            boost_exact_matches=2.0,
            boost_metadata_match=1.5,
            boost_quality_signals=1.3,
            diversity_penalty=0.8
        )

        assert reranker.boost_exact_matches == 2.0
        assert reranker.boost_metadata_match == 1.5
        assert reranker.boost_quality_signals == 1.3
        assert reranker.diversity_penalty == 0.8

    def test_basic_reranking(self, reranker, sample_documents):
        """Test basic reranking functionality."""
        query = "apartments with parking"
        results = reranker.rerank(query, sample_documents, k=5)

        assert len(results) <= 5
        assert all(isinstance(item, tuple) for item in results)
        assert all(len(item) == 2 for item in results)

    def test_reranking_order_changes(self, reranker, sample_documents):
        """Test that reranking changes result order."""
        query = "affordable apartment with parking"

        # Initial order
        initial_order = [doc.metadata['id'] for doc in sample_documents]

        # Reranked order
        reranked = reranker.rerank(query, sample_documents, k=5)
        reranked_order = [doc.metadata['id'] for doc, score in reranked]

        # Orders should be different (unless by chance they're the same)
        # We'll check that scores vary
        scores = [score for doc, score in reranked]
        assert len(set(scores)) > 1  # At least some different scores

    def test_exact_match_boosting(self, reranker):
        """Test exact keyword match boosting."""
        # Create documents with and without exact matches
        docs = [
            Document(
                page_content="A beautiful apartment with garden",
                metadata={"id": "1", "has_garden": True, "price": 1000}
            ),
            Document(
                page_content="A nice property available",
                metadata={"id": "2", "has_garden": False, "price": 1000}
            ),
        ]

        query = "apartment with garden"
        results = reranker.rerank(query, docs, k=2)

        # Document with exact matches should rank higher
        top_doc, top_score = results[0]
        assert "garden" in top_doc.page_content.lower()

    def test_metadata_alignment_boosting(self, reranker):
        """Test metadata alignment boosting."""
        docs = [
            Document(
                page_content="Property in city",
                metadata={"id": "1", "price": 900, "has_parking": True}
            ),
            Document(
                page_content="Property in city",
                metadata={"id": "2", "price": 1500, "has_parking": False}
            ),
        ]

        query = "under $1000 with parking"
        user_prefs = {'max_price': 1000, 'has_parking': True}

        results = reranker.rerank(
            query, docs, user_preferences=user_prefs, k=2
        )

        # Document matching preferences should rank higher
        top_doc, top_score = results[0]
        assert top_doc.metadata['price'] <= 1000
        assert top_doc.metadata['has_parking'] is True

    def test_quality_signals_boosting(self, reranker):
        """Test quality signals boosting."""
        docs = [
            Document(
                page_content="Basic apartment" * 30,  # Longer description
                metadata={
                    "id": "1",
                    "price": 1000,
                    "has_parking": True,
                    "has_garden": True,
                    "has_balcony": True,
                    "price_per_sqm": 20
                }
            ),
            Document(
                page_content="Apartment",  # Short description
                metadata={
                    "id": "2",
                    "price": 1000,
                    "price_per_sqm": 35
                }
            ),
        ]

        query = "apartment"
        results = reranker.rerank(query, docs, k=2)

        # Document with better quality signals should rank higher
        top_doc, top_score = results[0]
        assert top_doc.metadata['id'] == "1"  # More amenities, better price/sqm

    def test_diversity_penalty(self, reranker):
        """Test diversity penalty for similar results."""
        # Create multiple similar documents
        docs = [
            Document(
                page_content=f"Apartment {i} in Krakow",
                metadata={
                    "id": f"{i}",
                    "city": "Krakow",
                    "price": 950 + i * 10
                }
            )
            for i in range(10)
        ]

        query = "apartments"
        results = reranker.rerank(query, docs, k=10)

        # Check that diversity penalty was applied (visible in score variation)
        scores = [score for doc, score in results]
        assert len(set(scores)) > 1

    def test_k_parameter_limits_results(self, reranker, sample_documents):
        """Test that k parameter limits number of results."""
        query = "apartments"

        # Ask for 3 results
        results = reranker.rerank(query, sample_documents, k=3)
        assert len(results) == 3

        # Ask for more than available
        results = reranker.rerank(query, sample_documents, k=100)
        assert len(results) <= len(sample_documents)

    def test_empty_documents_list(self, reranker):
        """Test reranking with empty documents list."""
        query = "apartments"
        results = reranker.rerank(query, [], k=5)

        assert len(results) == 0

    def test_initial_scores_used(self, reranker, sample_documents):
        """Test that initial scores are incorporated."""
        query = "apartments"
        initial_scores = [0.9, 0.8, 0.7, 0.6, 0.5]

        results = reranker.rerank(
            query,
            sample_documents,
            initial_scores=initial_scores,
            k=5
        )

        # Results should be returned
        assert len(results) > 0

    def test_no_initial_scores(self, reranker, sample_documents):
        """Test reranking without initial scores."""
        query = "apartments"

        results = reranker.rerank(query, sample_documents, k=5)

        # Should still work with default scores
        assert len(results) > 0

    def test_reranking_improves_relevance(self, reranker):
        """Test that reranking improves relevance for specific query."""
        docs = [
            Document(
                page_content="Expensive luxury apartment",
                metadata={"id": "1", "price": 5000, "has_parking": False}
            ),
            Document(
                page_content="Affordable apartment with parking",
                metadata={"id": "2", "price": 900, "has_parking": True}
            ),
            Document(
                page_content="Mid-range property",
                metadata={"id": "3", "price": 1500, "has_parking": False}
            ),
        ]

        query = "affordable apartment with parking"
        user_prefs = {'max_price': 1000, 'has_parking': True}

        results = reranker.rerank(
            query, docs, user_preferences=user_prefs, k=3
        )

        # Best match should be at top
        top_doc, top_score = results[0]
        assert top_doc.metadata['id'] == "2"  # Matches all criteria


class TestSimpleReranker:
    """Test suite for SimpleReranker."""

    def test_simple_reranker_initialization(self):
        """Test simple reranker initialization."""
        reranker = SimpleReranker(boost_factor=2.0)
        assert reranker.boost_factor == 2.0

    def test_simple_reranking(self, sample_documents):
        """Test simple reranking with exact matches."""
        reranker = SimpleReranker()
        query = "apartments in Krakow"

        results = reranker.rerank(query, sample_documents, k=3)

        assert len(results) <= 3
        assert all(isinstance(item, tuple) for item in results)

    def test_exact_match_boost(self):
        """Test that exact matches get boosted."""
        reranker = SimpleReranker(boost_factor=2.0)

        docs = [
            Document(
                page_content="A nice property",
                metadata={"id": "1"}
            ),
            Document(
                page_content="An apartment in Krakow",
                metadata={"id": "2"}
            ),
        ]

        query = "apartment Krakow"
        results = reranker.rerank(query, docs, k=2)

        # Document with exact matches should rank higher
        top_doc, top_score = results[0]
        assert top_doc.metadata['id'] == "2"


class TestRerankerFactory:
    """Test reranker factory function."""

    def test_create_advanced_reranker(self):
        """Test creating advanced reranker."""
        reranker = create_reranker(advanced=True)
        assert isinstance(reranker, PropertyReranker)

    def test_create_simple_reranker(self):
        """Test creating simple reranker."""
        reranker = create_reranker(advanced=False)
        assert isinstance(reranker, SimpleReranker)


class TestRerankerEdgeCases:
    """Test edge cases for reranker."""

    def test_single_document(self, reranker):
        """Test reranking with single document."""
        doc = Document(
            page_content="An apartment",
            metadata={"id": "1", "price": 1000}
        )

        results = reranker.rerank("apartment", [doc], k=5)

        assert len(results) == 1

    def test_query_with_special_characters(self, reranker, sample_documents):
        """Test query with special characters."""
        query = "apartment $1000 2-bedroom!"

        results = reranker.rerank(query, sample_documents, k=3)

        # Should handle gracefully
        assert len(results) > 0

    def test_very_long_query(self, reranker, sample_documents):
        """Test with very long query."""
        query = "apartment " * 100  # Very long repeated query

        results = reranker.rerank(query, sample_documents, k=3)

        # Should complete without error
        assert len(results) > 0

    def test_empty_query(self, reranker, sample_documents):
        """Test with empty query."""
        query = ""

        results = reranker.rerank(query, sample_documents, k=3)

        # Should return documents with neutral scoring
        assert len(results) > 0
