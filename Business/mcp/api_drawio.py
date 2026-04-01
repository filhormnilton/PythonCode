"""
MCP: api_drawio
Tools for creating, reading, updating, and deleting Draw.io (.drawio / .xml) diagrams.
Draw.io uses XML internally; these tools manipulate the XML representation directly.
"""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List

from langchain_core.tools import tool

from Business.config import CONFIG

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


# ---------------------------------------------------------------------------
# Architecture templates
# ---------------------------------------------------------------------------

_TEMPLATES: dict = {
    "microservices": {
        "description": "Standard microservices architecture with API Gateway, services, and data stores.",
        "cells": [
            # API Gateway
            ('10', 'API Gateway', 'shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.api_gateway;fillColor=#E7157B;strokeColor=none;fontColor=#ffffff;', 80, 360, 60, 60),
            # Services
            ('20', 'Auth Service', 'rounded=1;fillColor=#dae8fc;strokeColor=#6c8ebf;', 240, 160, 160, 60),
            ('21', 'Order Service', 'rounded=1;fillColor=#dae8fc;strokeColor=#6c8ebf;', 240, 280, 160, 60),
            ('22', 'Product Service', 'rounded=1;fillColor=#dae8fc;strokeColor=#6c8ebf;', 240, 400, 160, 60),
            ('23', 'Notification Service', 'rounded=1;fillColor=#dae8fc;strokeColor=#6c8ebf;', 240, 520, 160, 60),
            # Databases
            ('30', 'Auth DB', 'shape=mxgraph.flowchart.database;fillColor=#f5f5f5;strokeColor=#666666;', 500, 160, 80, 60),
            ('31', 'Orders DB', 'shape=mxgraph.flowchart.database;fillColor=#f5f5f5;strokeColor=#666666;', 500, 280, 80, 60),
            ('32', 'Products DB', 'shape=mxgraph.flowchart.database;fillColor=#f5f5f5;strokeColor=#666666;', 500, 400, 80, 60),
            # Message Broker
            ('40', 'Message Broker\n(Kafka / RabbitMQ)', 'shape=mxgraph.archimate3.application;fillColor=#ffe6cc;strokeColor=#d6b656;', 700, 320, 160, 60),
            # Client
            ('50', 'Client (Web / Mobile)', 'shape=mxgraph.archimate3.actor;fillColor=#d5e8d4;strokeColor=#82b366;', 80, 200, 60, 60),
        ],
        "edges": [
            ('e1', '50', '10', 'HTTPS'),
            ('e2', '10', '20', 'route /auth'),
            ('e3', '10', '21', 'route /orders'),
            ('e4', '10', '22', 'route /products'),
            ('e5', '20', '30', 'SQL/NoSQL'),
            ('e6', '21', '31', 'SQL/NoSQL'),
            ('e7', '22', '32', 'SQL/NoSQL'),
            ('e8', '21', '40', 'publish event'),
            ('e9', '40', '23', 'consume event'),
        ],
    },
    "event-driven": {
        "description": "Event-driven architecture with producers, broker, consumers, and event store.",
        "cells": [
            ('10', 'Producer A', 'rounded=1;fillColor=#dae8fc;strokeColor=#6c8ebf;', 40, 100, 140, 60),
            ('11', 'Producer B', 'rounded=1;fillColor=#dae8fc;strokeColor=#6c8ebf;', 40, 220, 140, 60),
            ('12', 'Producer C', 'rounded=1;fillColor=#dae8fc;strokeColor=#6c8ebf;', 40, 340, 140, 60),
            ('20', 'Event Broker\n(Kafka)', 'shape=mxgraph.archimate3.application;fillColor=#ffe6cc;strokeColor=#d6b656;', 280, 220, 160, 60),
            ('30', 'Event Store', 'shape=mxgraph.flowchart.database;fillColor=#f5f5f5;strokeColor=#666666;', 280, 360, 160, 60),
            ('40', 'Consumer A', 'rounded=1;fillColor=#d5e8d4;strokeColor=#82b366;', 540, 100, 140, 60),
            ('41', 'Consumer B', 'rounded=1;fillColor=#d5e8d4;strokeColor=#82b366;', 540, 220, 140, 60),
            ('42', 'Consumer C', 'rounded=1;fillColor=#d5e8d4;strokeColor=#82b366;', 540, 340, 140, 60),
        ],
        "edges": [
            ('e1', '10', '20', 'publish'),
            ('e2', '11', '20', 'publish'),
            ('e3', '12', '20', 'publish'),
            ('e4', '20', '30', 'persist'),
            ('e5', '20', '40', 'subscribe'),
            ('e6', '20', '41', 'subscribe'),
            ('e7', '20', '42', 'subscribe'),
        ],
    },
    "layered": {
        "description": "Classic N-layer architecture: Presentation → Business → Persistence → Database.",
        "cells": [
            # Layers as swim lanes
            ('10', 'Presentation Layer', 'swimlane;fillColor=#dae8fc;strokeColor=#6c8ebf;', 40, 40, 700, 100),
            ('11', 'UI Components', 'rounded=1;fillColor=#dae8fc;strokeColor=#6c8ebf;', 60, 80, 140, 40),
            ('12', 'Controllers', 'rounded=1;fillColor=#dae8fc;strokeColor=#6c8ebf;', 240, 80, 140, 40),
            ('13', 'View Models', 'rounded=1;fillColor=#dae8fc;strokeColor=#6c8ebf;', 420, 80, 140, 40),
            ('20', 'Business Layer', 'swimlane;fillColor=#d5e8d4;strokeColor=#82b366;', 40, 180, 700, 100),
            ('21', 'Services', 'rounded=1;fillColor=#d5e8d4;strokeColor=#82b366;', 60, 220, 140, 40),
            ('22', 'Domain Models', 'rounded=1;fillColor=#d5e8d4;strokeColor=#82b366;', 240, 220, 140, 40),
            ('23', 'Use Cases', 'rounded=1;fillColor=#d5e8d4;strokeColor=#82b366;', 420, 220, 140, 40),
            ('30', 'Persistence Layer', 'swimlane;fillColor=#ffe6cc;strokeColor=#d6b656;', 40, 320, 700, 100),
            ('31', 'Repositories', 'rounded=1;fillColor=#ffe6cc;strokeColor=#d6b656;', 60, 360, 140, 40),
            ('32', 'ORM / Query Builder', 'rounded=1;fillColor=#ffe6cc;strokeColor=#d6b656;', 240, 360, 160, 40),
            ('40', 'Database Layer', 'swimlane;fillColor=#f8cecc;strokeColor=#b85450;', 40, 460, 700, 100),
            ('41', 'Relational DB', 'shape=mxgraph.flowchart.database;fillColor=#f8cecc;strokeColor=#b85450;', 80, 500, 100, 40),
            ('42', 'Cache (Redis)', 'shape=mxgraph.flowchart.database;fillColor=#f8cecc;strokeColor=#b85450;', 240, 500, 100, 40),
            ('43', 'Search (Elastic)', 'shape=mxgraph.flowchart.database;fillColor=#f8cecc;strokeColor=#b85450;', 400, 500, 120, 40),
        ],
        "edges": [
            ('e1', '10', '20', ''),
            ('e2', '20', '30', ''),
            ('e3', '30', '40', ''),
        ],
    },
    "hexagonal": {
        "description": "Hexagonal (Ports & Adapters) architecture with domain at center.",
        "cells": [
            # Domain core
            ('10', 'Domain Core\n(Entities + Use Cases)', 'ellipse;fillColor=#d5e8d4;strokeColor=#82b366;fontStyle=1;', 300, 240, 200, 120),
            # Driving ports/adapters
            ('20', 'REST API Adapter', 'rounded=1;fillColor=#dae8fc;strokeColor=#6c8ebf;', 60, 100, 160, 60),
            ('21', 'GraphQL Adapter', 'rounded=1;fillColor=#dae8fc;strokeColor=#6c8ebf;', 60, 220, 160, 60),
            ('22', 'CLI Adapter', 'rounded=1;fillColor=#dae8fc;strokeColor=#6c8ebf;', 60, 340, 160, 60),
            # Driven ports/adapters
            ('30', 'DB Adapter\n(Repository)', 'rounded=1;fillColor=#ffe6cc;strokeColor=#d6b656;', 580, 100, 160, 60),
            ('31', 'Email Adapter', 'rounded=1;fillColor=#ffe6cc;strokeColor=#d6b656;', 580, 220, 160, 60),
            ('32', 'Cache Adapter\n(Redis)', 'rounded=1;fillColor=#ffe6cc;strokeColor=#d6b656;', 580, 340, 160, 60),
            # External systems
            ('40', 'Database', 'shape=mxgraph.flowchart.database;fillColor=#f5f5f5;strokeColor=#666666;', 780, 100, 80, 60),
            ('41', 'SMTP Server', 'shape=mxgraph.flowchart.manual_input;fillColor=#f5f5f5;strokeColor=#666666;', 780, 220, 80, 60),
            ('42', 'Redis', 'shape=mxgraph.flowchart.database;fillColor=#f5f5f5;strokeColor=#666666;', 780, 340, 80, 60),
        ],
        "edges": [
            ('e1', '20', '10', 'inbound port'),
            ('e2', '21', '10', 'inbound port'),
            ('e3', '22', '10', 'inbound port'),
            ('e4', '10', '30', 'outbound port'),
            ('e5', '10', '31', 'outbound port'),
            ('e6', '10', '32', 'outbound port'),
            ('e7', '30', '40', ''),
            ('e8', '31', '41', ''),
            ('e9', '32', '42', ''),
        ],
    },
}


@tool
def create_drawio_from_template(filename: str, template: str) -> str:
    """Create a Draw.io diagram from a predefined architecture template.

    Available templates:
      - microservices : API Gateway + services + DBs + message broker
      - event-driven  : Producers + Kafka broker + consumers + event store
      - layered       : Presentation → Business → Persistence → Database layers
      - hexagonal     : Ports & Adapters (domain core + driving/driven adapters)

    Args:
        filename: Name of the output file (without extension).
        template: Template name. One of: microservices, event-driven, layered, hexagonal.

    Returns:
        Absolute path of the created .drawio file, or an error message.
    """
    template = template.lower().strip()
    if template not in _TEMPLATES:
        available = ", ".join(_TEMPLATES)
        return f"ERROR: Unknown template '{template}'. Available: {available}"

    _ensure_dir(CONFIG.output.diagrams_dir)
    path = CONFIG.output.diagrams_dir / f"{filename}.drawio"
    spec = _TEMPLATES[template]

    cells_xml: List[str] = []
    for cell_id, value, style, x, y, w, h in spec["cells"]:
        cells_xml.append(
            f'<mxCell id="{cell_id}" value="{value}" style="{style}" '
            f'vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>'
            f'</mxCell>'
        )
    for edge_id, src, tgt, label in spec["edges"]:
        cells_xml.append(
            f'<mxCell id="{edge_id}" value="{label}" style="edgeStyle=orthogonalEdgeStyle;" '
            f'edge="1" source="{src}" target="{tgt}" parent="1">'
            f'<mxGeometry relative="1" as="geometry"/>'
            f'</mxCell>'
        )

    xml_content = _DRAWIO_HEADER.format(
        name=f"{template.title()} Architecture",
        cells="\n        ".join(cells_xml),
    )
    path.write_text(xml_content, encoding="utf-8")
    return str(path)


DRAWIO_TOOLS = [
    create_drawio_diagram,
    read_drawio_diagram,
    add_node_to_diagram,
    add_edge_to_diagram,
    update_drawio_xml,
    delete_drawio_diagram,
    create_drawio_from_template,
]
