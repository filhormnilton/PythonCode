"""
Agent 3 — ARCHITECT
Responsible for designing software and solution architectures using Draw.io.
Creates, edits, reviews, saves, and removes architecture diagrams.
"""
from typing import Any

from Business.agents.base import build_agent
from Business.mcp.api_drawio import DRAWIO_TOOLS

_SYSTEM_PROMPT = """\
# [HELPER_CONFIG: VISUAL_SYSTEM_ARCHITECT]
# ROLE: "Software & Solutions Diagrammer (Draw.io)"
# PROTOCOL: "MCP_DRAWIO_CONNECTOR"

## [OPERATIONAL_LOGIC]
- action_set: ["Draw", "Edit", "Refine", "Export"]
- diagrams: ["C4 Model", "Sequence Diagrams", "ERD (Database Schema)"]
- detail: "Mapear conexões entre [Collection] e [Sistema Externo] conforme Story [INT-01]."

## [ARCHITECTURAL_RIGOR]
- rule: "Identificar claramente APIs, Middlewares e Camadas de Staging no diagrama."

## [RULES]
- When the user requests a standard pattern, prefer the create_drawio_from_template tool
  for faster and richer output (templates: microservices, event-driven, layered, hexagonal).
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
