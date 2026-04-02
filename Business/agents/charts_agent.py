"""
Agent 8 — CHARTS
Responsible for creating bar, line, pie, and scatter charts as PNG files.
"""
from typing import Any

from Business.agents.base import build_agent
from Business.mcp.api_charts import CHARTS_TOOLS

_SYSTEM_PROMPT = """\
# [HELPER_CONFIG: DATA_VISUALIZATION_ENGINE]
# ROLE: "Chart & Graph Generator"
# PROTOCOL: "MCP_CHARTS_CONNECTOR"

## [OPERATIONAL_LOGIC]
- action_set: ["Create", "List", "Delete"]
- supported_types: ["bar", "horizontal bar", "line", "pie", "scatter", "heatmap", "box plot", "violin plot"]
- output_format: "PNG (150 DPI) saved to business_output/charts/"

## [RULES]
- Always pass labels and values as valid JSON arrays in the tool parameters.
- For line charts with multiple series, pass y_series as a JSON object: {"series_name": [values]}.
- For heatmap, box plot, and violin plot, use the seaborn-based tools.
- Choose chart type based on data semantics:
    * bar/horizontal bar → comparisons between categories
    * line → trends over time
    * pie → proportions of a whole
    * scatter → correlations between two numeric variables
    * heatmap → matrix/correlation data (seaborn)
    * box plot → distribution and outliers per group (seaborn)
    * violin plot → distribution shape per group (seaborn)
- Always confirm the full file path returned by the tool.
- Filenames must be snake_case without spaces.
"""


def create_charts_agent(llm: Any):
    """Instantiate the CHARTS agent with chart generation tools.

    Args:
        llm: A LangChain chat model instance.

    Returns:
        Configured AgentWrapper for chart operations.
    """
    return build_agent(
        llm=llm,
        tools=CHARTS_TOOLS,
        system_prompt=_SYSTEM_PROMPT,
        agent_name="CHARTS",
    )
