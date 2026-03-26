"""
Servico responsavel pelo clone de configuracoes.
"""
import logging
from typing import Optional

from orchestra_tool.api.function_client import FunctionApiClient
from orchestra_tool.api.model_client import ModelApiClient
from orchestra_tool.models.results import BrokenConstraint, ClonedKey, OperationContext
from orchestra_tool.utils.constraint_parser import parse_broken_constraints

logger = logging.getLogger(__name__)


class CloneService:
    def __init__(self, model_client: ModelApiClient, function_client: FunctionApiClient) -> None:
        self._model = model_client
        self._function = function_client

    def clone(
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

        logger.info("Clonando | internal_id=%s | fert=%s | business_key=%s", internal_id, fert, business_key)

        clone_result = self._function.clone_configuration(
            original_configuration_id=internal_id,
            forced_user_requirements=forced_user_requirements,
        )

        if clone_result is None:
            context.cloned_keys.append(
                ClonedKey(
                    business_key=business_key, new_business_key=None, internal_id=None,
                    sap_item=fert, voltage_code=None, package_code=None, rated_power=None,
                    frame_size=None, excitation_type=None, im_code=None, flange=None,
                    disc=None, tbox_raw_material=None, avr_model=None, avr_installation=None,
                    status="Erro ao clonar",
                )
            )
            return

        new_id = clone_result.get("id")
        record = self._model.get_record(new_id) if new_id else {}
        data = record or {} 

        broken_constraints_raw = data.get("brokenConstraints", [])
        parsed_constraints = parse_broken_constraints(broken_constraints_raw, business_key, new_id, fert)
        context.broken_constraints.extend(parsed_constraints)

        new_bk = self._model.get_business_key(new_id) if new_id else None

        cloned = ClonedKey(
            business_key=business_key,
            new_business_key=new_bk,
            internal_id=new_id,
            sap_item=fert,
            voltage_code=self._deep_get(data, "data.basicParameters.application.voltageCode"),
            package_code=self._deep_get(data, "data.basicParameters.application.coreLength"),
            rated_power=self._deep_get(data, "data.basicParameters.ratedPower"),
            frame_size=self._deep_get(data, "data.basicParameters.frameSize"),
            excitation_type=self._deep_get(data, "data.designed.avrSet.avr.excitationType"),
            im_code=self._deep_get(data, "data.mounting.imCode1"),
            flange=self._deep_get(data, "data.mounting.flange"),
            disc=self._deep_get(data, "data.workaround.falsePositiveOptional.flywheelCode"),
            tbox_raw_material=self._deep_get(data, "data.designed.tboxStatorSet.tbox.rawMat"),
            avr_model=self._deep_get(data, "data.designed.avrSet.avr.model"),
            avr_installation=self._deep_get(data, "data.designed.avrSet.installationLocal"),
            status="cloned",
        )
        context.cloned_keys.append(cloned)
        logger.info("Clone criado com sucesso: %s", new_id)

    @staticmethod
    def _deep_get(data: dict, path: str) -> Optional[object]:
        keys = path.split(".")
        node = data
        for key in keys:
            if not isinstance(node, dict):
                return None
            node = node.get(key)
        return node

"""
