"""
Service for tracking and analyzing search quality metrics.

This service provides functionality to:
- Record search events and user interactions
- Calculate quality metrics (CTR, MRR, NDCG, dwell time)
- Generate reports for ranking configuration evaluation
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import SearchEvent, SearchResultInteraction

logger = logging.getLogger(__name__)


@dataclass
class SearchMetricsSummary:
    """Summary of search quality metrics for a period."""

    total_searches: int = 0
    total_clicks: int = 0
    total_views: int = 0
    avg_ctr: float = 0.0
    avg_mrr: float = 0.0
    avg_ndcg: float = 0.0
    avg_dwell_time_ms: float = 0.0
    avg_results_per_search: float = 0.0
    avg_processing_time_ms: float = 0.0

    # Breakdown by config/experiment
    by_config: dict[str, dict[str, float]] = field(default_factory=dict)


@dataclass
class InteractionData:
    """Data for recording a search result interaction."""

    search_event_id: str
    property_id: str
    position: int
    viewed: bool = False
    view_duration_ms: Optional[int] = None
    clicked: bool = False
    favorited: bool = False
    contacted: bool = False


class SearchMetricsService:
    """Service for tracking and analyzing search quality metrics."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # =========================================================================
    # Recording Methods
    # =========================================================================

    async def record_search_event(
        self,
        session_id: str,
        query: str,
        results_count: int,
        results_property_ids: list[str],
        processing_time_ms: int,
        user_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
        ranking_config_id: Optional[str] = None,
    ) -> SearchEvent:
        """
        Record a search event.

        Args:
            session_id: Session identifier.
            query: Search query.
            results_count: Number of results returned.
            results_property_ids: Ordered list of property IDs in results.
            processing_time_ms: Processing time in milliseconds.
            user_id: Optional user ID.
            experiment_id: Optional A/B experiment ID.
            ranking_config_id: Optional ranking config ID.

        Returns:
            Created SearchEvent.
        """
        event = SearchEvent(
            session_id=session_id,
            user_id=user_id,
            experiment_id=experiment_id,
            ranking_config_id=ranking_config_id,
            query=query,
            results_count=results_count,
            results_property_ids=results_property_ids,
            processing_time_ms=processing_time_ms,
        )

        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)

        logger.debug(
            f"Recorded search event: session={session_id[:8]}..., "
            f"query='{query[:30]}...', results={results_count}"
        )

        return event

    async def record_interaction(self, data: InteractionData) -> SearchResultInteraction:
        """
        Record a user interaction with a search result.

        Args:
            data: InteractionData with interaction details.

        Returns:
            Created SearchResultInteraction.
        """
        interaction = SearchResultInteraction(
            search_event_id=data.search_event_id,
            property_id=data.property_id,
            position=data.position,
            viewed=data.viewed,
            view_duration_ms=data.view_duration_ms,
            clicked=data.clicked,
            favorited=data.favorited,
            contacted=data.contacted,
        )

        self.session.add(interaction)
        await self.session.commit()
        await self.session.refresh(interaction)

        return interaction

    async def record_click(
        self,
        search_event_id: str,
        property_id: str,
        position: int,
    ) -> SearchResultInteraction:
        """
        Convenience method to record a click interaction.

        Args:
            search_event_id: The search event ID.
            property_id: The clicked property ID.
            position: Position in search results (0-indexed).

        Returns:
            Created SearchResultInteraction.
        """
        return await self.record_interaction(
            InteractionData(
                search_event_id=search_event_id,
                property_id=property_id,
                position=position,
                viewed=True,
                clicked=True,
            )
        )

    async def record_view(
        self,
        search_event_id: str,
        property_id: str,
        position: int,
        view_duration_ms: Optional[int] = None,
    ) -> SearchResultInteraction:
        """
        Convenience method to record a view interaction.

        Args:
            search_event_id: The search event ID.
            property_id: The viewed property ID.
            position: Position in search results (0-indexed).
            view_duration_ms: Time spent viewing in milliseconds.

        Returns:
            Created SearchResultInteraction.
        """
        return await self.record_interaction(
            InteractionData(
                search_event_id=search_event_id,
                property_id=property_id,
                position=position,
                viewed=True,
                view_duration_ms=view_duration_ms,
            )
        )

    # =========================================================================
    # Metrics Calculation Methods
    # =========================================================================

    async def calculate_ctr(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        ranking_config_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
    ) -> float:
        """
        Calculate Click-Through Rate (CTR).

        CTR = Total Clicks / Total Search Results Shown

        Args:
            start_date: Start of period.
            end_date: End of period.
            ranking_config_id: Filter by ranking config.
            experiment_id: Filter by experiment.

        Returns:
            CTR as a float (0.0 to 1.0).
        """
        filters = []

        if start_date:
            filters.append(SearchEvent.search_timestamp >= start_date)
        if end_date:
            filters.append(SearchEvent.search_timestamp <= end_date)
        if ranking_config_id:
            filters.append(SearchEvent.ranking_config_id == ranking_config_id)
        if experiment_id:
            filters.append(SearchEvent.experiment_id == experiment_id)

        # Count total results shown
        result = await self.session.execute(
            select(func.sum(SearchEvent.results_count)).where(and_(*filters))
        )
        total_results = result.scalar() or 0

        if total_results == 0:
            return 0.0

        # Count total clicks via interactions
        click_result = await self.session.execute(
            select(func.count())
            .select_from(SearchResultInteraction)
            .join(SearchEvent)
            .where(and_(SearchResultInteraction.clicked == True, *filters))  # noqa: E712
        )
        total_clicks = click_result.scalar() or 0

        return total_clicks / total_results

    async def calculate_mrr(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        ranking_config_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
    ) -> float:
        """
        Calculate Mean Reciprocal Rank (MRR).

        MRR = Average of (1 / rank of first clicked result) for each search

        Args:
            start_date: Start of period.
            end_date: End of period.
            ranking_config_id: Filter by ranking config.
            experiment_id: Filter by experiment.

        Returns:
            MRR as a float (0.0 to 1.0).
        """
        filters = []

        if start_date:
            filters.append(SearchEvent.search_timestamp >= start_date)
        if end_date:
            filters.append(SearchEvent.search_timestamp <= end_date)
        if ranking_config_id:
            filters.append(SearchEvent.ranking_config_id == ranking_config_id)
        if experiment_id:
            filters.append(SearchEvent.experiment_id == experiment_id)

        # Get first click position for each search event
        result = await self.session.execute(
            select(
                SearchResultInteraction.search_event_id,
                func.min(SearchResultInteraction.position).label("first_click_pos"),
            )
            .join(SearchEvent)
            .where(
                and_(
                    SearchResultInteraction.clicked == True,  # noqa: E712
                    *filters,
                )
            )
            .group_by(SearchResultInteraction.search_event_id)
        )

        first_clicks = result.all()

        if not first_clicks:
            return 0.0

        # Calculate MRR
        reciprocal_ranks = [1.0 / (row.first_click_pos + 1) for row in first_clicks]
        return float(sum(reciprocal_ranks) / len(reciprocal_ranks))

    async def calculate_ndcg(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        ranking_config_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
        k: int = 10,
    ) -> float:
        """
        Calculate Normalized Discounted Cumulative Gain (NDCG@k).

        Uses click and favorite signals as relevance indicators.
        Click = 1, Favorite = 2, Contact = 3

        Args:
            start_date: Start of period.
            end_date: End of period.
            ranking_config_id: Filter by ranking config.
            experiment_id: Filter by experiment.
            k: Number of positions to consider.

        Returns:
            Average NDCG@k as a float (0.0 to 1.0).
        """
        filters = []

        if start_date:
            filters.append(SearchEvent.search_timestamp >= start_date)
        if end_date:
            filters.append(SearchEvent.search_timestamp <= end_date)
        if ranking_config_id:
            filters.append(SearchEvent.ranking_config_id == ranking_config_id)
        if experiment_id:
            filters.append(SearchEvent.experiment_id == experiment_id)

        # Get search events with interactions
        events_result = await self.session.execute(select(SearchEvent).where(and_(*filters)))
        events = events_result.scalars().all()

        if not events:
            return 0.0

        ndcg_scores = []

        for event in events:
            # Get interactions for this event
            interactions_result = await self.session.execute(
                select(SearchResultInteraction)
                .where(SearchResultInteraction.search_event_id == event.id)
                .order_by(SearchResultInteraction.position)
            )
            interactions = interactions_result.scalars().all()

            if not interactions:
                continue

            # Build relevance gains (position -> gain)
            gains: dict[int, float] = {}
            for interaction in interactions:
                if interaction.position >= k:
                    continue

                # Calculate gain based on interaction type
                gain = 0.0
                if interaction.clicked:
                    gain += 1.0
                if interaction.favorited:
                    gain += 1.0  # Extra for favorite
                if interaction.contacted:
                    gain += 1.0  # Extra for contact

                if interaction.position in gains:
                    gains[interaction.position] = max(gains[interaction.position], gain)
                else:
                    gains[interaction.position] = gain

            if not gains:
                continue

            # Calculate DCG
            dcg = 0.0
            for pos, gain in gains.items():
                dcg += gain / math.log2(pos + 2)  # +2 because position is 0-indexed

            # Calculate ideal DCG (sorted by gain descending)
            ideal_gains = sorted(gains.values(), reverse=True)
            idcg = 0.0
            for i, gain in enumerate(ideal_gains[:k]):
                idcg += gain / math.log2(i + 2)

            if idcg > 0:
                ndcg_scores.append(dcg / idcg)

        if not ndcg_scores:
            return 0.0

        return sum(ndcg_scores) / len(ndcg_scores)

    async def calculate_avg_dwell_time(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        ranking_config_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
    ) -> float:
        """
        Calculate average dwell time in milliseconds.

        Args:
            start_date: Start of period.
            end_date: End of period.
            ranking_config_id: Filter by ranking config.
            experiment_id: Filter by experiment.

        Returns:
            Average dwell time in milliseconds.
        """
        filters = []

        if start_date:
            filters.append(SearchEvent.search_timestamp >= start_date)
        if end_date:
            filters.append(SearchEvent.search_timestamp <= end_date)
        if ranking_config_id:
            filters.append(SearchEvent.ranking_config_id == ranking_config_id)
        if experiment_id:
            filters.append(SearchEvent.experiment_id == experiment_id)

        result = await self.session.execute(
            select(func.avg(SearchResultInteraction.view_duration_ms))
            .join(SearchEvent)
            .where(and_(SearchResultInteraction.view_duration_ms.isnot(None), *filters))
        )

        avg = result.scalar()
        return float(avg) if avg else 0.0

    async def get_metrics_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        ranking_config_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
    ) -> SearchMetricsSummary:
        """
        Get a comprehensive summary of search metrics.

        Args:
            start_date: Start of period (default: 7 days ago).
            end_date: End of period (default: now).
            ranking_config_id: Filter by ranking config.
            experiment_id: Filter by experiment.

        Returns:
            SearchMetricsSummary with all metrics.
        """
        if start_date is None:
            start_date = datetime.now(UTC) - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now(UTC)

        filters = []
        if start_date:
            filters.append(SearchEvent.search_timestamp >= start_date)
        if end_date:
            filters.append(SearchEvent.search_timestamp <= end_date)
        if ranking_config_id:
            filters.append(SearchEvent.ranking_config_id == ranking_config_id)
        if experiment_id:
            filters.append(SearchEvent.experiment_id == experiment_id)

        # Get basic counts
        count_result = await self.session.execute(
            select(
                func.count().label("total_searches"),
                func.sum(SearchEvent.results_count).label("total_results"),
                func.avg(SearchEvent.results_count).label("avg_results"),
                func.avg(SearchEvent.processing_time_ms).label("avg_processing"),
            ).where(and_(*filters))
        )
        counts = count_result.one()

        # Get click counts
        click_result = await self.session.execute(
            select(func.count())
            .select_from(SearchResultInteraction)
            .join(SearchEvent)
            .where(and_(SearchResultInteraction.clicked == True, *filters))  # noqa: E712
        )
        total_clicks = click_result.scalar() or 0

        # Get view counts
        view_result = await self.session.execute(
            select(func.count())
            .select_from(SearchResultInteraction)
            .join(SearchEvent)
            .where(and_(SearchResultInteraction.viewed == True, *filters))  # noqa: E712
        )
        total_views = view_result.scalar() or 0

        # Calculate metrics
        total_results = counts.total_results or 0
        ctr = total_clicks / total_results if total_results > 0 else 0.0

        summary = SearchMetricsSummary(
            total_searches=counts.total_searches or 0,
            total_clicks=total_clicks,
            total_views=total_views,
            avg_ctr=ctr,
            avg_mrr=await self.calculate_mrr(
                start_date, end_date, ranking_config_id, experiment_id
            ),
            avg_ndcg=await self.calculate_ndcg(
                start_date, end_date, ranking_config_id, experiment_id
            ),
            avg_dwell_time_ms=await self.calculate_avg_dwell_time(
                start_date, end_date, ranking_config_id, experiment_id
            ),
            avg_results_per_search=float(counts.avg_results or 0),
            avg_processing_time_ms=float(counts.avg_processing or 0),
        )

        return summary

    async def compare_configs(
        self,
        config_ids: list[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict[str, SearchMetricsSummary]:
        """
        Compare metrics across multiple ranking configurations.

        Args:
            config_ids: List of ranking config IDs to compare.
            start_date: Start of period.
            end_date: End of period.

        Returns:
            Dict mapping config ID to metrics summary.
        """
        results = {}

        for config_id in config_ids:
            summary = await self.get_metrics_summary(
                start_date=start_date,
                end_date=end_date,
                ranking_config_id=config_id,
            )
            results[config_id] = summary

        return results


# Dependency injection helper
def get_search_metrics_service(session: AsyncSession) -> SearchMetricsService:
    """Get a SearchMetricsService instance."""
    return SearchMetricsService(session)
