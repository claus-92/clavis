from typing import Any

from clavis.core.errors import InvalidParameterError
from clavis.schemas.parameters import ParameterDefinition


def validate_options(options: dict[str, Any], definitions: list[ParameterDefinition]) -> None:
    by_name = {definition.name: definition for definition in definitions}
    for key, value in options.items():
        definition = by_name.get(key)
        if definition is None:
            raise InvalidParameterError(f"Unknown parameter: {key}")
        if definition.options and value not in definition.options:
            raise InvalidParameterError(f"Invalid value for {key}: {value}")
