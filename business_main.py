"""
business_main.py — Entry point for the Business Multi-Agent system.

Usage:
    # Interactive CLI mode (no Teams)
    python business_main.py --mode cli

    # Microsoft Teams Bot mode (requires Bot Framework credentials)
    python business_main.py --mode teams

    # One-shot execution
    python business_main.py --mode once --request "Crie uma user story para login com SSO"

    # Ingest documents from a URL into the knowledge base
    python business_main.py --mode ingest --ingest-url https://docs.example.com
    python business_main.py --mode ingest --ingest-url https://docs.example.com --ingest-depth 1 --ingest-tags "api,docs"
"""
import argparse
import logging
import os
import re
import sys

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def _build_llm():
    """Instantiate the LLM from configuration."""
    from Business.config import CONFIG
    try:
        from langchain_openai import ChatOpenAI  # type: ignore
    except ImportError:
        logger.error("langchain-openai is not installed. Run: pip install langchain-openai")
        sys.exit(1)

    return ChatOpenAI(
        model=CONFIG.llm.model,
        temperature=CONFIG.llm.temperature,
        api_key=CONFIG.llm.api_key,
    )


def run_cli(orchestrator) -> None:
    """Interactive command-line loop."""
    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║  Business Multi-Agent — Chief Architect 'frysda' (Negócios) ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print("Type your request and press Enter. Type 'exit' or 'quit' to stop.\n")

    from langchain_core.messages import HumanMessage, AIMessage
    history = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "sair"):
            print("Goodbye!")
            break

        response = orchestrator.invoke(user_input, chat_history=history)
        history.append(HumanMessage(content=user_input))
        history.append(AIMessage(content=response))
        print(f"\nfrysda: {response}\n")
        _open_charts_in_response(response)


def _open_charts_in_response(text: str) -> None:
    """Detect PNG file paths in the response and open them with the OS viewer."""
    paths = re.findall(r'[A-Za-z]:[\\\/][^\s\'"]+\.png', text)
    for path in paths:
        path = path.replace("/", os.sep)
        if os.path.isfile(path):
            logger.info("[CLI] Opening chart: %s", path)
            try:
                os.startfile(path)  # Windows default image viewer
            except Exception as exc:
                logger.warning("[CLI] Could not open chart: %s", exc)


def run_once(orchestrator, request: str) -> None:
    """Run a single request and print the result."""
    response = orchestrator.invoke(request)
    print(response)
    _open_charts_in_response(response)


def run_teams(orchestrator) -> None:
    """Start the Microsoft Teams bot server."""
    from Business.teams_bot.bot import run_bot
    run_bot(orchestrator)


def run_ingest(url: str, depth: int = 0, tags: str = "") -> None:
    """Fetch URL(s) and ingest page content into the local knowledge base.

    Args:
        url:   Root URL to fetch and ingest.
        depth: How many levels of same-domain links to follow (0 = only the given URL).
        tags:  Comma-separated tags to attach to every ingested entry.
    """
    try:
        import requests  # type: ignore
        from bs4 import BeautifulSoup  # type: ignore
    except ImportError:
        logger.error("requests/beautifulsoup4 not installed. Run: pip install requests beautifulsoup4")
        sys.exit(1)

    from urllib.parse import urljoin, urlparse
    from Business.mcp.api_knowledge_base import add_knowledge_entry

    headers = {"User-Agent": "Mozilla/5.0 (compatible; BusinessAgent/1.0)"}
    root_netloc = urlparse(url).netloc
    visited: set = set()

    def _ingest_one(target_url: str, current_depth: int) -> None:
        if target_url in visited:
            return
        visited.add(target_url)
        logger.info("[ingest] Fetching: %s", target_url)

        try:
            resp = requests.get(target_url, headers=headers, timeout=15)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("[ingest] Failed to fetch %s: %s", target_url, exc)
            return

        soup = BeautifulSoup(resp.text, "html.parser")
        title_tag = soup.title
        title = title_tag.string.strip() if title_tag and title_tag.string else target_url

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        content = soup.get_text(separator="\n", strip=True)[:8000]

        result = add_knowledge_entry.invoke({
            "title": title,
            "content": content,
            "tags": tags,
            "source": target_url,
        })
        logger.info("[ingest] %s", result)
        print(f"  + {title} ({target_url})")

        if current_depth > 0:
            base = f"{urlparse(target_url).scheme}://{urlparse(target_url).netloc}"
            for a in soup.find_all("a", href=True):
                link = urljoin(base, a["href"])
                parsed = urlparse(link)
                if parsed.scheme in ("http", "https") and parsed.netloc == root_netloc:
                    _ingest_one(link, current_depth - 1)

    print(f"\n[ingest] URL: {url}  |  depth={depth}  |  tags={tags or '(nenhuma)'}\n")
    _ingest_one(url, depth)
    print(f"\n[ingest] Concluido. {len(visited)} pagina(s) processada(s).\n")


def run_devui(orchestrator, port: int = 8080) -> None:
    """Start the dev/test web UI that simulates Teams group conversations.

    ⚠️  DEV/TEST ONLY — not intended for production deployment.
    Requires: pip install -r dev_ui/requirements-test.txt
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "dev_ui.server",
        os.path.join(os.path.dirname(__file__), "dev_ui", "server.py"),
    )
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    module._orchestrator = orchestrator
    logger.info("Dev UI iniciando em http://localhost:%d", port)
    import uvicorn
    uvicorn.run(module.app, host="0.0.0.0", port=port, log_level="info")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Business Multi-Agent System — frysda orchestrator"
    )
    parser.add_argument(
        "--mode",
        choices=["cli", "teams", "once", "devui", "ingest"],
        default="cli",
        help="Execution mode (default: cli)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Porta HTTP para --mode devui (padrão: 8080)",
    )
    parser.add_argument(
        "--request",
        default="",
        help="Request string for --mode once",
    )
    parser.add_argument(
        "--agents",
        default="",
        help=(
            "Comma-separated list of agents to activate. "
            "Valid values: docs,slides,architect,jira,web,process,miro. "
            "Omit to enable all agents. Example: --agents jira,web"
        ),
    )
    parser.add_argument(
        "--ingest-url",
        default="",
        metavar="URL",
        help="URL to fetch and ingest into the knowledge base (requires --mode ingest)",
    )
    parser.add_argument(
        "--ingest-depth",
        type=int,
        default=0,
        metavar="N",
        help="Number of same-domain link levels to crawl (default: 0 = only the given URL)",
    )
    parser.add_argument(
        "--ingest-tags",
        default="",
        metavar="TAGS",
        help="Comma-separated tags for ingested entries (e.g. 'api,docs')",
    )
    args = parser.parse_args()

    if args.mode == "ingest":
        if not args.ingest_url:
            logger.error("--ingest-url é obrigatório quando usando --mode ingest")
            sys.exit(1)
        run_ingest(args.ingest_url, depth=args.ingest_depth, tags=args.ingest_tags)
        return

    enabled_agents = (
        [a.strip() for a in args.agents.split(",") if a.strip()]
        if args.agents
        else None
    )

    from Business.orchestrator.chief_architect import create_business_orchestrator
    llm = _build_llm()
    orchestrator = create_business_orchestrator(llm, enabled_agents=enabled_agents)

    if args.mode == "cli":
        run_cli(orchestrator)
    elif args.mode == "teams":
        run_teams(orchestrator)
    elif args.mode == "devui":
        run_devui(orchestrator, port=args.port)
    elif args.mode == "once":
        if not args.request:
            logger.error("--request is required when using --mode once")
            sys.exit(1)
        run_once(orchestrator, args.request)


if __name__ == "__main__":
    main()
