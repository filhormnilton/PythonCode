"""
Agent 2 — SLIDES
Responsible for creating, editing, reviewing, saving, and removing
PowerPoint presentations.
"""
from typing import Any

from business.agents.base import build_agent
from business.mcp.api_powerpoint import POWERPOINT_TOOLS

_SYSTEM_PROMPT = """\
You are the SLIDES Agent — a specialist in presentation design and management.
Your responsibilities:
- Create, read, update, and delete PowerPoint (.pptx) presentations.
- Design slide content that is clear, concise, and visually structured.
- Add, update, or remove individual slides as requested.
- Follow storytelling best practices: one idea per slide, strong title, supporting body.
- Always confirm the file path after creating or updating a presentation.
"""


def create_slides_agent(llm: Any):
    """Instantiate the SLIDES agent with PowerPoint tools.

    Args:
        llm: A LangChain chat model instance.

    Returns:
        Configured AgentExecutor for presentation operations.
    """
    return build_agent(
        llm=llm,
        tools=POWERPOINT_TOOLS,
        system_prompt=_SYSTEM_PROMPT,
        agent_name="SLIDES",
    )
