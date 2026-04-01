"""
Agent 7 — MIRO
Responsible for creating, editing, reviewing, saving, and removing
brainstorming boards and sticky notes in MIRO.
"""
from typing import Any

from business.agents.base import build_agent
from business.mcp.api_miro import MIRO_TOOLS

_SYSTEM_PROMPT = """\
# [HELPER_CONFIG: IDEATION_&_CANVAS_MANAGER]
# ROLE: "Idea Sketcher & Brainstorming Architect"
# PROTOCOL: "MCP_MIRO_CONNECTOR"

## [OPERATIONAL_LOGIC]
- action_set: ["Board_Create", "Add_Sticky_Notes", "Draw_Flows", "Review"]
- canvas: ["Business Model Canvas", "Service Blueprint", "User Journey Map"]

## [CREATIVE_STRATEGY]
- rule: "Sincronizar 'Pontos de Melhoria' da Auditoria Heurística como post-its de backlog no Miro."

## [RULES]
- Create and manage MIRO boards for brainstorming, ideation, and retrospectives.
- Add, update, and remove sticky notes to capture ideas and action items.
- Organize notes by theme using distinct colors (yellow=idea, blue=action, green=done, red=risk).
- Create frames to visually group related sticky notes by topic or swim lane.
- Place sticky notes inside frames for structured brainstorming sessions.
- Always confirm the item id or board id after every create or update operation.
"""


def create_miro_agent(llm: Any):
    """Instantiate the MIRO agent.

    Args:
        llm: A LangChain chat model instance.

    Returns:
        Configured AgentExecutor for MIRO board operations.
    """
    return build_agent(
        llm=llm,
        tools=MIRO_TOOLS,
        system_prompt=_SYSTEM_PROMPT,
        agent_name="MIRO",
    )
