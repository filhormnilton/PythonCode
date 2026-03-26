"""
Cliente HTTP para a Model API do Orchestra.
"""
import logging
from typing import Any, Optional

import requests
from requests import Response

from orchestra_tool.config import ApiConfig

logger = logging.getLogger(__name__)


class ModelApiClient:
    def __init__(self, config: ApiConfig) -> None:
        self._base_url = config.model_url
        self._verify_ssl = config.verify_ssl
        self._collection_configuration = config.collection_configuration
        self._collection_related_to = config.collection_related_to
        self._collection_product_code_mapping = config.collection_product_code_mapping
        self._session = requests.Session()

    def _get(self, path: str, **kwargs) -> Response:
        url = f"{self._base_url}{path}"
        return self._session.get(url, verify=self._verify_ssl, **kwargs)

    def _post(self, path: str, payload: dict, **kwargs) -> Response:
        url = f"{self._base_url}{path}"
        return self._session.post(url, json=payload, verify=self._verify_ssl, **kwargs)

    def _patch(self, path: str, payload: dict, **kwargs) -> Response:
        url = f"{self._base_url}{path}"
        return self._session.patch(url, json=payload, verify=self._verify_ssl, **kwargs)

    def get_business_key(self, record_id: str) -> Optional[str]:
        response = self._get(f"/api/v1/data/record/{record_id}")
        if response.status_code == 200:
            return response.json().get("metadata", {}).get("platform/business-key")
        logger.error("Erro ao buscar business_key para %s: %s", record_id, response.content)
        return None

    def fetch_internal_id(self, business_key: str) -> Optional[str]:
        path = (
            f"/api/v1/data/collection/{self._collection_configuration}"
            f"/record/business-key/{business_key}"
        )
        response = self._get(path)
        if response.status_code == 200:
            return response.json().get("id")
        logger.error("Erro ao buscar ID para business key %s: %s", business_key, response.content)
        return None

    def get_record(self, record_id: str) -> Optional[dict]:
        response = self._get(f"/api/v1/data/record/{record_id}")
        if response.status_code == 200:
            return response.json()
        logger.error("Erro ao buscar registro %s: %s", record_id, response.content)
        return None

    def patch_record(self, record_id: str, payload: dict) -> Optional[Response]:
        response = self._patch(f"/api/v1/data/record/{record_id}", payload)
        if response.status_code != 200:
            logger.error("Patch error em %s: %s", record_id, response.content)
            return None
        return response

    def create_record(self, payload: dict) -> Optional[Response]:
        response = self._post("/api/v1/data/record", payload)
        if response.status_code != 201:
            logger.error("Erro ao criar registro: %s", response.content)
            return None
        return response

    def search_related_to(self, sap_item: str) -> Optional[list[dict]]:
        path = f"/api/v1/data/collection/{self._collection_related_to}/records/search"
        payload = {
            "relationships": {
                "type": "RELATED_TO",
                "target": {"type": "SAP", "subtype": "MATERIAL", "id": str(sap_item)},
            }
        }
        response = self._post(path, payload)
        if response.status_code == 200:
            data = response.json()
            return data if isinstance(data, list) else data.get("records", [])
        logger.error("Erro ao buscar related_to para %s: %s", sap_item, response.content)
        return None

    def search_product_code_mapping(self, sap_item: str) -> Optional[dict]:
        path = (
            f"/api/v1/data/collection/{self._collection_product_code_mapping}/records/search"
        )
        payload = {"data": {"productCode": str(sap_item)}}
        response = self._post(path, payload)
        if response.status_code == 200:
            results = response.json()
            if results:
                return results[0]
        logger.warning("Nenhum mapeamento encontrado para %s", sap_item)
        return None

    def update_product_code_mapping(self, record_id: str, version: str, internal_id: str) -> bool:
        payload = {
            "version": str(version),
            "ops": [{"op": "replace", "path": "/configurationId", "value": str(internal_id)}],
        }
        response = self._patch(f"/api/v1/data/record/{record_id}", payload)
        if response and response.status_code == 200:
            return True
        logger.error("Erro ao atualizar vinculo FERT %s -> %s", record_id, internal_id)
        return False

    def create_product_code_mapping(self, sap_item: str, internal_id: str) -> bool:
        payload = {
            "dataCollectionId": self._collection_product_code_mapping,
            "type": {"revision": "1.0.0"},
            "data": {"productCode": str(sap_item), "configurationId": str(internal_id)},
        }
        response = self._post("/api/v1/data/record", payload)
        if response and response.status_code == 201:
            return True
        logger.error("Erro ao criar mapeamento FERT %s -> %s", sap_item, internal_id)
        return False


"""
