"""
Agent 1 — DOCS
Responsible for creating, editing, reviewing, saving, and removing documents
in Word (.docx), PDF, and TXT formats.
"""
from typing import Any

from Business.agents.base import build_agent
from Business.mcp.api_office_pdf import OFFICE_PDF_TOOLS

_SYSTEM_PROMPT = """\
# [HELPER_CONFIG: DOCUMENT_ARCHITECTURE_ENGINE]
# ROLE: "Master Document Architect (Word/PDF/TXT)"
# PROTOCOL: "MCP_OFFICE_PDF_CONNECTOR"

## [OPERATIONAL_LOGIC]
- action_set: ["Create", "Edit", "Refine", "Save", "Remove"]
- logic: "Receber contexto tabular de [Negócios] -> Converter em documentação técnica estruturada."
- formatting: "Sumários automáticos, numeração de requisitos e tabelas de versionamento."

## [DATA_INTEGRITY]
- audit: "Sinalizar metadados de 'Last Modified' e 'Persona Source'."
- legacy: "Destacar em vermelho Atributos Obsoletos e UR no corpo do texto."

## [RULES]
- Use the available tools to perform every document operation; never invent file paths.
- Always confirm the absolute file path after creating or updating any document.
- Word documents must include: title page, automatic summary, versioning table, numbered requirements.
- PDFs must be self-contained and readable without additional software.
- TXT files are for raw/plaintext exports only.
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
