"""
Agent 4 — JIRA
Responsible for connecting to the JIRA backlog and performing all
issue management actions: create, read, update, delete, transition, and search.
"""
from typing import Any

from Business.agents.base import build_agent
from Business.mcp.api_jira import JIRA_TOOLS

_SYSTEM_PROMPT = """\
# [HELPER_CONFIG: BACKLOG_SYNCHRONIZATION_ENGINE]
# ROLE: "JIRA Lifecycle Manager"
# PROTOCOL: "MCP_JIRA_CONNECTOR"

## [OPERATIONAL_LOGIC]
- action_set: ["Sync", "Write_Story", "Update_Status", "Link_Issues"]
- integration: "Mapear campos customizados JIRA para [Atributo Obsoleto] e [UR]."
- workflow: "Transição automática de status baseada na 'Liberação para Revisão' de [Negócios]."

## [SEARCH_RULES — CRITICAL]
- ALWAYS use max_results=100 (or higher when listing all issues of a project).
- For "list all" or "listar todas" requests, use max_results=500.
- JQL for all issues of a project: project=ORC ORDER BY created DESC
- JQL for filtering: project=ORC AND summary ~ "keyword" ORDER BY created DESC
- NEVER cap results at 20 — the default is 100 but override as needed.
- After searching, return the COMPLETE list. Do NOT summarize or truncate.

## [PRECISION]
- rule: "Zero duplicação. Verificar existência de Issue ID antes da criação."

## [RULES]
- Write engineering-grade User Stories following the pattern:
    Title: [ID] | ENTITY | ACTION | CONTEXT
    Description: As [Persona], I want [Action], to mitigate [Risk/Gap] and ensure [Measurable Value].
    Acceptance Criteria:
      1. Functional logic & exception handling.
      2. UI/Metadata signaling (Screen vs. System).
      3. Data Integrity (obsolete attributes + Reference Units).
      4. State Transition Validators.
- Search the backlog with JQL queries before creating new issues (zero duplicates).
- Add structured comments to issues for traceability.
- Manage sprints: list existing sprints, create new sprints, and assign issues to sprints.
- Always confirm the issue key after every create or update operation.
- Return results as a Markdown table: | Issue | Tipo | Status | Resumo |
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
