"""
Servico responsavel por vincular FERTs as configuracoes.
"""
import logging

from orchestra_tool.api.function_client import FunctionApiClient
from orchestra_tool.api.model_client import ModelApiClient
from orchestra_tool.models.results import LinkedFert, OperationContext

logger = logging.getLogger(__name__)


class FertLinkService:
    def __init__(self, model_client: ModelApiClient, function_client: FunctionApiClient) -> None:
        self._model = model_client
        self._function = function_client

    def link(self, new_business_key: str, fert: str, context: OperationContext) -> None:
        internal_id = self._model.fetch_internal_id(new_business_key)
        if not internal_id:
            logger.warning("Internal ID nao encontrado para business key: %s", new_business_key)
            return

        if self._try_related_to(fert, internal_id, new_business_key, context):
            return

        self._try_product_code_mapping(fert, internal_id, new_business_key, context)

    def _try_related_to(self, fert: str, internal_id: str, new_business_key: str, context: OperationContext) -> bool:
        records = self._model.search_related_to(fert)
        if not records:
            return False

        for record in records:
            relationships: dict = record.get("relationships", {})
            if not self._is_related_to_match(relationships, fert):
                continue

            record_id = record.get("id")
            version = record.get("version")
            generated_from_key, generated_from_data = self._find_generated_from(relationships)

            if not (record_id and version and generated_from_key):
                if record_id:
                    logger.warning("GENERATED_FROM nao encontrado no registro %s", record_id)
                    context.linked_ferts.append(LinkedFert(new_business_key, internal_id, fert, "found in related_to"))
                    return True
                continue

            generated_from_hash = (
                generated_from_data.get("properties", {}).get("DesignedHash") if generated_from_data else None
            )

            patch_payload = {
                "version": str(version),
                "relationships": {
                    str(generated_from_key): None,
                    "$1": {
                        "type": "GENERATED_FROM",
                        "properties": {"DesignedHash": str(generated_from_hash), "Version": 2},
                        "target": {"id": str(internal_id), "type": "ENTITY"},
                    },
                },
            }

            patch_resp = self._model.patch_record(record_id, patch_payload)
            if patch_resp is None:
                return False

            success = self._function.sap_update_item(
                configuration_id=internal_id, item_id=record_id, material_id=fert,
            )

            if success:
                context.linked_ferts.append(LinkedFert(new_business_key, internal_id, fert, "updated related_to link"))
                return True

        return False

    def _try_product_code_mapping(self, fert: str, internal_id: str, new_business_key: str, context: OperationContext) -> None:
        mapping = self._model.search_product_code_mapping(fert)

        if mapping:
            record_id = mapping.get("id")
            version = mapping.get("version")
            if record_id and version:
                success = self._model.update_product_code_mapping(record_id, version, internal_id)
                status = "updated pccm link" if success else "pccm update error"
                context.linked_ferts.append(LinkedFert(new_business_key, internal_id, fert, status))
                return

        created = self._model.create_product_code_mapping(fert, internal_id)
        status = "created pccm link" if created else "pccm create error"
        context.linked_ferts.append(LinkedFert(new_business_key, internal_id, fert, status))

    @staticmethod
    def _is_related_to_match(relationships: dict, fert: str) -> bool:
        for relation in relationships.values():
            target = relation.get("target", {})
            if (
                relation.get("type") == "RELATED_TO"
                and target.get("type") == "SAP"
                and target.get("subtype") == "MATERIAL"
                and str(target.get("id")) == str(fert)
            ):
                return True
        return False

    @staticmethod
    def _find_generated_from(relationships: dict):
        for key, value in relationships.items():
            if value.get("type") == "GENERATED_FROM":
                return key, value
        return None, None

"""
