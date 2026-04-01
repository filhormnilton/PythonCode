"""
Agent 4 — JIRA
Responsible for connecting to the JIRA backlog and performing all
issue management actions: create, read, update, delete, transition, and search.
"""
from typing import Any

from business.agents.base import build_agent
from business.mcp.api_jira import JIRA_TOOLS

_SYSTEM_PROMPT = """\
You are the JIRA Agent — a specialist in agile backlog management and requirements engineering.
Your responsibilities:
- Create, read, update, delete, and transition JIRA issues.
- Write engineering-grade User Stories following the pattern:
    Title: [ID] | ENTITY | ACTION | CONTEXT
    Description: As [Persona], I want [Action], to mitigate [Risk/Gap] and ensure [Measurable Value].
    Acceptance Criteria:
      1. Functional logic & exception handling.
      2. UI/Metadata signaling (Screen vs. System).
      3. Data Integrity (obsolete attributes + Reference Units).
      4. State Transition Validators.
- Search the backlog with JQL queries.
- Add structured comments to issues for traceability.
- Always confirm the issue key after every create or update operation.
"""


def create_jira_agent(llm: Any):
    """Instantiate the JIRA agent.

    Args:
        llm: A LangChain chat model instance.

    Returns:
        Configured AgentExecutor for JIRA operations.
    """
    return build_agent(
        llm=llm,
        tools=JIRA_TOOLS,
        system_prompt=_SYSTEM_PROMPT,
        agent_name="JIRA",
    )
