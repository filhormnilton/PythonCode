"""
Shared agent factory utilities.
Provides a common way to build LangChain agents with a given LLM and tool list.

Compatible with LangChain 1.x (uses create_agent / CompiledStateGraph).
"""
from __future__ import annotations

import logging
from typing import Any, List, Optional

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import BaseTool
from langgraph.prebuilt import create_react_agent

logger = logging.getLogger(__name__)


class AgentWrapper:
    """Thin wrapper around a LangChain 1.x compiled agent graph.

    Exposes an ``invoke({"input": ..., "chat_history": [...]})`` interface
    compatible with the orchestrator delegation pattern.
    """

    def __init__(self, graph: Any, agent_name: str):
        self._graph = graph
        self._name = agent_name

    def invoke(self, payload: dict) -> dict:
        """Run the agent on a single input.

        Args:
            payload: Dict with keys ``"input"`` (str) and optional
                     ``"chat_history"`` (list of LangChain messages).

        Returns:
            Dict with key ``"output"`` containing the agent's final response.
        """
        user_input: str = payload.get("input", "")
        history: list = payload.get("chat_history", [])

        messages = list(history) + [HumanMessage(content=user_input)]
        state = self._graph.invoke({"messages": messages})

        # The last AIMessage in the messages list is the final answer
        output_messages = state.get("messages", [])
        for msg in reversed(output_messages):
            if isinstance(msg, AIMessage):
                content = msg.content
                if isinstance(content, list):
                    # Tool-calling format: extract text parts
                    text_parts = [p.get("text", "") for p in content if isinstance(p, dict) and "text" in p]
                    return {"output": " ".join(text_parts) or str(content)}
                return {"output": str(content)}

        return {"output": ""}


def build_agent(
    llm: Any,
    tools: List[BaseTool],
    system_prompt: str,
    agent_name: str,
    max_iterations: int = 10,
    verbose: bool = False,
) -> AgentWrapper:
    """Create an AgentWrapper from an LLM, tool list, and system prompt.

    Args:
        llm: A LangChain chat model instance (e.g. ChatOpenAI).
        tools: List of LangChain tools available to this agent.
        system_prompt: System-level instruction that defines the agent persona.
        agent_name: Human-readable label (used only for logging).
        max_iterations: Maximum reasoning steps (passed to create_agent as
                        recursion_limit via recursion_limit on the graph).
        verbose: Whether to print debug information (unused in 1.x; kept for
                 API compatibility).

    Returns:
        AgentWrapper ready to invoke.
    """
    graph = create_react_agent(
        model=llm,
        tools=tools,
        prompt=system_prompt,
    )
    return AgentWrapper(graph, agent_name)
