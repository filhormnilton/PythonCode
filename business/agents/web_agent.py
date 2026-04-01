"""
Agent 5 — WEB
Responsible for browsing the internet, executing searches, and extracting
information from web pages to support research and discovery tasks.
"""
from typing import Any

from business.agents.base import build_agent
from business.mcp.api_web import WEB_TOOLS

_SYSTEM_PROMPT = """\
You are the WEB Agent — a specialist in internet research and information extraction.
Your responsibilities:
- Search the web for relevant, up-to-date information using web_search.
- Fetch full page content with fetch_webpage for in-depth analysis.
- Extract links from pages to discover related resources.
- Synthesize findings into clear, cited summaries.
- Never fabricate URLs or content — only report what the tools return.
- Always cite the source URL for every piece of information retrieved.
"""


def create_web_agent(llm: Any):
    """Instantiate the WEB agent.

    Args:
        llm: A LangChain chat model instance.

    Returns:
        Configured AgentExecutor for web research operations.
    """
    return build_agent(
        llm=llm,
        tools=WEB_TOOLS,
        system_prompt=_SYSTEM_PROMPT,
        agent_name="WEB",
    )
