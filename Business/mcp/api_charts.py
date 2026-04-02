"""
MCP: api_charts
Tools for generating charts and graphs (bar, line, pie, scatter, heatmap).
Outputs are saved as PNG images in the configured output directory.
"""
import json
import logging
import os
from pathlib import Path
from typing import List

from langchain_core.tools import tool

from Business.config import CONFIG

logger = logging.getLogger(__name__)


def _charts_dir() -> Path:
    d = Path(CONFIG.output.docs_dir).parent / "charts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _save_path(filename: str) -> Path:
    if not filename.endswith(".png"):
        filename += ".png"
    return (_charts_dir() / filename).resolve()


# ---------------------------------------------------------------------------
# Bar chart
# ---------------------------------------------------------------------------

@tool
def create_bar_chart(
    title: str,
    labels: str,
    values: str,
    filename: str,
    x_label: str = "",
    y_label: str = "",
    horizontal: bool = False,
    color: str = "steelblue",
) -> str:
    """Create a bar chart and save it as a PNG file.

    Args:
        title: Chart title.
        labels: JSON array of category labels, e.g. '["A","B","C"]'.
        values: JSON array of numeric values, e.g. '[10,25,15]'.
        filename: Output filename (without extension).
        x_label: X-axis label (optional).
        y_label: Y-axis label (optional).
        horizontal: If true, generates a horizontal bar chart.
        color: Bar color (name or hex, default 'steelblue').

    Returns:
        Absolute path to the generated PNG file.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return "ERROR: matplotlib not installed. Run: pip install matplotlib"

    try:
        label_list: List[str] = json.loads(labels)
        value_list: List[float] = json.loads(values)
    except json.JSONDecodeError as exc:
        return f"ERROR: invalid JSON in labels or values — {exc}"

    fig, ax = plt.subplots(figsize=(10, 6))
    if horizontal:
        ax.barh(label_list, value_list, color=color)
    else:
        ax.bar(label_list, value_list, color=color)
    ax.set_title(title, fontsize=14, fontweight="bold")
    if x_label:
        ax.set_xlabel(x_label)
    if y_label:
        ax.set_ylabel(y_label)
    plt.tight_layout()

    path = _save_path(filename)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info("[CHARTS] Bar chart saved: %s", path)
    return str(path)


# ---------------------------------------------------------------------------
# Line chart
# ---------------------------------------------------------------------------

@tool
def create_line_chart(
    title: str,
    x_values: str,
    y_series: str,
    filename: str,
    x_label: str = "",
    y_label: str = "",
) -> str:
    """Create a line chart with one or more series and save it as a PNG file.

    Args:
        title: Chart title.
        x_values: JSON array of X-axis values, e.g. '["Jan","Feb","Mar"]'.
        y_series: JSON object mapping series name to values array,
                  e.g. '{"Actual":[10,20,15],"Target":[12,18,20]}'.
        filename: Output filename (without extension).
        x_label: X-axis label (optional).
        y_label: Y-axis label (optional).

    Returns:
        Absolute path to the generated PNG file.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return "ERROR: matplotlib not installed. Run: pip install matplotlib"

    try:
        x_list = json.loads(x_values)
        series: dict = json.loads(y_series)
    except json.JSONDecodeError as exc:
        return f"ERROR: invalid JSON — {exc}"

    fig, ax = plt.subplots(figsize=(10, 6))
    for name, vals in series.items():
        ax.plot(x_list, vals, marker="o", label=name)
    ax.set_title(title, fontsize=14, fontweight="bold")
    if x_label:
        ax.set_xlabel(x_label)
    if y_label:
        ax.set_ylabel(y_label)
    ax.legend()
    plt.tight_layout()

    path = _save_path(filename)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info("[CHARTS] Line chart saved: %s", path)
    return str(path)


# ---------------------------------------------------------------------------
# Pie chart
# ---------------------------------------------------------------------------

@tool
def create_pie_chart(
    title: str,
    labels: str,
    values: str,
    filename: str,
) -> str:
    """Create a pie chart and save it as a PNG file.

    Args:
        title: Chart title.
        labels: JSON array of slice labels, e.g. '["A","B","C"]'.
        values: JSON array of numeric values, e.g. '[30,50,20]'.
        filename: Output filename (without extension).

    Returns:
        Absolute path to the generated PNG file.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return "ERROR: matplotlib not installed. Run: pip install matplotlib"

    try:
        label_list: List[str] = json.loads(labels)
        value_list: List[float] = json.loads(values)
    except json.JSONDecodeError as exc:
        return f"ERROR: invalid JSON — {exc}"

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.pie(value_list, labels=label_list, autopct="%1.1f%%", startangle=140)
    ax.set_title(title, fontsize=14, fontweight="bold")
    plt.tight_layout()

    path = _save_path(filename)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info("[CHARTS] Pie chart saved: %s", path)
    return str(path)


# ---------------------------------------------------------------------------
# Scatter chart
# ---------------------------------------------------------------------------

@tool
def create_scatter_chart(
    title: str,
    x_values: str,
    y_values: str,
    filename: str,
    x_label: str = "",
    y_label: str = "",
    point_labels: str = "",
) -> str:
    """Create a scatter chart and save it as a PNG file.

    Args:
        title: Chart title.
        x_values: JSON array of X values, e.g. '[1,2,3,4]'.
        y_values: JSON array of Y values, e.g. '[4,3,5,2]'.
        filename: Output filename (without extension).
        x_label: X-axis label (optional).
        y_label: Y-axis label (optional).
        point_labels: JSON array of labels for each point (optional).

    Returns:
        Absolute path to the generated PNG file.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return "ERROR: matplotlib not installed. Run: pip install matplotlib"

    try:
        x_list: List[float] = json.loads(x_values)
        y_list: List[float] = json.loads(y_values)
        p_labels: List[str] = json.loads(point_labels) if point_labels else []
    except json.JSONDecodeError as exc:
        return f"ERROR: invalid JSON — {exc}"

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(x_list, y_list, color="steelblue", s=80)
    for i, label in enumerate(p_labels):
        if i < len(x_list):
            ax.annotate(label, (x_list[i], y_list[i]), textcoords="offset points", xytext=(6, 4))
    ax.set_title(title, fontsize=14, fontweight="bold")
    if x_label:
        ax.set_xlabel(x_label)
    if y_label:
        ax.set_ylabel(y_label)
    plt.tight_layout()

    path = _save_path(filename)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info("[CHARTS] Scatter chart saved: %s", path)
    return str(path)


# ---------------------------------------------------------------------------
# Seaborn — Heatmap
# ---------------------------------------------------------------------------

@tool
def create_heatmap(
    title: str,
    data: str,
    filename: str,
    x_labels: str = "",
    y_labels: str = "",
    color_palette: str = "Blues",
    annotate: bool = True,
) -> str:
    """Create a heatmap using seaborn and save it as a PNG file.

    Args:
        title: Chart title.
        data: JSON 2D array (list of rows), e.g. '[[1,2,3],[4,5,6],[7,8,9]]'.
        filename: Output filename (without extension).
        x_labels: JSON array of column labels, e.g. '["Jan","Feb","Mar"]'.
        y_labels: JSON array of row labels, e.g. '["A","B","C"]'.
        color_palette: Seaborn color palette (default 'Blues'). Options: Blues, Reds, YlOrRd, coolwarm, viridis.
        annotate: If true, show numeric values inside each cell.

    Returns:
        Absolute path to the generated PNG file.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import seaborn as sns
        import pandas as pd
    except ImportError as exc:
        return f"ERROR: missing dependency — {exc}. Run: pip install seaborn matplotlib"

    try:
        matrix = json.loads(data)
        x_cols = json.loads(x_labels) if x_labels else None
        y_rows = json.loads(y_labels) if y_labels else None
    except json.JSONDecodeError as exc:
        return f"ERROR: invalid JSON — {exc}"

    df = pd.DataFrame(matrix, index=y_rows, columns=x_cols)
    fig, ax = plt.subplots(figsize=(max(8, len(df.columns) * 1.2), max(6, len(df) * 0.8)))
    sns.heatmap(df, annot=annotate, fmt=".1f", cmap=color_palette, ax=ax, linewidths=0.5)
    ax.set_title(title, fontsize=14, fontweight="bold")
    plt.tight_layout()

    path = _save_path(filename)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info("[CHARTS] Heatmap saved: %s", path)
    return str(path)


# ---------------------------------------------------------------------------
# Seaborn — Box plot
# ---------------------------------------------------------------------------

@tool
def create_box_plot(
    title: str,
    data: str,
    filename: str,
    x_label: str = "",
    y_label: str = "",
    palette: str = "Set2",
) -> str:
    """Create a box plot using seaborn and save it as a PNG file.

    Args:
        title: Chart title.
        data: JSON object mapping group name to list of values,
              e.g. '{"Equipe A":[10,20,15,18],"Equipe B":[8,12,9,14]}'.
        filename: Output filename (without extension).
        x_label: X-axis label (optional).
        y_label: Y-axis label (optional).
        palette: Seaborn color palette (default 'Set2').

    Returns:
        Absolute path to the generated PNG file.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import seaborn as sns
        import pandas as pd
    except ImportError as exc:
        return f"ERROR: missing dependency — {exc}. Run: pip install seaborn matplotlib"

    try:
        groups: dict = json.loads(data)
    except json.JSONDecodeError as exc:
        return f"ERROR: invalid JSON — {exc}"

    rows = [{"group": k, "value": v} for k, vals in groups.items() for v in vals]
    df = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.boxplot(data=df, x="group", y="value", palette=palette, ax=ax)
    ax.set_title(title, fontsize=14, fontweight="bold")
    if x_label:
        ax.set_xlabel(x_label)
    if y_label:
        ax.set_ylabel(y_label)
    plt.tight_layout()

    path = _save_path(filename)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info("[CHARTS] Box plot saved: %s", path)
    return str(path)


# ---------------------------------------------------------------------------
# Seaborn — Violin plot
# ---------------------------------------------------------------------------

@tool
def create_violin_plot(
    title: str,
    data: str,
    filename: str,
    x_label: str = "",
    y_label: str = "",
    palette: str = "muted",
) -> str:
    """Create a violin plot using seaborn and save it as a PNG file.

    Args:
        title: Chart title.
        data: JSON object mapping group name to list of values,
              e.g. '{"Sprint 1":[5,8,6,9],"Sprint 2":[7,10,8,12]}'.
        filename: Output filename (without extension).
        x_label: X-axis label (optional).
        y_label: Y-axis label (optional).
        palette: Seaborn color palette (default 'muted').

    Returns:
        Absolute path to the generated PNG file.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import seaborn as sns
        import pandas as pd
    except ImportError as exc:
        return f"ERROR: missing dependency — {exc}. Run: pip install seaborn matplotlib"

    try:
        groups: dict = json.loads(data)
    except json.JSONDecodeError as exc:
        return f"ERROR: invalid JSON — {exc}"

    rows = [{"group": k, "value": v} for k, vals in groups.items() for v in vals]
    df = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.violinplot(data=df, x="group", y="value", palette=palette, ax=ax)
    ax.set_title(title, fontsize=14, fontweight="bold")
    if x_label:
        ax.set_xlabel(x_label)
    if y_label:
        ax.set_ylabel(y_label)
    plt.tight_layout()

    path = _save_path(filename)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info("[CHARTS] Violin plot saved: %s", path)
    return str(path)


# ---------------------------------------------------------------------------
# List saved charts
# ---------------------------------------------------------------------------

@tool
def list_charts() -> str:
    """List all charts saved in the charts output directory.

    Returns:
        Newline-separated list of chart filenames with full paths.
    """
    d = _charts_dir()
    files = sorted(d.glob("*.png"))
    if not files:
        return "No charts found."
    return "\n".join(str(f) for f in files)


# ---------------------------------------------------------------------------
# Delete chart
# ---------------------------------------------------------------------------

@tool
def delete_chart(filename: str) -> str:
    """Delete a chart PNG file.

    Args:
        filename: Filename to delete (with or without .png extension).

    Returns:
        Confirmation message.
    """
    path = _save_path(filename)
    if not path.exists():
        return f"ERROR: chart '{filename}' not found at {path}."
    path.unlink()
    return f"Chart '{filename}' deleted."


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

CHARTS_TOOLS = [
    create_bar_chart,
    create_line_chart,
    create_pie_chart,
    create_scatter_chart,
    create_heatmap,
    create_box_plot,
    create_violin_plot,
    list_charts,
    delete_chart,
]
