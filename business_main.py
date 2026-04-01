"""
business_main.py — Entry point for the Business Multi-Agent system.

Usage:
    # Interactive CLI mode (no Teams)
    python business_main.py --mode cli

    # Microsoft Teams Bot mode (requires Bot Framework credentials)
    python business_main.py --mode teams

    # One-shot execution
    python business_main.py --mode once --request "Crie uma user story para login com SSO"
"""
import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def _build_llm():
    """Instantiate the LLM from configuration."""
    from business.config import CONFIG
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


def run_once(orchestrator, request: str) -> None:
    """Run a single request and print the result."""
    response = orchestrator.invoke(request)
    print(response)


def run_teams(orchestrator) -> None:
    """Start the Microsoft Teams bot server."""
    from business.teams_bot.bot import run_bot
    run_bot(orchestrator)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Business Multi-Agent System — frysda orchestrator"
    )
    parser.add_argument(
        "--mode",
        choices=["cli", "teams", "once"],
        default="cli",
        help="Execution mode (default: cli)",
    )
    parser.add_argument(
        "--request",
        default="",
        help="Request string for --mode once",
    )
    args = parser.parse_args()

    from business.orchestrator.chief_architect import create_business_orchestrator
    llm = _build_llm()
    orchestrator = create_business_orchestrator(llm)

    if args.mode == "cli":
        run_cli(orchestrator)
    elif args.mode == "teams":
        run_teams(orchestrator)
    elif args.mode == "once":
        if not args.request:
            logger.error("--request is required when using --mode once")
            sys.exit(1)
        run_once(orchestrator, args.request)


if __name__ == "__main__":
    main()
