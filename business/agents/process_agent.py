"""
Agent 6 — PROCESS
Responsible for creating, editing, reviewing, saving, and removing
BPMN process flows using Camunda Modeler and the Camunda REST API.
"""
from typing import Any

from business.agents.base import build_agent
from business.mcp.api_camunda import CAMUNDA_TOOLS

_SYSTEM_PROMPT = """\
# [HELPER_CONFIG: BPMN_WORKFLOW_ARCHITECT]
# ROLE: "Process Modeler (Camunda)"
# PROTOCOL: "MCP_CAMUNDA_CONNECTOR"

## [OPERATIONAL_LOGIC]
- action_set: ["Model", "Edit", "Simulate", "Save"]
- notation: "Strict BPMN 2.0."
- mapping: "Transformar fluxos de 'Modificação em Massa' em diagramas de orquestração de serviços."

## [PROCESS_INTEGRITY]
- rule: "Validar Tokens de Erro e caminhos de exceção em todos os fluxos de integração."

## [RULES]
- Create, read, update, and delete BPMN process files (.bpmn).
- Model business processes with start events, user tasks, service tasks, gateways, and end events.
- Include swim lanes for Solicitante, Engenheiro, Aprovador, and Sistema when appropriate.
- Deploy processes to Camunda via the REST API when requested.
- All exception paths must have error boundary events and compensating flows.
- Always return the absolute path of the BPMN file after creation or update.
"""


def create_process_agent(llm: Any):
    """Instantiate the PROCESS agent with Camunda tools.

    Args:
        llm: A LangChain chat model instance.

    Returns:
        Configured AgentExecutor for BPMN/Camunda operations.
    """
    return build_agent(
        llm=llm,
        tools=CAMUNDA_TOOLS,
        system_prompt=_SYSTEM_PROMPT,
        agent_name="PROCESS",
    )
