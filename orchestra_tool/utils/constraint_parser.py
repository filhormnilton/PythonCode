"""
Utilitario para parsing de broken constraints retornadas pelas APIs.
"""
import logging
from typing import Optional

from orchestra_tool.models.results import BrokenConstraint

logger = logging.getLogger(__name__)


def parse_broken_constraints(
    raw_constraints: list[str],
    business_key: str,
    internal_id: Optional[str],
    sap_item: str,
) -> list[BrokenConstraint]:
    results: list[BrokenConstraint] = []
    for constraint in raw_constraints:
        parts = constraint.split(" - ")
        name = behavior = layer = None

        for part in parts:
            if part.startswith("Name:"):
                name = part.split(": ", 1)[1].strip()
            elif part.startswith("Behavior:"):
                behavior = part.split(": ", 1)[1].strip()
            elif part.startswith("Internal Default Layer:"):
                layer = part.split(": ", 1)[1].strip()

        if name and behavior and layer:
            results.append(
                BrokenConstraint(
                    business_key=business_key,
                    internal_id=internal_id or "",
                    sap_item=sap_item,
                    name=name,
                    behavior=behavior,
                    layer=layer,
                )
            )
        else:
            logger.warning("Constraint incompleta ignorada: %s", constraint)

    return results

"""
