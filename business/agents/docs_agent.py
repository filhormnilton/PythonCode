"""
Agent 1 — DOCS
Responsible for creating, editing, reviewing, saving, and removing documents
in Word (.docx), PDF, and TXT formats.
"""
from typing import Any

from business.agents.base import build_agent
from business.mcp.api_office_pdf import OFFICE_PDF_TOOLS

_SYSTEM_PROMPT = """\
You are the DOCS Agent — a specialist in document management.
Your responsibilities:
- Create, read, update, and delete Word (.docx), PDF, and TXT documents.
- Format content professionally and consistently.
- Ensure accuracy, completeness, and clear structure.
- Always confirm the file path after creating or updating a document.
- Use the available tools to perform every document operation; never invent file paths.
"""


def create_docs_agent(llm: Any):
    """Instantiate the DOCS agent with Office/PDF tools.

    Args:
        llm: A LangChain chat model instance.

    Returns:
        Configured AgentExecutor for document operations.
    """
    return build_agent(
        llm=llm,
        tools=OFFICE_PDF_TOOLS,
        system_prompt=_SYSTEM_PROMPT,
        agent_name="DOCS",
    )
