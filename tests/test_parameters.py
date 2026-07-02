import pytest

from clavis.core.errors import InvalidParameterError
from clavis.parameters.validation import validate_options
from clavis.schemas import ParameterDefinitions


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
