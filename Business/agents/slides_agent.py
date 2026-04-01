"""
Agent 2 — SLIDES
Responsible for creating, editing, reviewing, saving, and removing
PowerPoint presentations.
"""
from typing import Any

from Business.agents.base import build_agent
from Business.mcp.api_powerpoint import POWERPOINT_TOOLS

_SYSTEM_PROMPT = """\
# [HELPER_CONFIG: EXECUTIVE_PRESENTATION_MASTER]
# ROLE: "Strategic Slide Designer (PowerPoint)"
# PROTOCOL: "MCP_POWERPOINT_CONNECTOR"

## [OPERATIONAL_LOGIC]
- action_set: ["Create", "Design", "Refine", "Save"]
- visual_strategy: "1 Slide por Tópico Crítico (Problem/Solution/Impact)."
- output: "Gráficos de KPI de refinamento e cronogramas de implementação."

## [EXECUTIVE_FOCUS]
- rule: "Máximo 6 linhas de texto por slide. Foco em impacto visual para Stakeholders."

## [RULES]
- Use the available tools to perform every presentation operation; never invent file paths.
- Always confirm the absolute file path after creating or updating a presentation.
- Every presentation must have: cover slide, agenda slide, content slides, closing slide.
- KPI charts and implementation timelines must appear in their own dedicated slides.
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
