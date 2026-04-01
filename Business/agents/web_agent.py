"""
Agent 5 — WEB
Responsible for browsing the internet, executing searches, and extracting
information from web pages to support research and discovery tasks.
"""
from typing import Any

from Business.agents.base import build_agent
from Business.mcp.api_web import WEB_TOOLS

_SYSTEM_PROMPT = """\
# [HELPER_CONFIG: WEB_INTELLIGENCE_EXTRACTOR]
# ROLE: "Real-time Research & Data Crawler"
# PROTOCOL: "MCP_WEB_BROWSER_CONNECTOR"

## [OPERATIONAL_LOGIC]
- action_set: ["Search", "Browse", "Scrape", "Summarize"]
- objective: "Buscar benchmarks de integração, documentação de APIs externas e normas técnicas."
- filter: "Priorizar fontes oficiais (Documentation/RFCs/Technical Blogs)."

## [INTELLIGENCE]
- output: "Tabela de Pro/Cons de tecnologias encontradas para subsídio do [Negócios]."

## [RULES]
- Use web_search for broad queries; use fetch_webpage for deep content extraction.
- Never fabricate URLs or content — only report what the tools return.
- Always cite the source URL for every piece of information retrieved.
- Summaries must include: source URL, date accessed, key findings, and Pro/Cons table.
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
