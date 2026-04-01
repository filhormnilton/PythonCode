"""
Agent 7 — MIRO
Responsible for creating, editing, reviewing, saving, and removing
brainstorming boards and sticky notes in MIRO.
"""
from typing import Any

from business.agents.base import build_agent
from business.mcp.api_miro import MIRO_TOOLS

_SYSTEM_PROMPT = """\
You are the MIRO Agent — a facilitation and visual thinking specialist.
Your responsibilities:
- Create and manage MIRO boards for brainstorming, ideation, and retrospectives.
- Add, update, and remove sticky notes to capture ideas and action items.
- Organize notes by theme using distinct colors (yellow=idea, blue=action, green=done, red=risk).
- List board items to provide status updates.
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
