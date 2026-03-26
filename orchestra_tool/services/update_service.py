"""
Servico responsavel pela atualizacao de configuracoes.
"""
import logging
from typing import Optional

from orchestra_tool.api.function_client import FunctionApiClient
from orchestra_tool.api.model_client import ModelApiClient
from orchestra_tool.models.results import (
    BrokenConstraint, DifferenceConf, DifferenceItem, OperationContext, UpdateResult,
)
from orchestra_tool.utils.constraint_parser import parse_broken_constraints

logger = logging.getLogger(__name__)


class UpdateService:
    def __init__(self, model_client: ModelApiClient, function_client: FunctionApiClient) -> None:
        self._model = model_client
        self._function = function_client

    def update(
        self,
        business_key: str,
        fert: str,
        forced_user_requirements: Optional[dict],
        context: OperationContext,
    ) -> None:
        internal_id = self._model.fetch_internal_id(business_key)
        if not internal_id:
            logger.warning("Internal ID nao encontrado para: %s", business_key)
            return

        result = self._function.update_configuration(
            data_record_id=internal_id,
            forced_user_requirements=forced_user_requirements,
        )

        if result is None:
            context.updates.append(
                UpdateResult(business_key=business_key, internal_id=internal_id, sap_item=fert, status="Erro ao atualizar")
            )
            return

        configuration_diff: dict = result.get("configurationDiff", {})
        item_diff: dict = result.get("itemDiff", {})
        broken_constraints_raw: list = result.get("brokenConstraints", [])

        for attribute, value in configuration_diff.items():
            context.differences_conf.append(
                DifferenceConf(
                    business_key=business_key, internal_id=internal_id, sap_item=fert,
                    attribute=attribute, value_s=value.get("s"), value_t=value.get("t"),
                )
            )

        for attribute, value in item_diff.items():
            context.differences_item.append(
                DifferenceItem(
                    business_key=business_key, internal_id=internal_id, sap_item=fert,
                    attribute=attribute, value_s=value.get("s"), value_t=value.get("t"),
                )
            )

        parsed_constraints = parse_broken_constraints(broken_constraints_raw, business_key, internal_id, fert)
        context.broken_constraints.extend(parsed_constraints)

        context.updates.append(
            UpdateResult(business_key=business_key, internal_id=internal_id, sap_item=fert, status="updated")
        )
        logger.info("Atualizacao concluida: %s", internal_id)

"""
