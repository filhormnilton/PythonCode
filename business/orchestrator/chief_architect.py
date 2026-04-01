"""
Chief Business Architect & Orchestrator — "frysda" / "Negócios"

Implements a supervisor-style multi-agent orchestration pattern using LangChain.
The orchestrator analyses the user request, decides which specialist agent(s) to
invoke, and composes the final response.

Routing table
─────────────
MODE 1 – Engenharia de User Story  → JIRA + DOCS
MODE 2 – Auditoria Heurística      → JIRA + MIRO + SLIDES
MODE 3 – Discovery & Arquitetura   → WEB + PROCESS + ARCHITECT
MODE 4 – Gestão de Mudança em Massa→ JIRA + DOCS + PROCESS
MODE 5 – Orquestração Ad-hoc       → intelligent routing by demand
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool, tool
from langchain.agents import create_agent
from business.agents.base import AgentWrapper

from business.agents.architect_agent import create_architect_agent
from business.agents.docs_agent import create_docs_agent
from business.agents.jira_agent import create_jira_agent
from business.agents.miro_agent import create_miro_agent
from business.agents.process_agent import create_process_agent
from business.agents.slides_agent import create_slides_agent
from business.agents.web_agent import create_web_agent
from business.mcp.api_knowledge_base import KNOWLEDGE_BASE_TOOLS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Orchestrator system prompt (frysda persona)
# ---------------------------------------------------------------------------
_ORCHESTRATOR_SYSTEM_PROMPT = """\
# [SYSTEM_CONFIG: CHIEF_BUSINESS_ARCHITECT_&_ORCHESTRATOR_PHD]
# PERSONA_ID: "Negócios" | SENIORITY: PhD_Master_Level_30+ | ALIAS: "frysda"

## [CORE_IDENTITY_LOGIC]
- role: "Chief Requirements Architect, Strategic BA & Multi-Agent Orchestrator"
- mindset: ["Systems Thinking", "Risk Mitigation", "Strategic Alignment", "Zero Ambiguity"]
- communication_protocol: "EXECUTIVE_OBJECTIVE_ONLY"
- output_structure: "STRICT_TABULAR_DATA_PRIOR_TO_DISPATCH"

## [ORCHESTRATION_HELPER_REGISTRY]
helpers:
  1_DOCS:      scope="Word, PDF, TXT"               actions=[C,R,U,D]
  2_SLIDES:    scope="PowerPoint"                   actions=[C,R,U,D]
  3_ARCHITECT: scope="Draw.io Architecture"         actions=[C,R,U,D]
  4_JIRA:      scope="Jira Software Backlog"        actions=[Sync,Write,Update]
  5_WEB:       scope="Research & Extraction"        actions=[Browse,Search]
  6_PROCESS:   scope="Camunda Modeler BPMN"         actions=[C,R,U,D]
  7_MIRO:      scope="Brainstorming Boards"         actions=[C,R,U,D]

## [KNOWLEDGE_BASE]
- The orchestrator has DIRECT access to the local knowledge base (no helper needed).
- Use add_knowledge_entry to persist important findings, decisions, or reference material.
- Use search_knowledge_base before delegating to helpers to enrich context with prior knowledge.
- Use list_knowledge_entries to show the user what knowledge has been accumulated.
- Knowledge base is stored at: business_output/knowledge_base/

## [MEMORY]
- Conversation history is automatically maintained per session.
- For persistence across restarts, set COSMOS_ENDPOINT + COSMOS_KEY environment variables.
- The knowledge base provides cross-session, persistent domain memory.

## [EXECUTION_MODES]
| ID | Operation                     | Helpers Activated         |
|----|-------------------------------|---------------------------|
|  1 | Engenharia de User Story      | JIRA + DOCS               |
|  2 | Auditoria Heurística          | JIRA + MIRO + SLIDES      |
|  3 | Discovery & Arquitetura       | WEB + PROCESS + ARCHITECT |
|  4 | Gestão de Mudança em Massa    | JIRA + DOCS + PROCESS     |
|  5 | Orquestração Ad-hoc           | Intelligent routing        |

## [INTERACTION_RULES]
- Always present a brief execution plan (table format) before dispatching to helpers.
- After each helper completes, summarize results and ask if refinement is needed.
- Zero ambiguity: if the request is unclear, ask ONE clarifying question before proceeding.
- Loop options after each response: [1. Refinar Definição | 2. Despachar | 3. Stress Test]

You have access to tools that delegate work to each specialist agent AND to the knowledge base.
Use them according to the routing table above.
"""


# ---------------------------------------------------------------------------
# Delegate tools (wrap each agent as a tool for the orchestrator)
# ---------------------------------------------------------------------------

class BusinessOrchestrator:
    """Multi-agent orchestrator for the Business system."""

    def __init__(self, llm: Any):
        self._llm = llm
        self._agents: Dict[str, AgentWrapper] = {}
        self._executor: Optional[AgentWrapper] = None

    # ------------------------------------------------------------------
    # Lazy agent initialisation
    # ------------------------------------------------------------------

    def _get_agent(self, name: str) -> AgentWrapper:
        if name not in self._agents:
            factories = {
                "docs": create_docs_agent,
                "slides": create_slides_agent,
                "architect": create_architect_agent,
                "jira": create_jira_agent,
                "web": create_web_agent,
                "process": create_process_agent,
                "miro": create_miro_agent,
            }
            self._agents[name] = factories[name](self._llm)
        return self._agents[name]

    # ------------------------------------------------------------------
    # Build orchestrator tools (each tool delegates to a specialist)
    # ------------------------------------------------------------------

    def _build_tools(self) -> List[BaseTool]:
        orchestrator = self  # capture reference for closures

        def _invoke_agent(name: str, task: str) -> str:
            """Helper: invoke a named specialist agent and return its output."""
            result = orchestrator._get_agent(name).invoke({"input": task})
            output = result.get("output", "")
            if not output:
                logger.warning("[ORCHESTRATOR] %s agent returned empty output for task: %s", name.upper(), task[:80])
                return f"{name.upper()} agent returned no output. Please retry or rephrase the task."
            return output

        @tool
        def delegate_to_docs(task: str) -> str:
            """Delegate a document creation/editing task to the DOCS agent (Word, PDF, TXT).

            Args:
                task: Full task description for the DOCS agent.
            Returns:
                Agent response string.
            """
            logger.info("[ORCHESTRATOR] → DOCS: %s", task[:80])
            return _invoke_agent("docs", task)

        @tool
        def delegate_to_slides(task: str) -> str:
            """Delegate a presentation task to the SLIDES agent (PowerPoint).

            Args:
                task: Full task description for the SLIDES agent.
            Returns:
                Agent response string.
            """
            logger.info("[ORCHESTRATOR] → SLIDES: %s", task[:80])
            return _invoke_agent("slides", task)

        @tool
        def delegate_to_architect(task: str) -> str:
            """Delegate an architecture diagramming task to the ARCHITECT agent (Draw.io).

            Args:
                task: Full task description for the ARCHITECT agent.
            Returns:
                Agent response string.
            """
            logger.info("[ORCHESTRATOR] → ARCHITECT: %s", task[:80])
            return _invoke_agent("architect", task)

        @tool
        def delegate_to_jira(task: str) -> str:
            """Delegate a backlog management task to the JIRA agent.

            Args:
                task: Full task description for the JIRA agent.
            Returns:
                Agent response string.
            """
            logger.info("[ORCHESTRATOR] → JIRA: %s", task[:80])
            return _invoke_agent("jira", task)

        @tool
        def delegate_to_web(task: str) -> str:
            """Delegate a web research task to the WEB agent.

            Args:
                task: Full task description for the WEB agent.
            Returns:
                Agent response string.
            """
            logger.info("[ORCHESTRATOR] → WEB: %s", task[:80])
            return _invoke_agent("web", task)

        @tool
        def delegate_to_process(task: str) -> str:
            """Delegate a BPMN process modeling task to the PROCESS agent (Camunda).

            Args:
                task: Full task description for the PROCESS agent.
            Returns:
                Agent response string.
            """
            logger.info("[ORCHESTRATOR] → PROCESS: %s", task[:80])
            return _invoke_agent("process", task)

        @tool
        def delegate_to_miro(task: str) -> str:
            """Delegate a brainstorming/ideation task to the MIRO agent.

            Args:
                task: Full task description for the MIRO agent.
            Returns:
                Agent response string.
            """
            logger.info("[ORCHESTRATOR] → MIRO: %s", task[:80])
            return _invoke_agent("miro", task)

        return [
            delegate_to_docs,
            delegate_to_slides,
            delegate_to_architect,
            delegate_to_jira,
            delegate_to_web,
            delegate_to_process,
            delegate_to_miro,
            # Knowledge base tools are directly available to the orchestrator
            *KNOWLEDGE_BASE_TOOLS,
        ]

    # ------------------------------------------------------------------
    # Executor
    # ------------------------------------------------------------------

    def _build_executor(self) -> AgentWrapper:
        tools = self._build_tools()
        graph = create_agent(
            model=self._llm,
            tools=tools,
            system_prompt=_ORCHESTRATOR_SYSTEM_PROMPT,
        )
        return AgentWrapper(graph, "ORCHESTRATOR")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def invoke(self, user_input: str, chat_history: Optional[List] = None) -> str:
        """Process a user request through the multi-agent pipeline.

        Args:
            user_input: The user's request in natural language.
            chat_history: Optional list of previous messages for context.

        Returns:
            Orchestrator's final response string.
        """
        if self._executor is None:
            self._executor = self._build_executor()

        payload: Dict[str, Any] = {"input": user_input}
        if chat_history:
            payload["chat_history"] = chat_history

        result = self._executor.invoke(payload)
        return result.get("output", "")


def create_business_orchestrator(llm: Any) -> BusinessOrchestrator:
    """Factory function to create a BusinessOrchestrator instance.

    Args:
        llm: A LangChain-compatible chat model instance.

    Returns:
        Configured BusinessOrchestrator.
    """
    return BusinessOrchestrator(llm)
