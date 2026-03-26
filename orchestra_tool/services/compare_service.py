"""
Servico responsavel por identificar duplicacoes entre FERT e configuracoes.
"""
import logging

from orchestra_tool.api.model_client import ModelApiClient
from orchestra_tool.models.results import DuplicatedFert, OperationContext

logger = logging.getLogger(__name__)


class CompareService:
    def __init__(self, model_client: ModelApiClient) -> None:
        self._model = model_client

    def compare(self, new_business_key: str, fert: str, context: OperationContext) -> None:
        internal_id = self._model.fetch_internal_id(new_business_key)
        record_id = self._find_related_to_record_id(fert)
        pccm_id = self._find_pccm_id(fert)

        if record_id and pccm_id:
            context.duplicated_ferts.append(
                DuplicatedFert(
                    internal_id=internal_id or "",
                    record_id=record_id,
                    pccm_id=pccm_id,
                    new_business_key=new_business_key,
                    sap_item=fert,
                    linked="duplicated",
                )
            )

    def _find_related_to_record_id(self, fert: str) -> str | None:
        records = self._model.search_related_to(fert)
        if not records:
            return None
        for record in records:
            relationships = record.get("relationships", {})
            for relation in relationships.values():
                target = relation.get("target", {})
                if (
                    relation.get("type") == "RELATED_TO"
                    and target.get("type") == "SAP"
                    and target.get("subtype") == "MATERIAL"
                    and str(target.get("id")) == str(fert)
                ):
                    return record.get("id")
        return None

    def _find_pccm_id(self, fert: str) -> str | None:
        mapping = self._model.search_product_code_mapping(fert)
        return mapping.get("id") if mapping else None

"""
