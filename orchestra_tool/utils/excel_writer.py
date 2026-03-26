"""
Utilitario para persistir os resultados em arquivos Excel.
"""
import logging
from pathlib import Path

import pandas as pd

from orchestra_tool.config import PathConfig
from orchestra_tool.models.results import OperationContext

logger = logging.getLogger(__name__)


def _write(df: pd.DataFrame, path: Path, **kwargs) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_excel(path, index=False, **kwargs)
        logger.info("Arquivo salvo: %s", path)
    except Exception:
        logger.exception("Falha ao salvar arquivo: %s", path)


def save_all(context: OperationContext, paths: PathConfig) -> None:
    _write(
        pd.DataFrame(
            [r.to_row() for r in context.cloned_keys],
            columns=context.cloned_keys[0].columns() if context.cloned_keys else [],
        ),
        paths.output_cloned,
    )
    _write(
        pd.DataFrame(
            [r.to_row() for r in context.updates],
            columns=context.updates[0].columns() if context.updates else [],
        ),
        paths.output_update,
    )
    _write(
        pd.DataFrame(
            [r.to_row() for r in context.differences_conf],
            columns=context.differences_conf[0].columns() if context.differences_conf else [],
        ),
        paths.output_diff_conf,
        na_rep="-",
    )
    _write(
        pd.DataFrame(
            [r.to_row() for r in context.differences_item],
            columns=context.differences_item[0].columns() if context.differences_item else [],
        ),
        paths.output_diff_item,
        na_rep="-",
    )
    _write(
        pd.DataFrame(
            [r.to_row() for r in context.broken_constraints],
            columns=context.broken_constraints[0].columns() if context.broken_constraints else [],
        ),
        paths.output_broken_constraints,
        na_rep="-",
    )
    _write(
        pd.DataFrame(
            [r.to_row() for r in context.linked_ferts],
            columns=context.linked_ferts[0].columns() if context.linked_ferts else [],
        ),
        paths.output_linked,
    )
    _write(
        pd.DataFrame(
            [r.to_row() for r in context.duplicated_ferts],
            columns=context.duplicated_ferts[0].columns() if context.duplicated_ferts else [],
        ),
        paths.output_duplicated,
    )

"""
