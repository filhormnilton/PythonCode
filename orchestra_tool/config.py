"""
Configurações centralizadas do projeto Orchestra Tool.
Utiliza variáveis de ambiente para flexibilidade entre ambientes.
"""
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ApiConfig:
    model_url: str
    function_api_url: str
    collection_configuration: str = "0FHTNQEZKG0KW"
    collection_related_to: str = "0G385EYT8R0FN"
    collection_product_code_mapping: str = "0FZ8EYPCE2MFK"
    verify_ssl: bool = False


dataclass(frozen=True)
class PathConfig:
    base_dir: Path
    input_operations: Path
    input_fert_link: Path
    output_cloned: Path
    output_update: Path
    output_differences: Path
    output_diff_conf: Path
    output_diff_item: Path
    output_broken_constraints: Path
    output_linked: Path
    output_duplicated: Path


def load_api_config() -> ApiConfig:
    env = os.getenv("ORCHESTRA_ENV", "beta").lower()
    urls = {
        "beta": {
            "model": "http://internal-a046aa95f9fa5474ab0c7fb7f99f5a22-997522895.us-east-1.elb.amazonaws.com",
            "function": "http://internal-a7730541728724cd487486f4b23988cc-633213069.us-east-1.elb.amazonaws.com",
        },
        "prd": {
            "model": "https://model-api.orchestra.weg.net",
            "function": "https://functions.orchestra.weg.net",
        },
    }
    selected = urls.get(env, urls["beta"])
    return ApiConfig(
        model_url=os.getenv("MODEL_URL", selected["model"]),
        function_api_url=os.getenv("FUNCTION_API_URL", selected["function"]),
        verify_ssl=os.getenv("VERIFY_SSL", "false").lower() == "true",
    )


def load_path_config() -> PathConfig:
    base = Path(os.getenv("OUTPUT_DIR", "C:/Users/niltonf/dev"))
    return PathConfig(
        base_dir=base,
        input_operations=base / "teste.xlsx",
        input_fert_link=base / "fert_link.xlsx",
        output_cloned=base / "cloned_keys.xlsx",
        output_update=base / "update.xlsx",
        output_differences=base / "configuration_differences.xlsx",
        output_diff_conf=base / "configuration_differences_form.xlsx",
        output_diff_item=base / "item_differences_form.xlsx",
        output_broken_constraints=base / "broken_constraints.xlsx",
        output_linked=base / "linked.xlsx",
        output_duplicated=base / "duplicated.xlsx",
    )


# Instâncias globais prontas para uso
API_CONFIG = load_api_config()
PATH_CONFIG = load_path_config()