"""Integration tests for the lead-scoring funnel.

`get_agent_funnel` counts the leads assigned to one agent by priority tier
and by status. It reads them through the real repository - the agent filter
is a join over the assignments, not a column on the lead - so it is
exercised here against the real session, as the integration suite does.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import AgentAssignment, Lead, User
from services.lead_scoring import PrioritizedLeadScoringService


@pytest.fixture
async def agent(db_session: AsyncSession) -> str:
    """A user the leads can be assigned to."""
    user = User(id="agent-funnel-1", email="agent-funnel@example.test")
    db_session.add(user)
    await db_session.flush()
    return user.id


@pytest.mark.asyncio
async def test_the_funnel_counts_the_leads_assigned_to_one_agent(
    db_session: AsyncSession, agent: str
) -> None:
    """A hot, new lead is counted once, in the hot tier and in the new status."""
    lead = Lead(visitor_id="visitor-funnel-1", status="new", current_score=90)
    db_session.add(lead)
    await db_session.flush()
    db_session.add(AgentAssignment(lead_id=lead.id, agent_id=agent))
    await db_session.flush()

    funnel = await PrioritizedLeadScoringService(db_session).get_agent_funnel(agent)

    assert funnel["agent_id"] == agent
    assert funnel["total_leads"] == 1
    assert funnel["by_priority"]["hot"] == 1
    assert funnel["by_priority"]["cold"] == 0
    assert funnel["by_status"]["new"] == 1
    assert funnel["average_score"] == 90.0


@pytest.mark.asyncio
async def test_the_funnel_of_an_agent_without_leads_is_empty(
    db_session: AsyncSession, agent: str
) -> None:
    """An agent with no leads gets a report with zeroes, not an error."""
    funnel = await PrioritizedLeadScoringService(db_session).get_agent_funnel(agent)

    assert funnel["total_leads"] == 0
    assert funnel["by_priority"] == {"hot": 0, "warm": 0, "cool": 0, "cold": 0}
    assert funnel["by_status"]["new"] == 0
    assert funnel["average_score"] == 0.0
