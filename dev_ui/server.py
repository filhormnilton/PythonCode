"""
dev_ui/server.py — Servidor web para testes da UI que simula o Teams.

⚠️  APENAS PARA TESTES — Este módulo NÃO faz parte do deploy de produção.
     Não inclua a pasta dev_ui/ no deploy do bot do Teams.

Uso:
    pip install fastapi uvicorn          # instalar dependências de teste
    python dev_ui/server.py              # inicia com todos os agentes
    python dev_ui/server.py --agents jira,charts --port 8080

    Depois abra: http://localhost:8080
"""
import argparse
import logging
import os
import re
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

# Garante que o projeto raiz está no sys.path para importar Business.*
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print(
        "ERRO: Instale as dependências de teste antes de usar a dev UI:\n"
        "  pip install fastapi uvicorn\n"
        "  ou: pip install -r dev_ui/requirements-test.txt"
    )
    sys.exit(1)

from langchain_core.messages import HumanMessage, AIMessage  # type: ignore

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).parent.parent
_UI_HTML = Path(__file__).parent / "index.html"
_CHARTS_DIR = _PROJECT_ROOT / "business_output" / "charts"
_BPMN_DIR    = _PROJECT_ROOT / "business_output" / "bpmn"
_DRAWIO_DIR  = Path(os.getenv("DRAWIO_OUTPUT_DIR", "").strip() or str(_PROJECT_ROOT / "business_output" / "diagrams"))
# Detecta: caminhos absolutos Windows (C:\...) OU nomes de arquivo .png soltos
_PNG_RE = re.compile(
    r'(?:[A-Za-z]:[\\\/][^\s\'"]+\.png'
    r'|(?:[\w\-]+\/)*[\w\-\.]+\.png)',
    re.IGNORECASE,
)
# Detecta caminhos ou nomes de arquivo .bpmn na resposta
_BPMN_RE = re.compile(
    r'(?:[A-Za-z]:[\\\/][^\s\'"]+\.bpmn'
    r'|(?:[\w\-]+\/)*[\w\-\.]+\.bpmn)',
    re.IGNORECASE,
)# Detecta caminhos ou nomes de arquivo .drawio na resposta
_DRAWIO_RE = re.compile(
    r'(?:[A-Za-z]:[\\\\][^\s\'"]+\.drawio'
    r'|(?:[\w\-]+\/)*[\w\-\.]+\.drawio)',
    re.IGNORECASE,
)
# ---------------------------------------------------------------------------
# Histórico em memória (mesmo padrão do history_store.py)
# ---------------------------------------------------------------------------

_conversations: Dict[str, List] = {}


def _get_history(conv_id: str) -> List:
    if conv_id not in _conversations:
        _conversations[conv_id] = []
    return _conversations[conv_id]


# ---------------------------------------------------------------------------
# Aplicação FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(title="frysda Dev UI", docs_url=None, redoc_url=None)
_orchestrator: Any = None
# Conversações onde frysda já entrou (para exibir nota de entrada apenas uma vez)
_joined_conversations: set = set()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    conversation_id: str
    user_name: str
    message: str


class ObserveRequest(BaseModel):
    conversation_id: str
    speaker_name: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    chart_urls: list[str] = []
    bpmn_urls: list[str] = []
    drawio_urls: list[str] = []
    conversation_id: str
    joined: bool = False  # True na primeira vez que frysda entra na conversa


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def frontend() -> HTMLResponse:
    """Serve a UI de teste."""
    if not _UI_HTML.is_file():
        raise HTTPException(status_code=404, detail="index.html não encontrado em dev_ui/")
    return HTMLResponse(_UI_HTML.read_text(encoding="utf-8"))


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """Recebe uma mensagem do usuário e retorna a resposta do orquestrador."""
    # Valida ID de conversa (evita injeção em logs)
    if len(req.conversation_id) > 100:
        raise HTTPException(status_code=400, detail="conversation_id inválido")

    history = _get_history(req.conversation_id)
    logger.info("[DEV UI] conv=%s user=%s | %s", req.conversation_id[:8], req.user_name, req.message[:120])

    try:
        # Chamada síncrona direta — evita conflitos entre LangChain e asyncio thread pool
        reply: str = _orchestrator.invoke(req.message, chat_history=history, caller_name=req.user_name)
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("[DEV UI] Orchestrator error:\n%s", tb)
        # Retorna o erro como mensagem de chat para ficar visível na UI
        reply = f"❌ **Erro interno do orquestrador:**\n```\n{exc}\n```\n\nConsulte os logs do servidor para mais detalhes."

    history.append(HumanMessage(content=req.message))
    history.append(AIMessage(content=reply))

    # Detecta caminhos/nomes de PNG na resposta e converte para URLs da API
    chart_urls: List[str] = []
    seen: set = set()
    for raw_path in _PNG_RE.findall(reply):
        # Normaliza para obter só o nome do arquivo
        fname = Path(raw_path.replace("\\", "/")).name
        if not fname.lower().endswith(".png"):
            continue
        if fname in seen:
            continue
        chart_path = _CHARTS_DIR / fname
        if chart_path.is_file():
            seen.add(fname)
            chart_urls.append(f"/api/charts/{fname}")
            logger.info("[DEV UI] Chart detectado na resposta: %s", fname)

    # Detecta caminhos/nomes de .bpmn na resposta e converte para URLs de download
    bpmn_urls: List[str] = []
    seen_bpmn: set = set()
    for raw_path in _BPMN_RE.findall(reply):
        fname = Path(raw_path.replace("\\", "/")).name
        if not fname.lower().endswith(".bpmn"):
            continue
        if fname in seen_bpmn:
            continue
        bpmn_path = _BPMN_DIR / fname
        if bpmn_path.is_file():
            seen_bpmn.add(fname)
            bpmn_urls.append(f"/api/bpmn/{fname}")
            logger.info("[DEV UI] BPMN detectado na resposta: %s", fname)

    # Detecta caminhos/nomes de .drawio na resposta e converte para URLs de download
    drawio_urls: List[str] = []
    seen_drawio: set = set()
    for raw_path in _DRAWIO_RE.findall(reply):
        fname = Path(raw_path.replace("\\", "/")).name
        if not fname.lower().endswith(".drawio"):
            continue
        if fname in seen_drawio:
            continue
        drawio_path = _DRAWIO_DIR / fname
        if drawio_path.is_file():
            seen_drawio.add(fname)
            drawio_urls.append(f"/api/drawio/{fname}")
            logger.info("[DEV UI] Draw.io detectado na resposta: %s", fname)

    joined = req.conversation_id not in _joined_conversations
    if joined:
        _joined_conversations.add(req.conversation_id)

    return ChatResponse(reply=reply, chart_urls=chart_urls, bpmn_urls=bpmn_urls, drawio_urls=drawio_urls, conversation_id=req.conversation_id, joined=joined)


@app.post("/api/observe")
async def observe(req: ObserveRequest) -> JSONResponse:
    """Registra uma mensagem do grupo no histórico e dispara aprendizado silencioso.

    Chamado para TODA mensagem do grupo, mesmo quando frysda não responde.
    Permite que o agente acompanhe o contexto e evolua sua base de conhecimento.
    """
    if len(req.conversation_id) > 100:
        raise HTTPException(status_code=400, detail="conversation_id inválido")

    history = _get_history(req.conversation_id)
    logger.info("[DEV UI OBSERVE] conv=%s speaker=%s | %s", req.conversation_id[:8], req.speaker_name, req.message[:100])

    try:
        _orchestrator.observe(
            message=req.message,
            speaker_name=req.speaker_name,
            chat_history=history,
        )
    except Exception as exc:
        logger.debug("[DEV UI OBSERVE] observe skipped: %s", exc)

    return JSONResponse({"status": "observed"})


@app.get("/api/drawio/{filename}")
async def serve_drawio(filename: str) -> FileResponse:
    """Serve arquivos Draw.io gerados para download."""
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido")
    drawio_path = _DRAWIO_DIR / filename
    if not drawio_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo Draw.io não encontrado")
    return FileResponse(
        str(drawio_path),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/bpmn/{filename}")
async def serve_bpmn(filename: str) -> FileResponse:
    """Serve arquivos BPMN gerados para download."""
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido")
    bpmn_path = _BPMN_DIR / filename
    if not bpmn_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo BPMN não encontrado")
    return FileResponse(
        str(bpmn_path),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/charts/{filename}")
async def serve_chart(filename: str) -> FileResponse:
    """Serve arquivos PNG de gráficos gerados."""
    # Proteção contra path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido")
    chart_path = _CHARTS_DIR / filename
    if not chart_path.is_file():
        raise HTTPException(status_code=404, detail="Gráfico não encontrado")
    return FileResponse(str(chart_path), media_type="image/png")


@app.delete("/api/conversations/{conv_id}")
async def clear_conversation(conv_id: str) -> JSONResponse:
    """Limpa o histórico de uma conversa."""
    _conversations.pop(conv_id, None)
    _joined_conversations.discard(conv_id)
    return JSONResponse({"status": "cleared"})


@app.get("/api/conversations/{conv_id}/history")
async def get_history(conv_id: str) -> JSONResponse:
    """Retorna o histórico de mensagens de uma conversa."""
    history = _get_history(conv_id)
    return JSONResponse([
        {"role": "human" if isinstance(m, HumanMessage) else "ai", "content": m.content}
        for m in history
    ])


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "ui": "dev"})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    global _orchestrator

    parser = argparse.ArgumentParser(description="frysda Dev UI Server")
    parser.add_argument(
        "--agents",
        default="",
        help="Lista de agentes separados por vírgula (ex: jira,charts). Omita para ativar todos.",
    )
    parser.add_argument("--port", type=int, default=8080, help="Porta HTTP (padrão: 8080)")
    args = parser.parse_args()

    enabled_agents: Optional[List[str]] = (
        [a.strip() for a in args.agents.split(",") if a.strip()] if args.agents else None
    )

    from Business.config import CONFIG  # noqa: PLC0415
    from langchain_openai import ChatOpenAI  # type: ignore  # noqa: PLC0415
    from Business.orchestrator.chief_architect import create_business_orchestrator  # noqa: PLC0415

    llm = ChatOpenAI(
        model=CONFIG.llm.model,
        temperature=CONFIG.llm.temperature,
        api_key=CONFIG.llm.api_key,
    )
    _orchestrator = create_business_orchestrator(llm, enabled_agents=enabled_agents)

    logger.info("Orquestrador pronto. Iniciando dev UI em http://localhost:%d", args.port)
    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="info")


if __name__ == "__main__":
    main()
