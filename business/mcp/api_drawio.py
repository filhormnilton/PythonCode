"""
MCP: api_drawio
Tools for creating, reading, updating, and deleting Draw.io (.drawio / .xml) diagrams.
Draw.io uses XML internally; these tools manipulate the XML representation directly.
"""
import xml.etree.ElementTree as ET
from pathlib import Path

from langchain_core.tools import tool

from business.config import CONFIG

_DRAWIO_HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="app.diagrams.net" version="21.0.0">
  <diagram name="{name}">
    <mxGraphModel dx="1422" dy="762" grid="1" gridSize="10" guides="1"
                  tooltips="1" connect="1" arrows="1" fold="1" page="1"
                  pageScale="1" pageWidth="1169" pageHeight="827"
                  math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        {cells}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>"""


def _ensure_dir(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)


@tool
def create_drawio_diagram(filename: str, diagram_name: str, description: str) -> str:
    """Create a new Draw.io diagram file with a starter layout derived from the description.

    The tool generates a simple rectangular node for each line in the description.

    Args:
        filename: Name of the file (without extension).
        diagram_name: Human-readable diagram title embedded in the XML.
        description: Newline-separated list of component names/labels to add as nodes.

    Returns:
        Absolute path of the created .drawio file.
    """
    _ensure_dir(CONFIG.output.diagrams_dir)
    path = CONFIG.output.diagrams_dir / f"{filename}.drawio"

    cells = []
    y_offset = 40
    for idx, label in enumerate(description.strip().splitlines(), start=2):
        label = label.strip()
        if not label:
            continue
        cell_id = str(idx)
        cells.append(
            f'<mxCell id="{cell_id}" value="{label}" style="rounded=1;whiteSpace=wrap;html=1;" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="40" y="{y_offset}" width="200" height="60" as="geometry"/>'
            f"</mxCell>"
        )
        y_offset += 80

    xml_content = _DRAWIO_HEADER.format(name=diagram_name, cells="\n        ".join(cells))
    path.write_text(xml_content, encoding="utf-8")
    return str(path)


@tool
def read_drawio_diagram(filepath: str) -> str:
    """Read a Draw.io file and return its raw XML content.

    Args:
        filepath: Absolute or relative path to the .drawio file.

    Returns:
        Raw XML string.
    """
    return Path(filepath).read_text(encoding="utf-8")


@tool
def add_node_to_diagram(filepath: str, node_label: str, x: int, y: int, width: int, height: int) -> str:
    """Add a rectangular node to an existing Draw.io diagram.

    Args:
        filepath: Absolute or relative path to the .drawio file.
        node_label: Text label for the new node.
        x: X coordinate.
        y: Y coordinate.
        width: Node width in pixels.
        height: Node height in pixels.

    Returns:
        Confirmation message with the new node id.
    """
    content = Path(filepath).read_text(encoding="utf-8")
    tree = ET.fromstring(content)

    root_elem = tree.find(".//root")
    if root_elem is None:
        return "ERROR: Could not locate <root> element in the diagram XML."

    existing_ids = [int(c.get("id", 0)) for c in root_elem if c.get("id", "").isdigit()]
    new_id = str(max(existing_ids, default=1) + 1)

    new_cell = ET.SubElement(root_elem, "mxCell")
    new_cell.set("id", new_id)
    new_cell.set("value", node_label)
    new_cell.set("style", "rounded=1;whiteSpace=wrap;html=1;")
    new_cell.set("vertex", "1")
    new_cell.set("parent", "1")
    geom = ET.SubElement(new_cell, "mxGeometry")
    geom.set("x", str(x))
    geom.set("y", str(y))
    geom.set("width", str(width))
    geom.set("height", str(height))
    geom.set("as", "geometry")

    Path(filepath).write_text(ET.tostring(tree, encoding="unicode"), encoding="utf-8")
    return f"Node '{node_label}' added with id={new_id}."


@tool
def add_edge_to_diagram(filepath: str, source_id: str, target_id: str, label: str) -> str:
    """Add a directed edge between two nodes in a Draw.io diagram.

    Args:
        filepath: Absolute or relative path to the .drawio file.
        source_id: Cell id of the source node.
        target_id: Cell id of the target node.
        label: Optional label for the edge.

    Returns:
        Confirmation message.
    """
    content = Path(filepath).read_text(encoding="utf-8")
    tree = ET.fromstring(content)

    root_elem = tree.find(".//root")
    if root_elem is None:
        return "ERROR: Could not locate <root> element."

    existing_ids = [int(c.get("id", 0)) for c in root_elem if c.get("id", "").isdigit()]
    new_id = str(max(existing_ids, default=1) + 1)

    edge = ET.SubElement(root_elem, "mxCell")
    edge.set("id", new_id)
    edge.set("value", label)
    edge.set("style", "edgeStyle=orthogonalEdgeStyle;")
    edge.set("edge", "1")
    edge.set("source", source_id)
    edge.set("target", target_id)
    edge.set("parent", "1")
    geom = ET.SubElement(edge, "mxGeometry")
    geom.set("relative", "1")
    geom.set("as", "geometry")

    Path(filepath).write_text(ET.tostring(tree, encoding="unicode"), encoding="utf-8")
    return f"Edge from {source_id} to {target_id} added with id={new_id}."


@tool
def update_drawio_xml(filepath: str, raw_xml: str) -> str:
    """Completely replace the content of a Draw.io file with new XML.

    Args:
        filepath: Absolute or relative path to the .drawio file.
        raw_xml: Full XML string to write.

    Returns:
        Confirmation message.
    """
    Path(filepath).write_text(raw_xml, encoding="utf-8")
    return f"Diagram updated: {filepath}"


@tool
def delete_drawio_diagram(filepath: str) -> str:
    """Delete a Draw.io diagram file.

    Args:
        filepath: Absolute or relative path to the .drawio file.

    Returns:
        Confirmation message.
    """
    path = Path(filepath)
    if not path.exists():
        return f"ERROR: File not found: {filepath}"
    path.unlink()
    return f"Deleted: {filepath}"


DRAWIO_TOOLS = [
    create_drawio_diagram,
    read_drawio_diagram,
    add_node_to_diagram,
    add_edge_to_diagram,
    update_drawio_xml,
    delete_drawio_diagram,
]
