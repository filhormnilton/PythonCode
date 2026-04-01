# Business MultiAgent

A multi-agent AI system built with **LangChain** that orchestrates seven specialist agents via Model Context Protocol (MCP) tool wrappers.

## Architecture

```
Microsoft Teams
      │
      ▼
business/teams_bot/bot.py  ← Bot Framework Adapter
      │
      ▼
business/orchestrator/chief_architect.py  ← "frysda" / LangChain AgentExecutor
      │
  ┌───┼──────────────────────────────────────────────┐
  ▼   ▼       ▼         ▼       ▼       ▼       ▼
DOCS SLIDES ARCHITECT  JIRA    WEB   PROCESS  MIRO
  │    │       │         │       │       │       │
MCP  MCP     MCP       MCP     MCP     MCP     MCP
(Word/  (pptx) (drawio)  (jira)  (web) (camunda)(miro)
 PDF/
 TXT)
```

See the full diagram: **[business/architecture.drawio](business/architecture.drawio)**
→ Open at [app.diagrams.net](https://app.diagrams.net/#Uhttps://raw.githubusercontent.com/filhormnilton/PythonCode/copilot/create-multiagent-architecture-business/business/architecture.drawio)

## Agents

| # | Agent | File | MCP Tools | Scope |
|---|-------|------|-----------|-------|
| 1 | **DOCS** | `agents/docs_agent.py` | `mcp/api_office_pdf.py` | Word, PDF, TXT |
| 2 | **SLIDES** | `agents/slides_agent.py` | `mcp/api_powerpoint.py` | PowerPoint |
| 3 | **ARCHITECT** | `agents/architect_agent.py` | `mcp/api_drawio.py` | Draw.io |
| 4 | **JIRA** | `agents/jira_agent.py` | `mcp/api_jira.py` | JIRA backlog |
| 5 | **WEB** | `agents/web_agent.py` | `mcp/api_web.py` | Web research |
| 6 | **PROCESS** | `agents/process_agent.py` | `mcp/api_camunda.py` | BPMN / Camunda |
| 7 | **MIRO** | `agents/miro_agent.py` | `mcp/api_miro.py` | MIRO boards |

## Orchestrator Modes

| Mode | Operation | Agents |
|------|-----------|--------|
| 1 | Engenharia de User Story | JIRA + DOCS |
| 2 | Auditoria Heurística | JIRA + MIRO + SLIDES |
| 3 | Discovery & Arquitetura | WEB + PROCESS + ARCHITECT |
| 4 | Gestão de Mudança em Massa | JIRA + DOCS + PROCESS |
| 5 | Ad-hoc Orchestration | Intelligent routing |

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Run

```bash
# Interactive CLI
python business_main.py --mode cli

# One-shot request
python business_main.py --mode once --request "Crie uma user story para login SSO"

# Microsoft Teams Bot (requires Azure Bot registration)
python business_main.py --mode teams
```

## Microsoft Teams Setup

1. Register a bot in [Azure Bot Service](https://portal.azure.com) (Bot Framework v4).
2. Add the **Microsoft Teams** channel.
3. Set the messaging endpoint to `https://<your-host>/api/messages`.
4. Copy App ID and Password to `.env` (`TEAMS_APP_ID`, `TEAMS_APP_PASSWORD`).
5. Run `python business_main.py --mode teams`.
6. Add the bot to your Teams group or meeting chat.

## Project Structure

```
business/
├── __init__.py
├── config.py                        # Centralised configuration
├── architecture.drawio              # Full architecture diagram
├── agents/
│   ├── base.py                      # Shared agent factory
│   ├── docs_agent.py
│   ├── slides_agent.py
│   ├── architect_agent.py
│   ├── jira_agent.py
│   ├── web_agent.py
│   ├── process_agent.py
│   └── miro_agent.py
├── mcp/
│   ├── api_office_pdf.py
│   ├── api_powerpoint.py
│   ├── api_drawio.py
│   ├── api_jira.py
│   ├── api_web.py
│   ├── api_camunda.py
│   └── api_miro.py
├── orchestrator/
│   └── chief_architect.py           # "frysda" supervisor agent
└── teams_bot/
    └── bot.py                       # Bot Framework adapter + aiohttp server
business_main.py                     # CLI / Teams / once entry point
```
