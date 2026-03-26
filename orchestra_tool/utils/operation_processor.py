"""
Utilitário para processar o arquivo de operações (clone/update).
"""
import json
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from orchestra_tool.models.results import OperationContext
from orchestra_tool.services.clone_service import CloneService
from orchestra_tool.services.update_service import UpdateService

logger = logging.getLogger(__name__)

def process_operations(
    file_path: Path,
    clone_service: CloneService,
    update_service: UpdateService,
    context: OperationContext,
) -> None:
    """Lê o arquivo Excel e executa clone ou update para cada linha."""
    data = pd.read_excel(file_path)
    for _, row in data.iterrows():
        operation_type: str = str(row.iloc[0]).strip().lower()
        business_key: str = str(row.iloc[1])
        fert: str = str(row.iloc[2])
        forced_user_requirements: Optional[dict] = None

        if len(row) > 3 and isinstance(row.iloc[3], str):
            try:
                forced_user_requirements = json.loads(row.iloc[3])
            except json.JSONDecodeError:
                logger.warning("forced_user_requirements inválido na linha: %s", row)

        if operation_type == "clone":
            clone_service.clone(business_key, fert, forced_user_requirements, context)
        elif operation_type == "update":
            update_service.update(business_key, fert, forced_user_requirements, context)
        else:
            logger.warning("Operação desconhecida ignorada: %s", operation_type)


def process_fert_link(file_path: Path, fert_link_service, context: OperationContext) -> None:
    """Lê o arquivo Excel e executa o vínculo de FERT para cada linha."""
    data = pd.read_excel(file_path)
    for _, row in data.iterrows():
        new_business_key: str = str(row.iloc[1])
        fert: str = str(row.iloc[3])
        fert_link_service.link(new_business_key, fert, context)


def process_compare(file_path: Path, compare_service, context: OperationContext) -> None:
    """Lê o arquivo Excel e executa a comparação para cada linha."""
    data = pd.read_excel(file_path)
    for _, row in data.iterrows():
        new_business_key: str = str(row.iloc[1])
        fert: str = str(row.iloc[3])
        compare_service.compare(new_business_key, fert, context)