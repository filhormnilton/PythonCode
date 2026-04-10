"""
api_server.py — REST API + Microsoft Teams Bot server for the Business Multi-Agent system.

Single server deployed to Azure (App Service or Container Apps) that exposes:
  • A JSON REST API consumed by external Azure applications.
  • The Microsoft Bot Framework webhook consumed by Microsoft Teams channels.

No frontend — the Teams UX is the interface for end-users.
Source-of-truth: GitHub → Azure Container Registry → Azure Container Apps.

REST API endpoints (X-API-Key header required when API_KEY env var is set):
    GET  /health                            Liveness / readiness probe (no auth)
    POST /api/v1/chat                       Send a message to the orchestrator
    DELETE /api/v1/conversations/{id}       Clear a conversation history
    POST /api/v1/ingest                     Ingest a URL into the knowledge base
    GET  /api/v1/files/charts/{filename}    Download a generated PNG chart
    GET  /api/v1/files/bpmn/{filename}      Download a generated BPMN file
    GET  /api/v1/files/diagrams/{filename}  Download a generated Draw.io diagram

Teams Bot Framework endpoint (auth handled by Bot Framework itself):
    POST /api/messages                      Azure Bot Service → Teams messages

Required env vars (Teams):
    TEAMS_APP_ID        Azure Bot registration App ID
    TEAMS_APP_PASSWORD  Azure Bot registration App Password (client secret)

Usage:
    uvicorn api_server:app --host 0.0.0.0 --port 8000
    python api_server.py                   (port 8000 by default)
    python api_server.py --port 80 --agents jira,web
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

try:
    from fastapi import FastAPI, HTTPException, Request, Response, Security, status
    from fastapi.responses import FileResponse, JSONResponse
    from fastapi.security.api_key import APIKeyHeader
    from pydantic import BaseModel, Field
    import uvicorn
except ImportError:
    print(
        "ERROR: fastapi / uvicorn not installed.\n"
        "  Run: pip install fastapi uvicorn\n"
        "  or:  pip install -r requirements.txt"
    )
    sys.exit(1)

from langchain_core.messages import AIMessage, HumanMessage  # type: ignore

# ---------------------------------------------------------------------------
# Optional: Bot Framework (Teams)
# ---------------------------------------------------------------------------

try:
    from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings  # type: ignore
    from botbuilder.schema import Activity  # type: ignore
    _BOT_FRAMEWORK_AVAILABLE = True
except ImportError:
    _BOT_FRAMEWORK_AVAILABLE = False
    logger.warning(
        "[API] botbuilder not installed — /api/messages (Teams) endpoint disabled. "
        "Run: pip install botbuilder-core botbuilder-schema botbuilder-integration-aiohttp"
    )

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).parent
_CHARTS_DIR = _PROJECT_ROOT / "business_output" / "charts"
_BPMN_DIR = _PROJECT_ROOT / "business_output" / "bpmn"
_DRAWIO_DIR = Path(
    os.getenv("DRAWIO_OUTPUT_DIR", "").strip()
    or str(_PROJECT_ROOT / "business_output" / "diagrams")
)

# ---------------------------------------------------------------------------
# Regex helpers — detect generated file references in LLM replies
# ---------------------------------------------------------------------------

_PNG_RE = re.compile(
    r"(?:[A-Za-z]:[\\\/][^\s'\"]+\.png|(?:[\w\-]+\/)*[\w\-\.]+\.png)",
    re.IGNORECASE,
)
_BPMN_RE = re.compile(
    r"(?:[A-Za-z]:[\\\/][^\s'\"]+\.bpmn|(?:[\w\-]+\/)*[\w\-\.]+\.bpmn)",
    re.IGNORECASE,
)
_DRAWIO_RE = re.compile(
    r"(?:[A-Za-z]:[\\\\][^\s'\"]+\.drawio|(?:[\w\-]+\/)*[\w\-\.]+\.drawio)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# In-memory conversation store  (key: conversation_id → list of messages)
# ---------------------------------------------------------------------------

_conversations: Dict[str, List] = {}


def _get_history(conv_id: str) -> List:
    if conv_id not in _conversations:
        _conversations[conv_id] = []
    return _conversations[conv_id]


# ---------------------------------------------------------------------------
# API-key authentication
# ---------------------------------------------------------------------------

_API_KEY_ENV = os.getenv("API_KEY", "")  # empty → auth disabled

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _require_api_key(api_key: Optional[str] = Security(_api_key_header)) -> None:
    """Dependency that enforces API-key authentication when API_KEY env is set."""
    if not _API_KEY_ENV:
        # Auth disabled — dev/test mode
        return
    if not api_key or api_key != _API_KEY_ENV:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Supply the X-API-Key header.",
        )


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    conversation_id: str = Field(
        ...,
        max_length=100,
        description="Unique identifier for this conversation thread.",
        examples=["user-123-session-abc"],
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="The user message to send to the orchestrator.",
    )
    user_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Optional caller name (used in multi-user context).",
    )


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    chart_urls: List[str] = []
    bpmn_urls: List[str] = []
    drawio_urls: List[str] = []


class IngestRequest(BaseModel):
    url: str = Field(..., description="URL to fetch and ingest into the knowledge base.")
    depth: int = Field(default=0, ge=0, le=3, description="Link crawl depth (0 = only the given URL).")
    tags: str = Field(default="", max_length=200, description="Comma-separated tags for the ingested entries.")


class IngestResponse(BaseModel):
    pages_ingested: int
    message: str


class ConversationDeleteResponse(BaseModel):
    conversation_id: str
    message: str


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Business Multi-Agent API",
    description=(
        "REST API for the frysda Business Multi-Agent orchestrator.\n\n"
        "Authenticate all requests (except `/health`) with the `X-API-Key` header."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Shared orchestrator instance (initialised on startup)
_orchestrator: Any = None
_enabled_agents: Optional[List[str]] = None

# Teams Bot Framework adapter (None when botbuilder is not installed or creds absent)
_bot_adapter: Any = None
_teams_bot: Any = None


# ---------------------------------------------------------------------------
# Startup — initialise the orchestrator and optional Teams bot adapter
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def _startup() -> None:
    global _orchestrator, _bot_adapter, _teams_bot
    logger.info("[API] Initialising Business Multi-Agent orchestrator...")
    try:
        from Business.config import CONFIG
        from langchain_openai import ChatOpenAI  # type: ignore
        from Business.orchestrator.chief_architect import create_business_orchestrator

        llm = ChatOpenAI(
            model=CONFIG.llm.model,
            temperature=CONFIG.llm.temperature,
            api_key=CONFIG.llm.api_key,
        )
        _orchestrator = create_business_orchestrator(llm, enabled_agents=_enabled_agents)
        logger.info("[API] Orchestrator ready.")
    except Exception:
        logger.error("[API] Failed to initialise orchestrator:\n%s", traceback.format_exc())
        # Don't crash — let /health report degraded state

    # Initialise Teams Bot Framework adapter (requires TEAMS_APP_ID + TEAMS_APP_PASSWORD)
    if _BOT_FRAMEWORK_AVAILABLE and _orchestrator is not None:
        try:
            from Business.config import CONFIG
            from Business.teams_bot.bot import BusinessBot

            settings = BotFrameworkAdapterSettings(
                app_id=CONFIG.teams.app_id,
                app_password=CONFIG.teams.app_password,
            )
            _bot_adapter = BotFrameworkAdapter(settings)
            _teams_bot = BusinessBot(_orchestrator)
            logger.info("[API] Teams Bot Framework adapter ready (app_id=%s).", CONFIG.teams.app_id or "(empty)")
        except Exception:
            logger.error("[API] Failed to initialise Teams adapter:\n%s", traceback.format_exc())


# ---------------------------------------------------------------------------
# Health check (no auth — used by Azure probes)
# ---------------------------------------------------------------------------

@app.get("/health", tags=["ops"], summary="Liveness / readiness probe")
async def health() -> JSONResponse:
    """Returns 200 when the service is running, 503 when the orchestrator failed to load."""
    if _orchestrator is None:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "degraded", "detail": "Orchestrator not initialised"},
        )
    return JSONResponse(content={
        "status": "ok",
        "teams_bot": _bot_adapter is not None,
    })


# ---------------------------------------------------------------------------
# Teams Bot Framework — /api/messages
# This endpoint is called by Azure Bot Service when Teams sends a message.
# Authentication is handled by the Bot Framework (JWT validation), NOT by X-API-Key.
# ---------------------------------------------------------------------------

@app.post("/api/messages", tags=["teams"], summary="Microsoft Teams Bot Framework webhook")
async def teams_messages(req: Request) -> Response:
    """
    Receives activities from Microsoft Teams via Azure Bot Service.

    - Registered as the **Messaging endpoint** in the Azure Bot resource.
    - Auth is validated by the Bot Framework SDK (JWT Bearer token).
    - TEAMS_APP_ID and TEAMS_APP_PASSWORD must be set as environment variables.
    """
    if not _BOT_FRAMEWORK_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="botbuilder is not installed on this server.",
        )
    if _bot_adapter is None or _teams_bot is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Teams adapter not initialised. Check TEAMS_APP_ID / TEAMS_APP_PASSWORD and server logs.",
        )

    body = await req.json()
    activity = Activity().deserialize(body)
    auth_header = req.headers.get("Authorization", "")

    try:
        invoke_response = await _bot_adapter.process_activity(activity, auth_header, _teams_bot.on_turn)
    except Exception as exc:
        logger.error("[TEAMS] process_activity error:\n%s", traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    if invoke_response:
        return Response(
            content=invoke_response.body,
            status_code=invoke_response.status,
            media_type="application/json",
        )
    return Response(status_code=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

@app.post(
    "/api/v1/chat",
    response_model=ChatResponse,
    tags=["chat"],
    summary="Send a message to the orchestrator",
    dependencies=[Security(_require_api_key)],
)
async def chat(req: ChatRequest) -> ChatResponse:
    """
    Send a user message and receive the orchestrator reply.

    - Keeps per-`conversation_id` history in memory.
    - Returns URLs for any charts, BPMN, or diagram files generated during the response.
    """
    if _orchestrator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Orchestrator not available. Check server logs.",
        )

    history = _get_history(req.conversation_id)
    logger.info(
        "[API] conv=%s user=%s | %s",
        req.conversation_id[:12],
        req.user_name or "anonymous",
        req.message[:120],
    )

    try:
        invoke_kwargs: Dict[str, Any] = {"chat_history": history}
        if req.user_name:
            invoke_kwargs["caller_name"] = req.user_name

        reply: str = _orchestrator.invoke(req.message, **invoke_kwargs)
    except Exception as exc:
        logger.error("[API] Orchestrator error:\n%s", traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Orchestrator error: {exc}",
        ) from exc

    history.append(HumanMessage(content=req.message))
    history.append(AIMessage(content=reply))

    # -- Resolve generated file references to API download URLs ---------------

    chart_urls: List[str] = []
    seen_png: set = set()
    for raw in _PNG_RE.findall(reply):
        fname = Path(raw.replace("\\", "/")).name
        if not fname.lower().endswith(".png") or fname in seen_png:
            continue
        if (_CHARTS_DIR / fname).is_file():
            seen_png.add(fname)
            chart_urls.append(f"/api/v1/files/charts/{fname}")

    bpmn_urls: List[str] = []
    seen_bpmn: set = set()
    for raw in _BPMN_RE.findall(reply):
        fname = Path(raw.replace("\\", "/")).name
        if not fname.lower().endswith(".bpmn") or fname in seen_bpmn:
            continue
        if (_BPMN_DIR / fname).is_file():
            seen_bpmn.add(fname)
            bpmn_urls.append(f"/api/v1/files/bpmn/{fname}")

    drawio_urls: List[str] = []
    seen_drawio: set = set()
    for raw in _DRAWIO_RE.findall(reply):
        fname = Path(raw.replace("\\", "/")).name
        if not fname.lower().endswith(".drawio") or fname in seen_drawio:
            continue
        if (_DRAWIO_DIR / fname).is_file():
            seen_drawio.add(fname)
            drawio_urls.append(f"/api/v1/files/diagrams/{fname}")

    return ChatResponse(
        conversation_id=req.conversation_id,
        reply=reply,
        chart_urls=chart_urls,
        bpmn_urls=bpmn_urls,
        drawio_urls=drawio_urls,
    )


# ---------------------------------------------------------------------------
# Conversation management
# ---------------------------------------------------------------------------

@app.delete(
    "/api/v1/conversations/{conversation_id}",
    response_model=ConversationDeleteResponse,
    tags=["chat"],
    summary="Clear a conversation history",
    dependencies=[Security(_require_api_key)],
)
async def delete_conversation(conversation_id: str) -> ConversationDeleteResponse:
    """Remove all stored messages for the given `conversation_id`."""
    if len(conversation_id) > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="conversation_id too long")
    _conversations.pop(conversation_id, None)
    return ConversationDeleteResponse(
        conversation_id=conversation_id,
        message="Conversation history cleared.",
    )


# ---------------------------------------------------------------------------
# Knowledge base ingest
# ---------------------------------------------------------------------------

@app.post(
    "/api/v1/ingest",
    response_model=IngestResponse,
    tags=["knowledge"],
    summary="Ingest a URL into the knowledge base",
    dependencies=[Security(_require_api_key)],
)
async def ingest(req: IngestRequest) -> IngestResponse:
    """
    Fetch a URL (and optionally follow same-domain links up to `depth` levels)
    and store the extracted text in the local knowledge base.
    """
    try:
        import requests as http_requests  # type: ignore
        from bs4 import BeautifulSoup  # type: ignore
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="requests / beautifulsoup4 not installed.",
        )

    from urllib.parse import urljoin, urlparse
    from Business.mcp.api_knowledge_base import add_knowledge_entry

    headers = {"User-Agent": "Mozilla/5.0 (compatible; BusinessAgent/1.0)"}
    root_netloc = urlparse(req.url).netloc
    visited: set = set()

    def _ingest_one(target_url: str, current_depth: int) -> None:
        if target_url in visited:
            return
        visited.add(target_url)
        logger.info("[INGEST] Fetching: %s", target_url)
        try:
            resp = http_requests.get(target_url, headers=headers, timeout=15)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("[INGEST] Failed %s: %s", target_url, exc)
            return

        soup = BeautifulSoup(resp.text, "html.parser")
        title_tag = soup.title
        title = title_tag.string.strip() if title_tag and title_tag.string else target_url
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        content = soup.get_text(separator="\n", strip=True)[:8000]

        add_knowledge_entry.invoke({
            "title": title,
            "content": content,
            "tags": req.tags,
            "source": target_url,
        })

        if current_depth > 0:
            base = f"{urlparse(target_url).scheme}://{urlparse(target_url).netloc}"
            for a in soup.find_all("a", href=True):
                link = urljoin(base, a["href"])
                parsed = urlparse(link)
                if parsed.scheme in ("http", "https") and parsed.netloc == root_netloc:
                    _ingest_one(link, current_depth - 1)

    try:
        _ingest_one(req.url, req.depth)
    except Exception as exc:
        logger.error("[INGEST] Error: %s", traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingest failed: {exc}",
        ) from exc

    return IngestResponse(
        pages_ingested=len(visited),
        message=f"Ingested {len(visited)} page(s) from {req.url}.",
    )


# ---------------------------------------------------------------------------
# File downloads — charts, BPMN, Draw.io
# ---------------------------------------------------------------------------

def _safe_file_response(directory: Path, filename: str, media_type: str) -> FileResponse:
    """Return a FileResponse after validating the path stays within *directory*."""
    # Prevent path traversal
    safe_name = Path(filename).name
    file_path = (directory / safe_name).resolve()
    if not str(file_path).startswith(str(directory.resolve())):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename")
    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return FileResponse(path=str(file_path), media_type=media_type, filename=safe_name)


@app.get(
    "/api/v1/files/charts/{filename}",
    tags=["files"],
    summary="Download a generated PNG chart",
    dependencies=[Security(_require_api_key)],
)
async def get_chart(filename: str) -> FileResponse:
    return _safe_file_response(_CHARTS_DIR, filename, "image/png")


@app.get(
    "/api/v1/files/bpmn/{filename}",
    tags=["files"],
    summary="Download a generated BPMN file",
    dependencies=[Security(_require_api_key)],
)
async def get_bpmn(filename: str) -> FileResponse:
    return _safe_file_response(_BPMN_DIR, filename, "application/xml")


@app.get(
    "/api/v1/files/diagrams/{filename}",
    tags=["files"],
    summary="Download a generated Draw.io diagram",
    dependencies=[Security(_require_api_key)],
)
async def get_diagram(filename: str) -> FileResponse:
    return _safe_file_response(_DRAWIO_DIR, filename, "application/xml")


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Business Multi-Agent REST API Server"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument(
        "--agents",
        default="",
        help=(
            "Comma-separated list of agents to activate. "
            "Valid: docs,slides,architect,jira,web,process,miro,charts. "
            "Omit to enable all."
        ),
    )
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (dev only)")
    args = parser.parse_args()

    global _enabled_agents
    if args.agents:
        _enabled_agents = [a.strip() for a in args.agents.split(",") if a.strip()]

    uvicorn.run(
        "api_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
