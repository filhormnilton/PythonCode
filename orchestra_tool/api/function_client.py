"""
Cliente HTTP para a Function API do Orchestra.
"""
import logging
from typing import Any, Optional

import requests
from requests import Response

from orchestra_tool.config import ApiConfig

logger = logging.getLogger(__name__)

_CLONE_FUNCTION = "functions.net.weg.orchestra.configuration.CloneConfiguration"
_UPDATE_FUNCTION = "functions.net.weg.orchestra.configuration.UpdateConfiguration"
_SAP_UPDATE_FUNCTION = "functions.net.weg.orchestra.system.itemmanager.sap.functions.SapUpdateItem"


class FunctionApiClient:
    def __init__(self, config: ApiConfig) -> None:
        self._base_url = config.function_api_url
        self._verify_ssl = config.verify_ssl
        self._session = requests.Session()

    def _post(self, function_name: str, payload: dict) -> Response:
        url = f"{self._base_url}/api/v1/function/execute/{function_name}"
        return self._session.post(url, json=payload, verify=self._verify_ssl)

    def clone_configuration(
        self,
        original_configuration_id: str,
        forced_user_requirements: Optional[dict] = None,
        using_new_configurable: bool = True,
    ) -> Optional[dict]:
        payload: dict[str, Any] = {
            "originalConfigurationId": original_configuration_id,
            "usingNewConfigurable": using_new_configurable,
        }
        if forced_user_requirements:
            payload["forcedUserRequirements"] = forced_user_requirements
        response = self._post(_CLONE_FUNCTION, payload)
        if response.status_code == 200:
            return response.json()
        logger.error("Erro ao clonar configuracao %s: %s", original_configuration_id, response.content)
        return None

    def update_configuration(
        self,
        data_record_id: str,
        forced_user_requirements: Optional[dict] = None,
        autofix: bool = True,
        simulate: bool = False,
        re_enable_constraints: bool = True,
    ) -> Optional[dict]:
        payload: dict[str, Any] = {
            "dataRecordId": data_record_id,
            "autofix": autofix,
            "simulate": simulate,
            "reEnableConstraints": re_enable_constraints,
        }
        if forced_user_requirements:
            payload["forcedUserRequirements"] = forced_user_requirements
        response = self._post(_UPDATE_FUNCTION, payload)
        if response.status_code == 200:
            return response.json()
        logger.error("Erro ao atualizar configuracao %s: %s", data_record_id, response.content)
        return None

    def sap_update_item(
        self,
        configuration_id: str,
        item_id: str,
        material_id: str,
        simulate: bool = False,
    ) -> bool:
        payload = {
            "configurationId": configuration_id,
            "itemId": item_id,
            "materialId": material_id,
            "simulate": simulate,
        }
        response = self._post(_SAP_UPDATE_FUNCTION, payload)
        if response.ok:
            logger.info("SAP item atualizado: %s -> %s -> %s", material_id, item_id, configuration_id)
            return True
        logger.error("Erro SAP update %s: status=%s body=%s", item_id, response.status_code, response.text)
        return False

"""
