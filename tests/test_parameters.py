import pytest

from clavis.core.errors import InvalidParameterError
from clavis.parameters.validation import validate_options, validate_parameter_definitions
from clavis.schemas import ParameterDefinition, ParameterDefinitions


def definition(**overrides: object) -> ParameterDefinition:
    values: dict[str, object] = {
        "name": "value",
        "type": "integer",
        "defaultValue": 1,
        "options": [],
        "description": "Test value",
    }
    values.update(overrides)
    return ParameterDefinition(**values)


def definitions(*items: ParameterDefinition) -> ParameterDefinitions:
    return ParameterDefinitions(
        generalParameters=list(items),
        channelParameters=[],
        groupParameters=[],
    )


def test_parameter_definitions_can_be_validated() -> None:
    definitions = ParameterDefinitions(
        generalParameters=[],
        channelParameters=[{"name": "power", "type": "string", "defaultValue": "off", "options": ["on", "off"], "description": "Power"}],
        groupParameters=[],
    )

    assert definitions.channelParameters[0].name == "power"


def test_invalid_parameter_values_are_rejected() -> None:
    definitions = ParameterDefinitions(
        generalParameters=[],
        channelParameters=[{"name": "gain", "type": "integer", "defaultValue": 1, "options": [1, 2, 4, 8], "description": "Gain"}],
        groupParameters=[],
    )
    with pytest.raises(InvalidParameterError):
        validate_options({"gain": 3}, definitions.channelParameters)


@pytest.mark.parametrize(
    ("declared_type", "value"),
    [
        ("boolean", True),
        ("integer", 2),
        ("number", 2),
        ("number", 2.5),
        ("string", "two"),
    ],
)
def test_strict_parameter_types_accept_matching_values(declared_type: str, value: object) -> None:
    item = definition(type=declared_type, defaultValue=value)
    validate_options({"value": value}, [item])


@pytest.mark.parametrize(
    ("declared_type", "value"),
    [
        ("boolean", 1),
        ("integer", True),
        ("integer", 2.0),
        ("integer", "2"),
        ("number", True),
        ("string", 2),
    ],
)
def test_strict_parameter_types_reject_non_matching_values(declared_type: str, value: object) -> None:
    item = definition(type=declared_type)
    with pytest.raises(InvalidParameterError, match="Invalid type"):
        validate_options({"value": value}, [item])


@pytest.mark.parametrize("value", [0, 10])
def test_numeric_bounds_are_inclusive(value: int) -> None:
    item = definition(defaultValue=0, minimum=0, maximum=10)
    validate_options({"value": value}, [item])


@pytest.mark.parametrize("value", [-1, 11])
def test_numeric_bounds_reject_values_outside_range(value: int) -> None:
    item = definition(defaultValue=0, minimum=0, maximum=10)
    with pytest.raises(InvalidParameterError):
        validate_options({"value": value}, [item])


def test_options_use_strict_types() -> None:
    item = definition(type="integer", defaultValue=1, options=[1, 2])
    with pytest.raises(InvalidParameterError, match="Invalid type"):
        validate_options({"value": True}, [item])


@pytest.mark.parametrize(
    "item",
    [
        definition(type="unsupported"),
        definition(type="string", defaultValue="x", minimum=0),
        definition(defaultValue=1, minimum=2, maximum=1),
        definition(defaultValue="1"),
        definition(defaultValue=1, options=[1, "2"]),
        definition(defaultValue=3, options=[1, 2]),
        definition(defaultValue=11, minimum=0, maximum=10),
        definition(defaultValue=1, options=[1, 11], minimum=0, maximum=10),
    ],
)
def test_invalid_parameter_definitions_are_rejected(item: ParameterDefinition) -> None:
    with pytest.raises(InvalidParameterError):
        validate_parameter_definitions(definitions(item))


def test_duplicate_parameter_names_are_rejected() -> None:
    with pytest.raises(InvalidParameterError, match="Duplicate parameter"):
        validate_parameter_definitions(definitions(definition(), definition()))
