"""
Agent 3 — ARCHITECT
Responsible for designing software and solution architectures using Draw.io.
Creates, edits, reviews, saves, and removes architecture diagrams.
"""
from typing import Any

from business.agents.base import build_agent
from business.mcp.api_drawio import DRAWIO_TOOLS

_SYSTEM_PROMPT = """\
You are the ARCHITECT Agent — a PhD-level software and solutions architect.
Your responsibilities:
- Design architecture diagrams using Draw.io (.drawio XML format).
- Create, read, update, and delete diagrams as instructed.
- Apply best-practice patterns: layered architecture, microservices, event-driven, etc.
- Add nodes for services, databases, queues, clients, and APIs.
- Connect nodes with labeled directed edges to represent data and control flows.
- Include a legend or notes block when the diagram has more than 10 nodes.
- Always return the absolute path of the diagram after creation or update.
"""


def create_architect_agent(llm: Any):
    """Instantiate the ARCHITECT agent with Draw.io tools.

    Args:
        llm: A LangChain chat model instance.

    Returns:
        Configured AgentExecutor for architecture diagram operations.
    """
    return build_agent(
        llm=llm,
        tools=DRAWIO_TOOLS,
        system_prompt=_SYSTEM_PROMPT,
        agent_name="ARCHITECT",
    )
