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

from business.config import CONFIG

_BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
_CAMUNDA_NS = "http://camunda.org/schema/1.0/bpmn"

_BPMN_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"
             xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
             xmlns:camunda="http://camunda.org/schema/1.0/bpmn"
             xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
             xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
             targetNamespace="http://bpmn.io/schema/bpmn"
             id="Definitions_{process_id}">
  <process id="{process_id}" name="{process_name}" isExecutable="true">
    <startEvent id="StartEvent_1" name="Start"/>
    {tasks}
    <endEvent id="EndEvent_1" name="End"/>
  </process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="{process_id}"/>
  </bpmndi:BPMNDiagram>
</definitions>"""


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
def create_bpmn_process(filename: str, process_id: str, process_name: str, tasks: str) -> str:
    """Create a new BPMN 2.0 process file.

    Args:
        filename: Name of the output file (without extension).
        process_id: BPMN process id (no spaces, e.g. 'order-processing').
        process_name: Human-readable process name.
        tasks: Newline-separated list of task names to add as UserTasks.

    Returns:
        Absolute path of the created .bpmn file.
    """
    _ensure_dir(CONFIG.output.bpmn_dir)
    path = CONFIG.output.bpmn_dir / f"{filename}.bpmn"

    task_xml_parts = []
    for idx, task_name in enumerate(tasks.strip().splitlines(), start=1):
        task_name = task_name.strip()
        if not task_name:
            continue
        task_id = f"Task_{idx}"
        task_xml_parts.append(
            f'<userTask id="{task_id}" name="{task_name}" camunda:assignee="${{assignee}}"/>'
        )

    xml = _BPMN_TEMPLATE.format(
        process_id=process_id,
        process_name=process_name,
        tasks="\n    ".join(task_xml_parts),
    )
    path.write_text(xml, encoding="utf-8")
    return str(path)


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
