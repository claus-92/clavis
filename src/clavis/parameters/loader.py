import json
from pathlib import Path

from clavis.schemas.parameters import ParameterDefinitions


def definitions_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "parameter_definitions"


def load_parameter_definitions(name: str) -> ParameterDefinitions:
    path = definitions_dir() / f"{name}.json"
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if hasattr(ParameterDefinitions, "model_validate"):
        return ParameterDefinitions.model_validate(data)
    return ParameterDefinitions.parse_obj(data)
