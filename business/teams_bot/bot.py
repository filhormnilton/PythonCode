"""
Microsoft Teams Bot — Business Multi-Agent Gateway

Listens for incoming messages from Microsoft Teams (via Bot Framework)
and routes them through the BusinessOrchestrator.

Usage (standalone):
    python -m business.teams_bot.bot

The bot exposes a single POST endpoint at /api/messages that the
Azure Bot Service or Microsoft Teams channel will call.
"""
from __future__ import annotations

import logging
import sys
from typing import Any, Dict, List, Optional

from aiohttp import web
from botbuilder.core import (  # type: ignore
    BotFrameworkAdapterSettings,
    BotFrameworkAdapter,
    TurnContext,
    ActivityHandler,
    MessageFactory,
)
from botbuilder.schema import Activity  # type: ignore

logger = logging.getLogger(__name__)


class BusinessBot(ActivityHandler):
    """Activity handler that forwards every Teams message to the orchestrator."""

    def __init__(self, orchestrator: Any):
        super().__init__()
        self._orchestrator = orchestrator
        # Per-conversation history (in-memory; replace with CosmosDB for production)
        self._history: Dict[str, List] = {}

    async def on_message_activity(self, turn_context: TurnContext) -> None:
        """Handle an incoming text message from Teams."""
        conversation_id = turn_context.activity.conversation.id
        user_text = (turn_context.activity.text or "").strip()

        if not user_text:
            await turn_context.send_activity(
                MessageFactory.text("⚠️ Mensagem vazia. Por favor, descreva sua solicitação.")
            )
            return

        logger.info("[TEAMS BOT] conv=%s | input=%s", conversation_id, user_text[:100])

        # Typing indicator
        await turn_context.send_activity(Activity(type="typing"))

        # Retrieve conversation history
        history = self._history.setdefault(conversation_id, [])

        try:
            response = self._orchestrator.invoke(user_text, chat_history=history)
        except Exception as exc:
            logger.exception("Orchestrator error: %s", exc)
            response = f"❌ Erro interno: {exc}"

        # Persist the exchange in history
        from langchain_core.messages import HumanMessage, AIMessage  # type: ignore
        history.append(HumanMessage(content=user_text))
        history.append(AIMessage(content=response))

        await turn_context.send_activity(MessageFactory.text(response))


def create_app(orchestrator: Any) -> web.Application:
    """Build and return the aiohttp application.

    Args:
        orchestrator: A BusinessOrchestrator instance.

    Returns:
        Configured aiohttp Application.
    """
    from business.config import CONFIG

    settings = BotFrameworkAdapterSettings(
        app_id=CONFIG.teams.app_id,
        app_password=CONFIG.teams.app_password,
    )
    adapter = BotFrameworkAdapter(settings)
    bot = BusinessBot(orchestrator)

    async def messages(req: web.Request) -> web.Response:
        if req.content_type != "application/json":
            return web.Response(status=415, text="Unsupported Media Type")

        body = await req.json()
        activity = Activity().deserialize(body)
        auth_header = req.headers.get("Authorization", "")

        try:
            response = await adapter.process_activity(activity, auth_header, bot.on_turn)
            if response:
                return web.json_response(data=response.body, status=response.status)
            return web.Response(status=201)
        except Exception as exc:
            logger.exception("Adapter error: %s", exc)
            return web.Response(status=500, text="Internal server error")

    app = web.Application()
    app.router.add_post("/api/messages", messages)
    return app


def run_bot(orchestrator: Any, port: Optional[int] = None) -> None:
    """Start the Teams bot HTTP server.

    Args:
        orchestrator: A BusinessOrchestrator instance.
        port: TCP port to listen on (defaults to CONFIG.teams.port).
    """
    from business.config import CONFIG

    listen_port = port or CONFIG.teams.port
    app = create_app(orchestrator)
    logger.info("Business Teams Bot starting on port %d", listen_port)
    web.run_app(app, host="0.0.0.0", port=listen_port)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    from business.config import CONFIG
    from langchain_openai import ChatOpenAI  # type: ignore
    from business.orchestrator.chief_architect import create_business_orchestrator

    llm = ChatOpenAI(
        model=CONFIG.llm.model,
        temperature=CONFIG.llm.temperature,
        api_key=CONFIG.llm.api_key,
    )
    orc = create_business_orchestrator(llm)
    run_bot(orc)
