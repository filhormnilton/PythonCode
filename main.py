"""
Ponto de entrada da aplicação Orchestra Tool.

Uso:
    python main.py --mode operations
    python main.py --mode fert_link
    python main.py --mode compare
    python main.py --mode all
"""
import argparse
import logging
import sys

from orchestra_tool.api.function_client import FunctionApiClient
from orchestra_tool.api.model_client import ModelApiClient
from orchestra_tool.config import API_CONFIG, PATH_CONFIG
from orchestra_tool.models.results import OperationContext
from orchestra_tool.services.clone_service import CloneService
from orchestra_tool.services.compare_service import CompareService
from orchestra_tool.services.fert_link_service import FertLinkService
from orchestra_tool.services.update_service import UpdateService
from orchestra_tool.utils.excel_writer import save_all
from orchestra_tool.utils.operation_processor import (
    process_compare,
    process_fert_link,
    process_operations,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

def build_services():
    model_client = ModelApiClient(API_CONFIG)
    function_client = FunctionApiClient(API_CONFIG)
    return (
        CloneService(model_client, function_client),
        UpdateService(model_client, function_client),
        FertLinkService(model_client, function_client),
        CompareService(model_client),
    )

def run_operations(context: OperationContext, clone_svc, update_svc) -> None:
    path = PATH_CONFIG.input_operations
    logger.info("Processando operações: %s", path)
    process_operations(path, clone_svc, update_svc, context)
    save_all(context, PATH_CONFIG)

def run_fert_link(context: OperationContext, fert_svc) -> None:
    path = PATH_CONFIG.input_fert_link
    logger.info("Processando fert_link: %s", path)
    process_fert_link(path, fert_svc, context)
    save_all(context, PATH_CONFIG)

def run_compare(context: OperationContext, compare_svc) -> None:
    path = PATH_CONFIG.input_fert_link
    logger.info("Processando compare: %s", path)
    process_compare(path, compare_svc, context)
    save_all(context, PATH_CONFIG)

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Orchestra Tool — Gerenciamento de configurações via API"
    )
    parser.add_argument(
        "--mode",
        choices=["operations", "fert_link", "compare", "all"],
        default="operations",
        help="Modo de execução (default: operations)",
    )
    args = parser.parse_args()

    clone_svc, update_svc, fert_svc, compare_svc = build_services()
    context = OperationContext()

    try:
        if args.mode in ("operations", "all"):
            run_operations(context, clone_svc, update_svc)
        if args.mode in ("fert_link", "all"):
            run_fert_link(context, fert_svc)
        if args.mode in ("compare", "all"):
            run_compare(context, compare_svc)
    except FileNotFoundError as exc:
        logger.error("Arquivo não encontrado: %s", exc)
        sys.exit(1)
    except Exception:
        logger.exception("Erro inesperado durante a execução")
        sys.exit(1)

if __name__ == "__main__":
    main()