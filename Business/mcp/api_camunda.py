"""
MCP: api_camunda
Tools for creating, reading, updating, and deleting BPMN process models via Camunda REST API,
and for generating/manipulating BPMN 2.0 XML files for use with Camunda Modeler.
"""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

import requests

from langchain_core.tools import tool

from Business.config import CONFIG

_BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
_CAMUNDA_NS = "http://camunda.org/schema/1.0/bpmn"

# Layout constants (Camunda Modeler compatible)
_SHAPE_W = 100
_SHAPE_H = 80
_START_W = 36
_START_H = 36
_END_W = 36
_END_H = 36
_GAP = 50        # horizontal gap between elements
_Y_CENTER = 200  # vertical center of the single lane


def _build_bpmn_xml(process_id: str, process_name: str, steps: list[dict]) -> str:
    """Generate BPMN 2.0 XML with full DI layout for Camunda Modeler.

    Each step dict has keys: id, name, type  (startEvent|userTask|serviceTask|exclusiveGateway|endEvent)
    """
    # ---- sequence flows ----
    seq_flows_xml = []
    for i in range(len(steps) - 1):
        sf_id = f"Flow_{i+1}"
        seq_flows_xml.append(
            f'    <sequenceFlow id="{sf_id}" sourceRef="{steps[i]["id"]}" targetRef="{steps[i+1]["id"]}"/>'
        )

    # ---- process elements ----
    elems_xml = []
    for s in steps:
        t = s["type"]
        eid = s["id"]
        ename = s["name"]
        if t == "startEvent":
            elems_xml.append(f'    <startEvent id="{eid}" name="{ename}"/>')
        elif t == "endEvent":
            elems_xml.append(f'    <endEvent id="{eid}" name="{ename}"/>')
        elif t == "exclusiveGateway":
            elems_xml.append(f'    <exclusiveGateway id="{eid}" name="{ename}" gatewayDirection="Diverging"/>')
        elif t == "serviceTask":
            elems_xml.append(f'    <serviceTask id="{eid}" name="{ename}" camunda:type="external" camunda:topic="{eid}"/>')
        else:  # userTask default
            elems_xml.append(f'    <userTask id="{eid}" name="{ename}"/>')

    # ---- DI shapes ----
    x = 80
    shape_xmls = []
    edge_xmls = []
    positions = {}  # id -> (cx, cy, w, h)

    for s in steps:
        t = s["type"]
        eid = s["id"]
        if t in ("startEvent", "endEvent"):
            w, h = _START_W, _START_H
        elif t == "exclusiveGateway":
            w, h = 50, 50
        else:
            w, h = _SHAPE_W, _SHAPE_H
        y = _Y_CENTER - h // 2
        positions[eid] = (x, y, w, h)
        shape_xmls.append(
            f'      <bpmndi:BPMNShape id="{eid}_di" bpmnElement="{eid}">\n'
            f'        <dc:Bounds x="{x}" y="{y}" width="{w}" height="{h}"/>\n'
            f'      </bpmndi:BPMNShape>'
        )
        x += w + _GAP

    for i in range(len(steps) - 1):
        sf_id = f"Flow_{i+1}"
        src = steps[i]["id"]
        tgt = steps[i + 1]["id"]
        sx, sy, sw, sh = positions[src]
        tx, ty, tw, th = positions[tgt]
        mid_src_x = sx + sw
        mid_src_y = sy + sh // 2
        mid_tgt_x = tx
        mid_tgt_y = ty + th // 2
        edge_xmls.append(
            f'      <bpmndi:BPMNEdge id="{sf_id}_di" bpmnElement="{sf_id}">\n'
            f'        <di:waypoint x="{mid_src_x}" y="{mid_src_y}"/>\n'
            f'        <di:waypoint x="{mid_tgt_x}" y="{mid_tgt_y}"/>\n'
            f'      </bpmndi:BPMNEdge>'
        )

    total_w = x + 80
    total_h = _Y_CENTER + _SHAPE_H + 80

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"
             xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
             xmlns:camunda="http://camunda.org/schema/1.0/bpmn"
             xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
             xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
             xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
             targetNamespace="http://bpmn.io/schema/bpmn"
             id="Definitions_{process_id}">
  <process id="{process_id}" name="{process_name}" isExecutable="true">
{chr(10).join(elems_xml)}
{chr(10).join(seq_flows_xml)}
  </process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="{process_id}">
{chr(10).join(shape_xmls)}
{chr(10).join(edge_xmls)}
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</definitions>"""
    return xml


def _ensure_dir(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)


def _camunda_url(path: str) -> str:
    return f"{CONFIG.camunda.rest_url.rstrip('/')}/{path.lstrip('/')}"


def _camunda_auth():
    return (CONFIG.camunda.user, CONFIG.camunda.password)


# ---------------------------------------------------------------------------
# Local BPMN file tools
# ---------------------------------------------------------------------------

@tool
def create_bpmn_process(filename: str, process_id: str, process_name: str, steps: str) -> str:
    """Create a BPMN 2.0 file ready to open in Camunda Modeler, with full visual layout.

    Args:
        filename: Output filename without extension (e.g. 'scope-approval').
        process_id: BPMN process id — no spaces (e.g. 'scope-approval').
        process_name: Human-readable process name shown in Camunda Modeler.
        steps: Newline-separated steps. Each line: "type:Label"
            Supported types: startEvent, userTask, serviceTask, exclusiveGateway, endEvent
            Example:
                startEvent:Solicitação recebida
                userTask:Análise Técnica
                exclusiveGateway:Aprovado?
                userTask:Execução
                endEvent:Processo encerrado

    Returns:
        Absolute path of the created .bpmn file (open with Camunda Modeler).
    """
    _ensure_dir(CONFIG.output.bpmn_dir)
    path = CONFIG.output.bpmn_dir / f"{filename}.bpmn"

    step_list = []
    for idx, line in enumerate(steps.strip().splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            stype, sname = line.split(":", 1)
            stype = stype.strip()
            sname = sname.strip()
        else:
            stype, sname = "userTask", line
        valid_types = {"startEvent", "userTask", "serviceTask", "exclusiveGateway", "endEvent"}
        if stype not in valid_types:
            stype = "userTask"
        step_list.append({"id": f"Step_{idx}", "name": sname, "type": stype})

    # Ensure always starts with startEvent and ends with endEvent
    if not step_list or step_list[0]["type"] != "startEvent":
        step_list.insert(0, {"id": "Step_0", "name": "Início", "type": "startEvent"})
    if step_list[-1]["type"] != "endEvent":
        step_list.append({"id": f"Step_{len(step_list)+1}", "name": "Fim", "type": "endEvent"})

    xml = _build_bpmn_xml(process_id, process_name, step_list)
    path.write_text(xml, encoding="utf-8")
    return f"BPMN file created: {path}\nOpen with Camunda Modeler to visualize and edit."


@tool
def read_bpmn_process(filepath: str) -> str:
    """Read a BPMN file and return its XML content.

    Args:
        filepath: Absolute or relative path to the .bpmn file.

    Returns:
        Raw BPMN XML string.
    """
    return Path(filepath).read_text(encoding="utf-8")


@tool
def update_bpmn_xml(filepath: str, raw_xml: str) -> str:
    """Overwrite a BPMN file with new XML content.

    Args:
        filepath: Absolute or relative path to the .bpmn file.
        raw_xml: Complete BPMN 2.0 XML string.

    Returns:
        Confirmation message.
    """
    Path(filepath).write_text(raw_xml, encoding="utf-8")
    return f"BPMN updated: {filepath}"


@tool
def delete_bpmn_process(filepath: str) -> str:
    """Delete a local BPMN file.

    Args:
        filepath: Absolute or relative path to the .bpmn file.

    Returns:
        Confirmation message.
    """
    path = Path(filepath)
    if not path.exists():
        return f"ERROR: File not found: {filepath}"
    path.unlink()
    return f"Deleted: {filepath}"


# ---------------------------------------------------------------------------
# Camunda REST API tools
# ---------------------------------------------------------------------------

@tool
def deploy_bpmn_to_camunda(filepath: str, deployment_name: str) -> str:
    """Deploy a BPMN file to a running Camunda engine via the REST API.

    Args:
        filepath: Absolute or relative path to the .bpmn file.
        deployment_name: Name for the deployment.

    Returns:
        Deployment id from Camunda or an error message.
    """
    path = Path(filepath)
    if not path.exists():
        return f"ERROR: File not found: {filepath}"

    url = _camunda_url("/deployment/create")
    try:
        with path.open("rb") as f:
            resp = requests.post(
                url,
                files={"upload": (path.name, f, "application/octet-stream")},
                data={"deployment-name": deployment_name},
                auth=_camunda_auth(),
                timeout=30,
            )
        resp.raise_for_status()
        return f"Deployed. ID: {resp.json().get('id', 'unknown')}"
    except Exception as exc:
        return f"Camunda deploy failed: {exc}"


@tool
def list_camunda_processes() -> str:
    """List all deployed process definitions from Camunda.

    Returns:
        Formatted list of process definitions.
    """
    url = _camunda_url("/process-definition")
    try:
        resp = requests.get(url, auth=_camunda_auth(), timeout=15)
        resp.raise_for_status()
        defs = resp.json()
        if not defs:
            return "No process definitions deployed."
        return "\n".join(f"{d.get('id')}: {d.get('name')} (v{d.get('version')})" for d in defs)
    except Exception as exc:
        return f"Failed to list processes: {exc}"


@tool
def start_camunda_process(process_definition_key: str, variables: str = "") -> str:
    """Start a new process instance in Camunda.

    Args:
        process_definition_key: The key of the process definition to start.
        variables: JSON string of process variables (e.g. '{"assignee":"john"}').

    Returns:
        New process instance id or error message.
    """
    import json
    url = _camunda_url(f"/process-definition/key/{process_definition_key}/start")
    payload = {}
    if variables:
        try:
            raw = json.loads(variables)
            payload["variables"] = {k: {"value": v, "type": "String"} for k, v in raw.items()}
        except json.JSONDecodeError:
            return "ERROR: variables must be a valid JSON object string."

    try:
        resp = requests.post(url, json=payload, auth=_camunda_auth(), timeout=15)
        resp.raise_for_status()
        return f"Process started. Instance id: {resp.json().get('id', 'unknown')}"
    except Exception as exc:
        return f"Failed to start process: {exc}"


CAMUNDA_TOOLS = [
    create_bpmn_process,
    read_bpmn_process,
    update_bpmn_xml,
    delete_bpmn_process,
    deploy_bpmn_to_camunda,
    list_camunda_processes,
    start_camunda_process,
]
