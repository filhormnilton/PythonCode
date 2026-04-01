"""
Tests for the Business multi-agent package.

These tests validate module imports, configuration loading, MCP tool definitions,
and agent factory functions without requiring live API credentials.
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Make sure the repo root is on sys.path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class TestConfig:
    def test_config_loads(self):
        from business.config import load_config
        cfg = load_config()
        assert cfg is not None
        assert cfg.llm is not None
        assert cfg.jira is not None
        assert cfg.miro is not None

    def test_output_config_paths(self):
        from business.config import load_config
        cfg = load_config()
        assert cfg.output.docs_dir.name == "docs"
        assert cfg.output.slides_dir.name == "slides"
        assert cfg.output.diagrams_dir.name == "diagrams"
        assert cfg.output.bpmn_dir.name == "bpmn"

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
        from business import config as cfg_module
        # Reload to pick up the env var
        import importlib
        importlib.reload(cfg_module)
        new_cfg = cfg_module.load_config()
        assert new_cfg.llm.api_key == "test-key-123"


# ---------------------------------------------------------------------------
# MCP tool exports
# ---------------------------------------------------------------------------

class TestMcpToolExports:
    def test_office_pdf_tools_exported(self):
        from business.mcp.api_office_pdf import OFFICE_PDF_TOOLS
        assert len(OFFICE_PDF_TOOLS) >= 7
        names = [t.name for t in OFFICE_PDF_TOOLS]
        assert "create_word_document" in names
        assert "create_pdf_document" in names
        assert "create_txt_document" in names
        assert "delete_document" in names

    def test_powerpoint_tools_exported(self):
        from business.mcp.api_powerpoint import POWERPOINT_TOOLS
        assert len(POWERPOINT_TOOLS) >= 4
        names = [t.name for t in POWERPOINT_TOOLS]
        assert "create_presentation" in names
        assert "read_presentation" in names

    def test_drawio_tools_exported(self):
        from business.mcp.api_drawio import DRAWIO_TOOLS
        assert len(DRAWIO_TOOLS) >= 5
        names = [t.name for t in DRAWIO_TOOLS]
        assert "create_drawio_diagram" in names
        assert "add_node_to_diagram" in names
        assert "add_edge_to_diagram" in names

    def test_jira_tools_exported(self):
        from business.mcp.api_jira import JIRA_TOOLS
        assert len(JIRA_TOOLS) >= 5
        names = [t.name for t in JIRA_TOOLS]
        assert "create_jira_issue" in names
        assert "search_jira_issues" in names

    def test_web_tools_exported(self):
        from business.mcp.api_web import WEB_TOOLS
        assert len(WEB_TOOLS) >= 2
        names = [t.name for t in WEB_TOOLS]
        assert "web_search" in names
        assert "fetch_webpage" in names

    def test_camunda_tools_exported(self):
        from business.mcp.api_camunda import CAMUNDA_TOOLS
        assert len(CAMUNDA_TOOLS) >= 5
        names = [t.name for t in CAMUNDA_TOOLS]
        assert "create_bpmn_process" in names
        assert "deploy_bpmn_to_camunda" in names

    def test_miro_tools_exported(self):
        from business.mcp.api_miro import MIRO_TOOLS
        assert len(MIRO_TOOLS) >= 5
        names = [t.name for t in MIRO_TOOLS]
        assert "create_miro_board" in names
        assert "create_sticky_note" in names


# ---------------------------------------------------------------------------
# MCP local-file tools (no external dependencies needed)
# ---------------------------------------------------------------------------

class TestDrawioMcpLocalTools:
    @pytest.fixture(autouse=True)
    def _patch_output_dir(self, tmp_path, monkeypatch):
        """Redirect output directory and reload affected modules for each test."""
        import importlib
        from business import config as cfg_module
        monkeypatch.setenv("BUSINESS_OUTPUT_DIR", str(tmp_path))
        importlib.reload(cfg_module)
        import business.mcp.api_drawio as drawio_module
        importlib.reload(drawio_module)
        self._drawio = drawio_module

    def test_create_and_read_drawio(self):
        result = self._drawio.create_drawio_diagram.invoke({
            "filename": "test_arch",
            "diagram_name": "Test Architecture",
            "description": "ServiceA\nServiceB\nDatabase",
        })
        assert result.endswith(".drawio")
        assert Path(result).exists()

        content = self._drawio.read_drawio_diagram.invoke({"filepath": result})
        assert "ServiceA" in content
        assert "ServiceB" in content
        assert "Database" in content

    def test_delete_drawio(self):
        path = self._drawio.create_drawio_diagram.invoke({
            "filename": "to_delete",
            "diagram_name": "Delete Me",
            "description": "NodeX",
        })
        assert Path(path).exists()
        msg = self._drawio.delete_drawio_diagram.invoke({"filepath": path})
        assert "Deleted" in msg
        assert not Path(path).exists()


class TestTxtMcpLocalTools:
    @pytest.fixture(autouse=True)
    def _patch_output_dir(self, tmp_path, monkeypatch):
        import importlib
        from business import config as cfg_module
        monkeypatch.setenv("BUSINESS_OUTPUT_DIR", str(tmp_path))
        importlib.reload(cfg_module)
        import business.mcp.api_office_pdf as docs_module
        importlib.reload(docs_module)
        self._docs = docs_module

    def test_create_read_update_txt(self):
        path = self._docs.create_txt_document.invoke({
            "filename": "notes",
            "content": "Hello World",
        })
        assert Path(path).exists()

        content = self._docs.read_txt_document.invoke({"filepath": path})
        assert content == "Hello World"

        self._docs.update_txt_document.invoke({"filepath": path, "new_content": "Updated"})
        assert Path(path).read_text() == "Updated"


class TestBpmnMcpLocalTools:
    @pytest.fixture(autouse=True)
    def _patch_output_dir(self, tmp_path, monkeypatch):
        import importlib
        from business import config as cfg_module
        monkeypatch.setenv("BUSINESS_OUTPUT_DIR", str(tmp_path))
        importlib.reload(cfg_module)
        import business.mcp.api_camunda as camunda_module
        importlib.reload(camunda_module)
        self._camunda = camunda_module

    def test_create_read_bpmn(self):
        path = self._camunda.create_bpmn_process.invoke({
            "filename": "order",
            "process_id": "order-process",
            "process_name": "Order Processing",
            "tasks": "Validate Order\nProcess Payment\nShip Item",
        })
        assert path.endswith(".bpmn")
        assert Path(path).exists()

        xml = self._camunda.read_bpmn_process.invoke({"filepath": path})
        assert "order-process" in xml
        assert "Validate Order" in xml


# ---------------------------------------------------------------------------
# Agent factories (mocked LLM)
# ---------------------------------------------------------------------------

class TestAgentFactories:
    @pytest.fixture
    def mock_llm(self):
        llm = MagicMock()
        llm.bind_tools = MagicMock(return_value=llm)
        llm.with_structured_output = MagicMock(return_value=llm)
        return llm

    def test_docs_agent_factory(self, mock_llm):
        from business.agents.docs_agent import create_docs_agent
        agent = create_docs_agent(mock_llm)
        assert agent is not None

    def test_slides_agent_factory(self, mock_llm):
        from business.agents.slides_agent import create_slides_agent
        agent = create_slides_agent(mock_llm)
        assert agent is not None

    def test_architect_agent_factory(self, mock_llm):
        from business.agents.architect_agent import create_architect_agent
        agent = create_architect_agent(mock_llm)
        assert agent is not None

    def test_jira_agent_factory(self, mock_llm):
        from business.agents.jira_agent import create_jira_agent
        agent = create_jira_agent(mock_llm)
        assert agent is not None

    def test_web_agent_factory(self, mock_llm):
        from business.agents.web_agent import create_web_agent
        agent = create_web_agent(mock_llm)
        assert agent is not None

    def test_process_agent_factory(self, mock_llm):
        from business.agents.process_agent import create_process_agent
        agent = create_process_agent(mock_llm)
        assert agent is not None

    def test_miro_agent_factory(self, mock_llm):
        from business.agents.miro_agent import create_miro_agent
        agent = create_miro_agent(mock_llm)
        assert agent is not None


# ---------------------------------------------------------------------------
# Orchestrator (mocked LLM)
# ---------------------------------------------------------------------------

class TestOrchestrator:
    def test_create_orchestrator(self):
        from unittest.mock import MagicMock
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)
        from business.orchestrator.chief_architect import create_business_orchestrator
        orc = create_business_orchestrator(mock_llm)
        assert orc is not None

    def test_orchestrator_invoke(self):
        """Verify orchestrator invoke delegates to the agent executor."""
        from unittest.mock import MagicMock, patch
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)
        from business.orchestrator.chief_architect import BusinessOrchestrator

        orc = BusinessOrchestrator(mock_llm)
        mock_executor = MagicMock()
        mock_executor.invoke.return_value = {"output": "Test response"}
        orc._executor = mock_executor

        result = orc.invoke("Hello")
        assert result == "Test response"
        mock_executor.invoke.assert_called_once()


# ---------------------------------------------------------------------------
# Architecture diagram file
# ---------------------------------------------------------------------------

class TestArchitectureDiagram:
    def test_diagram_file_exists(self):
        diagram = ROOT / "business" / "architecture.drawio"
        assert diagram.exists(), "architecture.drawio must exist"

    def test_diagram_is_valid_xml(self):
        import xml.etree.ElementTree as ET
        diagram = ROOT / "business" / "architecture.drawio"
        tree = ET.parse(str(diagram))
        root = tree.getroot()
        assert root.tag == "mxfile"

    def test_diagram_contains_all_agents(self):
        diagram = ROOT / "business" / "architecture.drawio"
        content = diagram.read_text(encoding="utf-8")
        for agent in ["DOCS", "SLIDES", "ARCHITECT", "JIRA", "WEB", "PROCESS", "MIRO"]:
            assert agent in content, f"Agent '{agent}' not found in architecture diagram"


# ---------------------------------------------------------------------------
# Knowledge Base MCP (local file tools — no external dependencies)
# ---------------------------------------------------------------------------

class TestKnowledgeBaseMcp:
    @pytest.fixture(autouse=True)
    def _patch_kb_dir(self, tmp_path, monkeypatch):
        """Redirect KB output directory and reload affected modules for each test."""
        import importlib
        from business import config as cfg_module
        monkeypatch.setenv("BUSINESS_OUTPUT_DIR", str(tmp_path))
        importlib.reload(cfg_module)
        import business.mcp.api_knowledge_base as kb_module
        importlib.reload(kb_module)
        self._kb = kb_module

    def test_tools_exported(self):
        assert len(self._kb.KNOWLEDGE_BASE_TOOLS) == 6
        names = [t.name for t in self._kb.KNOWLEDGE_BASE_TOOLS]
        assert "add_knowledge_entry" in names
        assert "search_knowledge_base" in names
        assert "get_knowledge_entry" in names
        assert "list_knowledge_entries" in names
        assert "update_knowledge_entry" in names
        assert "remove_knowledge_entry" in names

    def test_add_and_get(self):
        result = self._kb.add_knowledge_entry.invoke({
            "title": "REST API Best Practices",
            "content": "Use nouns for resources, HTTP verbs for actions.",
            "tags": "api,rest",
            "source": "https://restfulapi.net",
        })
        assert "REST API Best Practices" in result
        entry_id = result.split("ID=")[1].split(" ")[0]

        detail = self._kb.get_knowledge_entry.invoke({"entry_id": entry_id})
        assert "REST API Best Practices" in detail
        assert "Use nouns for resources" in detail
        assert "api" in detail

    def test_list_empty(self):
        result = self._kb.list_knowledge_entries.invoke({})
        assert "empty" in result.lower()

    def test_list_with_entries(self):
        self._kb.add_knowledge_entry.invoke({
            "title": "BPMN Gateway Types",
            "content": "Exclusive, Inclusive, Parallel gateways.",
            "tags": "bpmn,process",
        })
        result = self._kb.list_knowledge_entries.invoke({})
        assert "BPMN Gateway Types" in result

    def test_list_tag_filter(self):
        self._kb.add_knowledge_entry.invoke({
            "title": "Entry A",
            "content": "Content A",
            "tags": "jira,agile",
        })
        self._kb.add_knowledge_entry.invoke({
            "title": "Entry B",
            "content": "Content B",
            "tags": "bpmn",
        })
        result = self._kb.list_knowledge_entries.invoke({"tag_filter": "jira"})
        assert "Entry A" in result
        assert "Entry B" not in result

    def test_search_found(self):
        self._kb.add_knowledge_entry.invoke({
            "title": "Microservices Patterns",
            "content": "Saga pattern for distributed transactions.",
            "tags": "microservices,architecture",
        })
        result = self._kb.search_knowledge_base.invoke({"query": "saga distributed"})
        assert "Microservices Patterns" in result

    def test_search_not_found(self):
        # With an empty KB the message is different from a non-empty one with no match.
        result = self._kb.search_knowledge_base.invoke({"query": "nonexistent_xyz"})
        assert "No entries found" in result or "empty" in result.lower()

    def test_update_entry(self):
        self._kb.add_knowledge_entry.invoke({
            "title": "Original Title",
            "content": "Original content.",
            "tags": "test",
        })
        entries = self._kb._load_index()
        entry_id = entries[0]["id"]

        self._kb.update_knowledge_entry.invoke({
            "entry_id": entry_id,
            "content": "Updated content.",
            "tags": "test,updated",
        })

        detail = self._kb.get_knowledge_entry.invoke({"entry_id": entry_id})
        assert "Updated content." in detail
        assert "updated" in detail

    def test_remove_entry(self):
        self._kb.add_knowledge_entry.invoke({
            "title": "To Remove",
            "content": "Delete me.",
            "tags": "temp",
        })
        entries = self._kb._load_index()
        entry_id = entries[0]["id"]

        msg = self._kb.remove_knowledge_entry.invoke({"entry_id": entry_id})
        assert "removed" in msg.lower()

        detail = self._kb.get_knowledge_entry.invoke({"entry_id": entry_id})
        assert "not found" in detail.lower()

    def test_remove_nonexistent(self):
        result = self._kb.remove_knowledge_entry.invoke({"entry_id": "does-not-exist"})
        assert "not found" in result.lower()


# ---------------------------------------------------------------------------
# Config — knowledge_base_dir
# ---------------------------------------------------------------------------

class TestKnowledgeBaseConfig:
    def test_knowledge_base_dir(self):
        from business.config import load_config
        cfg = load_config()
        assert cfg.output.knowledge_base_dir.name == "knowledge_base"
