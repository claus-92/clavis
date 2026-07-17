from typing import Any

from clavis.core.errors import InvalidParameterError
from clavis.schemas import ParameterDefinition, ParameterDefinitions


SUPPORTED_TYPES = {"boolean", "integer", "number", "string"}


def validate_parameter_definitions(definitions: ParameterDefinitions) -> None:
    for scope, scope_definitions in (
        ("generalParameters", definitions.generalParameters),
        ("groupParameters", definitions.groupParameters),
        ("channelParameters", definitions.channelParameters),
    ):
        names: set[str] = set()
        for definition in scope_definitions:
            if definition.name in names:
                raise InvalidParameterError(f"Duplicate parameter in {scope}: {definition.name}")
            names.add(definition.name)
            _validate_definition(definition)


def validate_options(options: dict[str, Any], definitions: list[ParameterDefinition]) -> None:
    by_name = {definition.name: definition for definition in definitions}
    for key, value in options.items():
        definition = by_name.get(key)
        if definition is None:
            raise InvalidParameterError(f"Unknown parameter: {key}")
        _validate_definition(definition)
        _validate_value(key, value, definition)


def _validate_definition(definition: ParameterDefinition) -> None:
    if definition.type not in SUPPORTED_TYPES:
        raise InvalidParameterError(f"Unsupported type for {definition.name}: {definition.type}")
    if (definition.minimum is not None or definition.maximum is not None) and definition.type not in {"integer", "number"}:
        raise InvalidParameterError(f"Numeric bounds require integer or number type: {definition.name}")
    if definition.minimum is not None and definition.maximum is not None and definition.minimum > definition.maximum:
        raise InvalidParameterError(f"Minimum exceeds maximum for parameter: {definition.name}")

    _validate_value(definition.name, definition.defaultValue, definition, check_options=False)
    for option in definition.options:
        _validate_value(definition.name, option, definition, check_options=False)
    if definition.options and not _contains_strict(definition.defaultValue, definition.options):
        raise InvalidParameterError(f"Default value is not an option for {definition.name}: {definition.defaultValue}")


def _validate_value(key: str, value: Any, definition: ParameterDefinition, *, check_options: bool = True) -> None:
    if not _matches_type(value, definition.type):
        raise InvalidParameterError(f"Invalid type for {key}: expected {definition.type}")
    if check_options and definition.options and not _contains_strict(value, definition.options):
        raise InvalidParameterError(f"Invalid value for {key}: {value}")
    if definition.minimum is not None and value < definition.minimum:
        raise InvalidParameterError(f"Value for {key} is below minimum {definition.minimum}: {value}")
    if definition.maximum is not None and value > definition.maximum:
        raise InvalidParameterError(f"Value for {key} is above maximum {definition.maximum}: {value}")


def _matches_type(value: Any, declared_type: str) -> bool:
    if declared_type == "boolean":
        return isinstance(value, bool)
    if declared_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if declared_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if declared_type == "string":
        return isinstance(value, str)
    return False


def _contains_strict(value: Any, options: list[Any]) -> bool:
    return any(type(value) is type(option) and value == option for option in options)
