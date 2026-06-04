"""
Service for A/B testing ranking configurations.

This service manages experiment assignments and provides
deterministic bucketing for consistent user experience.
"""

import hashlib
import logging
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security_utils import sanitize_for_log
from db.models import ABExperiment, ABExperimentAssignment, RankingConfig
from services.ranking_config_service import RankingConfigService

logger = logging.getLogger(__name__)


class ABTestingService:
    """Service for managing A/B test experiments and assignments."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._config_service = RankingConfigService(session)

    async def get_active_experiment(self) -> Optional[ABExperiment]:
        """
        Get the currently running experiment.

        Returns:
            The active ABExperiment or None.
        """
        now = datetime.now(UTC)

        stmt = (
            select(ABExperiment)
            .where(
                and_(
                    ABExperiment.status == "running",
                    ABExperiment.start_date <= now,
                    (ABExperiment.end_date.is_(None)) | (ABExperiment.end_date > now),
                )
            )
            .order_by(ABExperiment.start_date.desc())
            .limit(1)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_experiment_for_session(
        self,
        session_id: str,
        user_id: Optional[str] = None,
    ) -> Optional[ABExperimentAssignment]:
        """
        Get or create an experiment assignment for a session.

        Uses deterministic hashing for consistent assignment.

        Args:
            session_id: The session identifier.
            user_id: Optional user ID for logged-in users.

        Returns:
            ABExperimentAssignment or None if no active experiment.
        """
        experiment = await self.get_active_experiment()
        if not experiment:
            return None

        # Check for existing assignment
        stmt = select(ABExperimentAssignment).where(
            and_(
                ABExperimentAssignment.experiment_id == experiment.id,
                ABExperimentAssignment.session_id == session_id,
            )
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        # Create new assignment using deterministic hash
        variant = self._assign_variant(
            session_id=session_id,
            experiment_id=str(experiment.id),
            traffic_split=experiment.traffic_split,
        )

        config_id = (
            experiment.control_config_id if variant == "control" else experiment.treatment_config_id
        )

        assignment = ABExperimentAssignment(
            experiment_id=experiment.id,
            user_id=user_id,
            session_id=session_id,
            variant=variant,
            config_id=config_id,
        )

        self.session.add(assignment)
        await self.session.commit()
        await self.session.refresh(assignment)

        logger.debug(
            "Created experiment assignment: experiment=%s, session=%s..., variant=%s",
            sanitize_for_log(experiment.name),
            sanitize_for_log(session_id[:8]),
            sanitize_for_log(variant),
        )

        return assignment

    async def get_ranking_config_for_session(
        self,
        session_id: str,
        user_id: Optional[str] = None,
    ) -> Optional[RankingConfig]:
        """
        Get the appropriate ranking config for a session.

        If the session is in an experiment, returns the assigned config.
        Otherwise, returns the active config.

        Args:
            session_id: The session identifier.
            user_id: Optional user ID.

        Returns:
            RankingConfig or None.
        """
        assignment = await self.get_experiment_for_session(session_id=session_id, user_id=user_id)

        if assignment:
            return await self._config_service.get_config_by_id(str(assignment.config_id))

        # No experiment, return active config
        return await self._config_service.get_active_config()

    def _assign_variant(
        self,
        session_id: str,
        experiment_id: str,
        traffic_split: float,
    ) -> str:
        """
        Deterministically assign a variant using hashing.

        Args:
            session_id: Session identifier.
            experiment_id: Experiment identifier.
            traffic_split: Traffic split ratio (0.5 = 50/50).

        Returns:
            "control" or "treatment".
        """
        # Create deterministic hash
        hash_input = f"{session_id}:{experiment_id}"
        hash_value = int(hashlib.sha256(hash_input.encode()).hexdigest(), 16)
        bucket = (hash_value % 100) / 100.0

        return "treatment" if bucket < traffic_split else "control"

    async def start_experiment(self, experiment_id: str) -> Optional[ABExperiment]:
        """
        Start an experiment.

        Args:
            experiment_id: The experiment ID.

        Returns:
            The started experiment or None if not found.
        """
        stmt = select(ABExperiment).where(ABExperiment.id == experiment_id)
        result = await self.session.execute(stmt)
        experiment = result.scalar_one_or_none()

        if not experiment:
            return None

        if experiment.status != "draft":
            raise ValueError(
                f"Can only start experiments in 'draft' status, current status: {experiment.status}"
            )

        experiment.status = "running"
        await self.session.commit()
        await self.session.refresh(experiment)

        logger.info(
            "Started experiment '%s' (id=%s)",
            sanitize_for_log(experiment.name),
            sanitize_for_log(experiment.id),
        )
        return experiment

    async def stop_experiment(
        self, experiment_id: str, reason: Optional[str] = None
    ) -> Optional[ABExperiment]:
        """
        Stop an experiment.

        Args:
            experiment_id: The experiment ID.
            reason: Optional reason for stopping.

        Returns:
            The stopped experiment or None if not found.
        """
        stmt = select(ABExperiment).where(ABExperiment.id == experiment_id)
        result = await self.session.execute(stmt)
        experiment = result.scalar_one_or_none()

        if not experiment:
            return None

        experiment.status = "completed"
        experiment.end_date = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(experiment)

        logger.info(
            "Stopped experiment '%s' (id=%s)%s",
            sanitize_for_log(experiment.name),
            sanitize_for_log(experiment.id),
            sanitize_for_log(f" - reason: {reason}" if reason else ""),
        )
        return experiment


# Dependency injection helper
def get_ab_testing_service(session: AsyncSession) -> ABTestingService:
    """Get an ABTestingService instance."""
    return ABTestingService(session)
